---
id: Spring Cloud Sleuth
started: 2025-08-01
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---

# Spring Cloud Sleuth에서 Micrometer Tracing으로

Spring Cloud Sleuth의 기능은 Spring Boot 3 세대부터 Micrometer Tracing으로 이동했다. 새 Application은 Sleuth Starter가 아니라 Micrometer Observation·Tracing과 Brave 또는 OpenTelemetry Bridge를 사용한다.

## Trace와 Span

- **Trace**: 한 요청이 여러 Service를 거치는 전체 흐름이다.
- **Span**: HTTP 호출, Database Query와 업무 단계 같은 하나의 작업 구간이다.
- **Trace ID**: 같은 Trace의 모든 Span이 공유한다.
- **Span ID**: 각 Span을 구분한다.
- **Context Propagation**: HTTP·Message Header로 Trace Context를 다음 Process에 전달한다.

Log의 Trace ID는 검색 연결점이고 Trace Backend의 Span은 시간·부모 관계·Tag와 Error를 보존한다. 민감 정보나 무제한 Cardinality의 ID를 Tag로 넣으면 안 된다.

## 의존성

Brave 또는 OpenTelemetry 중 하나의 Bridge를 선택하고 Exporter를 추가한다. Version은 Spring Boot Dependency Management에 맡긴다.

```groovy
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-actuator'
    implementation 'io.micrometer:micrometer-tracing-bridge-otel'
    implementation 'io.opentelemetry:opentelemetry-exporter-otlp'
}
```

## 설정

```yaml
management:
  tracing:
    sampling:
      probability: 0.1
  otlp:
    tracing:
      endpoint: ${OTLP_TRACING_ENDPOINT}
```

Production에서 100% Sampling을 기본값으로 두면 비용과 저장량이 급증할 수 있다. 오류·고지연 Trace를 더 보존하려면 Backend와 SDK가 지원하는 Tail Sampling 정책을 검토한다.

## Observation API를 우선한다

Metric과 Trace를 같은 계측 지점에서 만들려면 `ObservationRegistry`를 사용한다. Lifecycle을 직접 `start/end`하지 않아 Span 누락을 줄인다.

```java
@Service
@RequiredArgsConstructor
public class FareCalculationService {

    private final ObservationRegistry observationRegistry;
    private final FarePolicy farePolicy;

    public Fare calculate(FareContext context) {
        return Observation.createNotStarted("fare.calculate", observationRegistry)
                          .lowCardinalityKeyValue("fare.type", context.fareType().name())
                          .observe(() -> farePolicy.calculate(context));
    }
}
```

`bookingId`, Email과 전체 URL처럼 값 종류가 계속 늘어나는 값은 Low-cardinality Tag에 넣지 않는다. 필요하면 Log Field나 Trace Event에 제한적으로 기록하고 개인정보 정책을 적용한다.

## Error와 결과 관찰

아래 Method는 외부 결제 Provider를 감싸는 Out Adapter의 구현이다. Adapter는 `Either`를 반환하고 이를 호출하는 최상위 Service가 Application Exception으로 변환한다.

```java
@Component
@RequiredArgsConstructor
public class ObservedPaymentProviderAdapter implements ApprovePaymentPort {

    private final ObservationRegistry observationRegistry;
    private final PaymentClient paymentClient;
    private final PaymentMapper mapper;
    private final PaymentProviderProperties properties;

    @Override
    public Either<PaymentError, PaymentApproval> approve(PaymentRequest request) {
        return Observation.createNotStarted("payment.approve", observationRegistry)
            .lowCardinalityKeyValue("provider", properties.providerName())
            .observe(() -> Try.of(() -> paymentClient.approve(mapper.toProviderRequest(request)))
                .map(mapper::toApproval)
                .toEither()
                .mapLeft(cause -> new PaymentError.ProviderFailure(request.paymentId(), cause))
                .peekLeft(error -> Optional.ofNullable(Observation.currentObservation())
                    .ifPresent(current -> current.error(error.cause()))));
    }
}
```

`observe`가 성공과 실패 경로 모두에서 Observation을 종료한다. Provider Transaction ID처럼 값 종류가 무제한인 식별자는 Metric Tag가 아니라 보안 정책을 적용한 구조화 Log 또는 Trace Event로 남긴다.

## HTTP와 Kafka Context 전파

Spring이 관리하는 `RestClient`, `WebClient`, Kafka Template과 Listener Container를 Builder·Auto Configuration을 통해 사용하면 Observation Interceptor가 Context를 전파한다. 직접 Client를 `new`로 만들거나 Thread Pool에 Runnable만 넘기면 Context가 끊길 수 있다.

비동기 Executor에는 Context Propagation을 적용한다.

```java
@Bean
TaskDecorator contextPropagatingTaskDecorator() {
    return new ContextPropagatingTaskDecorator();
}

@Bean
ThreadPoolTaskExecutor applicationExecutor(TaskDecorator taskDecorator) {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setCorePoolSize(8);
    executor.setMaxPoolSize(32);
    executor.setQueueCapacity(500);
    executor.setTaskDecorator(taskDecorator);
    executor.setThreadNamePrefix("application-");
    executor.initialize();
    return executor;
}
```

Executor Queue, Rejection과 Shutdown 정책도 함께 설정한다. Context 전파는 무제한 Async 작업을 안전하게 만들어 주는 기능이 아니다.

## Baggage

Baggage는 Trace와 함께 전파되는 작은 Context 값이다. Tenant ID 같은 값을 무조건 Baggage에 넣으면 모든 Network 요청과 Log에 퍼질 수 있다.

- 필요한 Service만 읽는 값인지 확인한다.
- 크기와 개수를 제한한다.
- 인증 Token과 개인정보를 넣지 않는다.
- 신뢰 경계를 넘을 때 허용 목록으로 필터링한다.

## 운영 Checklist

- Trace Exporter 장애가 업무 요청을 막지 않는가?
- Sampling 비율과 저장 Retention이 비용 Budget 안인가?
- HTTP·Kafka·Executor 경계에서 Parent-Child 관계가 이어지는가?
- Error Span에 Stack과 업무 Error Code가 기록되는가?
- Tag Cardinality와 개인정보를 정기적으로 검사하는가?
- Trace ID가 구조화 Log에 포함되는가?

## 기억할 점

분산 추적은 Span을 많이 만드는 일이 아니다. 자동 계측을 기본으로 사용하고, 업무 병목 구간에 낮은 Cardinality의 의미 있는 Observation을 추가하며, Context 전파·Sampling·민감 정보와 Export 실패를 운영 정책으로 관리해야 한다.

# Reference

- [Micrometer Tracing](https://docs.micrometer.io/tracing/reference/)
- [Spring Boot Observability](https://docs.spring.io/spring-boot/reference/actuator/observability.html)
