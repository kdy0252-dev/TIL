---
id: Spring Cloud Sleuth
started: 2025-08-01
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Sleuth (Micrometer Tracing)

## 1. 개요 (Overview)
**Spring Cloud Sleuth**는 분산 시스템 환경(MSA)에서 **분산 추적(Distributed Tracing)**을 구현해주는 라이브러리입니다.
하나의 사용자 요청이 여러 마이크로서비스를 거쳐 처리될 때, 로그에 고유한 ID(Trace ID)를 남겨서 전체 흐름을 연결하고 병목 구간을 파악할 수 있게 해줍니다.

> **[IMPORTANT]**
> Spring Boot 3.x / Spring Cloud 2022.0.0 버전부터 **Spring Cloud Sleuth** 프로젝트는 종료되었으며, 그 기능은 **Micrometer Tracing**으로 이관되었습니다.
> 이 문서는 Sleuth의 개념을 설명하되, 최신 환경을 위해 Micrometer Tracing 마이그레이션 내용도 포함합니다.

---

## 2. 핵심 개념 (Core Concepts)

### 2.1 Trace & Span (Dapper 논문 기반)
Google Dapper 논문에서 유래한 용어를 사용합니다.
- **Trace (트레이스)**: 클라이언트의 최초 요청부터 마지막 응답까지의 전체 워크플로우를 의미합니다. 전체 여정동안 변하지 않는 유일한 **Trace ID**를 가집니다.
- **Span (스팬)**: Trace 내에서 수행되는 각각의 작업 단위(예: A 서비스 호출, DB 쿼리 등)입니다. 각 Span은 고유한 **Span ID**를 가지며, 부모 Span ID를 참조하여 트리 구조를 형성합니다.

### 2.2 로그 포맷팅 (Log Correlation)
Sleuth는 SLF4J의 MDC(Mapped Diagnostic Context) 기능을 사용하여 로그에 자동으로 Trace ID와 Span ID를 주입합니다.
- 형식: `[Service-Name, Trace-ID, Span-ID, Exportable]`
- 예: `[order-service, 64f1d5..., 3a1b2c..., true] Order created successfully.`
- 이 로그만 수집하면 ELK 스택(Logstash -> Elasticsearch)에서 Trace ID로 검색하여 전체 요청 흐름을 한눈에 볼 수 있습니다.

### 2.3 Context Propagation
HTTP(RestTemplate, Feign)나 Messaging(Kafka)을 통해 다른 서비스로 요청이 넘어갈 때, Sleuth는 필터나 인터셉터를 통해 헤더에 `X-B3-TraceId`, `X-B3-SpanId` 등을 자동으로 주입하여 ID를 전파(Propagation)합니다.

---

## 3. Zipkin 연동
Sleuth가 로그에 ID를 남겨주는 역할이라면, **Zipkin**은 이 데이터를 수집, 저장하고 시각화해주는 UI 서버입니다.
- **Architecture**: App -> (Reporter) -> Zipkin Server -> (Storage: ES/MySQL) -> Zipkin UI
- 각 Span의 시작과 끝 시간(Latency)을 기록하여 폭포수 차트(Waterfall Chart)로 보여줍니다. 어디서 시간이 오래 걸렸는지 시각적으로 디버깅할 수 있습니다.

---

## 4. Spring Boot 3 (Micrometer Tracing) 마이그레이션

Spring Boot 3에서는 Sleuth 대신 Micrometer Tracing을 사용해야 합니다.

### 4.1 의존성 변경

**Before (Sleuth)**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-sleuth'
implementation 'org.springframework.cloud:spring-cloud-sleuth-zipkin'
```

**After (Micrometer Tracing)**
```groovy
// 1. Micrometer Tracing Core
implementation 'io.micrometer:micrometer-tracing-bridge-brave' // 또는 otel

// 2. Zipkin Reporter
implementation 'io.zipkin.reporter2:zipkin-reporter-brave'
```

### 4.2 설정 (application.yml)
```yaml
management:
  tracing:
    sampling:
      probability: 1.0 # 100% 샘플링 (모든 요청 추적 - 개발용)
  zipkin:
    tracing:
      endpoint: "http://localhost:9411/api/v2/spans"
```

### 4.3 예제 코드 (Custom Span)
비즈니스 로직 내에서 특정 구간을 별도 Span으로 기록하고 싶을 때 사용합니다.

```java
@Service
@RequiredArgsConstructor
public class OrderService {
    
    // Tracer 주입 (Micrometer Tracing)
    private final Tracer tracer;

    public void processOrder() {
        // 새로운 Span 시작
        Span newSpan = tracer.nextSpan().name("calculate-tax");
        
        try (Tracer.SpanInScope ws = tracer.withSpan(newSpan.start())) {
            // 태그 추가
            newSpan.tag("tax.region", "KR");
            
            // 실제 로직...
            Thread.sleep(100);
            
        } catch (InterruptedException e) {
            newSpan.error(e);
        } finally {
            newSpan.end(); // 반드시 종료
        }
    }
}
```

---

## 5. 결론 및 요약
- **분산 추적의 필요성**: MSA에서는 로그가 파편화되어 있어 문제 추적이 어렵습니다. Trace ID 연결이 필수적입니다.
- **Sleuth의 역할**: ID 생성, 로그 주입(MDC), 컨텍스트 전파(Header Injection).
- **Zipkin의 역할**: 데이터 수집 및 시각화.
- **최신 동향**: Spring Boot 3부터는 `Micrometer Tracing` + `Brave`(또는 OpenTelemetry) 조합으로 표준화되었습니다.

# Reference
- [Spring Cloud Sleuth Reference (Deprecated)](https://docs.spring.io/spring-cloud-sleuth/docs/current/reference/html/)
- [Micrometer Tracing Documentation](https://micrometer.io/docs/tracing)
- [Baeldung - Migrating from Sleuth to Micrometer](https://www.baeldung.com/spring-boot-3-migration)
```