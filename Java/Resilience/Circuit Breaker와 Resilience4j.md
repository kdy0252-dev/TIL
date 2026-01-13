---
id: Circuit Breaker와 Resilience4j
started: 2026-01-13
tags:
  - ✅DONE
  - Java
  - Resilience
group:
  - "[[Java]]"
---
# Circuit Breaker와 Resilience4j: 장애 전파 방지를 위한 생존 전략

## 1. 개요 (Introduction)

마이크로서비스 아키텍처(MSA)에서 서비스 간의 호출은 필수적입니다. 하지만 만약 내가 호출하는 상대 서비스에 장애가 발생하여 응답이 오지 않는다면 어떻게 될까요? 

나의 서비스는 상대 서비스의 응답을 기다리며 스레드(Thread)를 점유하게 되고, 이런 호출이 쌓이면 결국 나의 서비스마저 스레드 부족으로 뻗어버리는 **장애 전파(Cascading Failure)** 현상이 발생합니다. 

이러한 연쇄 장애를 막고 시스템의 탄력성을 높이기 위해 반드시 도입해야 하는 패턴이 바로 **Circuit Breaker(서킷 브레이커)**입니다. 전기 회로 차단기가 과부하 시 전기를 끊어 화재를 막듯, 소프트웨어 서킷 브레이커는 비정상적인 서비스 호출을 차단하여 전체 시스템을 보호합니다.

---

## 2. Circuit Breaker의 동작 원리

서킷 브레이커는 시스템의 상태를 감시하며 세 가지 주요 상태 사이를 전이(Transition)합니다.

### 2.1 CLOSED (정상 상태)
- 모든 호출이 정상적으로 수행됩니다.
- 서킷 브레이커는 호출의 성공/실패율을 측정하며 백그라운드에서 감시합니다.

### 2.2 OPEN (장애 상태)
- 실패율이 설정된 임계치(Threshold)를 넘어서면 서킷이 열립니다.
- 이후의 요청은 실제 대상 서비스로 전달되지 않고 즉시 에러를 반환(Fail-fast)하거나 미리 준비된 **Fallback(대체 로직)**을 실행합니다.
- 이를 통해 장애가 발생한 서비스가 회복할 시간을 벌어줍니다.

### 2.3 HALF-OPEN (회복 시도 상태)
- 일정 시간이 지나면 서킷이 HALF-OPEN 상태로 변합니다.
- 소수의 요청만 대상 서비스로 보내 응답이 성공하는지 테스트합니다.
- 테스트가 성공하면 다시 `CLOSED`로 돌아가고, 실패하면 다시 `OPEN` 상태가 됩니다.

---

## 3. Resilience4j: 현대적인 탄력성 라이브러리

과거에는 Netflix Hystrix가 대세였으나, 현재는 유지보수 모드로 접어들었습니다. Spring Cloud에서도 공식적으로 권장하는 라이브러리는 **Resilience4j**입니다.

- **장점**:
  1. **경량성**: 다른 외부 라이브러리 의존성이 적습니다.
  2. **함수형 지향**: Java 8 익명 함수, 람다 등을 적극 지원합니다.
  3. **모듈화**: Circuit Breaker 외에도 Retry, RateLimiter, Bulkhead 등을 필요한 것만 골라 쓸 수 있습니다.

---

## 4. 실전 구현 예제 (Spring Boot 3 + Resilience4j)

### 4.1 의존성 설정 (build.gradle)

```gradle
dependencies {
    implementation 'io.github.resilience4j:resilience4j-spring-boot3'
    implementation 'org.springframework.boot:spring-boot-starter-aop'
}
```

### 4.2 설정 (application.yml)

```yaml
resilience4j:
  circuitbreaker:
    configs:
      default:
        slidingWindowSize: 10              # 최근 10번의 호출을 기준으로 통계 계산
        failureRateThreshold: 50           # 실패율이 50% 이상이면 서킷 오픈
        waitDurationInOpenState: 10s       # 오픈 후 10초 뒤에 Half-open 시도
        permittedNumberOfCallsInHalfOpenState: 3 # Half-open 상태에서 3번의 테스트 호출 수행
        slowCallRateThreshold: 50         # 느린 호출(Slow call) 임계치
        slowCallDurationThreshold: 2s      # 2초 이상 걸리면 느린 호출로 간주
    instances:
      externalService:
        baseConfig: default
```

### 4.3 서비스 코드 적용

```java
@Service
@Slf4j
@RequiredArgsConstructor
public class ExternalApiCaller {

    private final RestTemplate restTemplate;

    /**
     * @CircuitBreaker 어노테이션을 사용하여 선언적으로 적용
     * name: yml에 정의된 인스턴스 이름
     * fallbackMethod: 서킷이 오픈되었거나 에러 발생 시 실행될 메서드
     */
    @CircuitBreaker(name = "externalService", fallbackMethod = "fallbackForExternalApi")
    public String callExternalApi(String id) {
        log.info("외부 API 호출 시도: {}", id);
        // 고의로 장애 유발 시나리오
        return restTemplate.getForObject("http://unstable-service/api/data/" + id, String.class);
    }

    /**
     * Fallback 메서드는 타겟 메서드와 파라미터 타입이 같아야 하며,
     * 마지막 인자로 Throwable을 추가할 수 있습니다.
     */
    public String fallbackForExternalApi(String id, Throwable t) {
        log.error("서킷 오픈 또는 에러 발생! Fallback 실행. 원인: {}", t.getMessage());
        return "캐시된 데이터 또는 기본 응답값 반환 (ID: " + id + ")";
    }
}
```

---

## 5. 고급 활용 전략

### 5.1 Retry(재시도)와의 조합
일시적인 네트워크 순단은 한 번 더 시도하는 것만으로 해결될 수 있습니다. 
하지만 주의할 점은 **Retry를 Circuit Breaker보다 먼저 수행**하도록 설계해야 한다는 점입니다. (서킷이 열려있는데 재시도하는 것은 무의미하기 때문입니다.)

### 5.2 Bulkhead(벌크헤드) 패턴
타이타닉호의 선체 격벽 구조에서 유래한 패턴입니다. 
특정 API의 장애가 전체 서버의 스레드 풀을 다 써버리지 않도록, **기능별로 스레드 풀이나 세마포어(Semaphore)를 분리**하여 격리하는 기법입니다. Resilience4j는 이를 위한 전용 모듈을 제공합니다.

### 5.3 모니터링 (Observability)
서킷의 상태 변화는 매우 중요한 운영 지표입니다. 
- **Micrometer**를 사용하여 서킷의 상태(Opened/Closed)와 실패율 등을 **Prometheus**에 전송하고,
- **Grafana** 대시보드를 통해 실시간으로 시스템의 건강도를 시각화해야 합니다.

---

## 6. 결론

서킷 브레이커는 단순히 장애를 막는 도구가 아닙니다. 장애 상황에서도 시스템이 최소한의 기능을 유지하도록 돕는 **Graceful Degradation(품위 있는 성능 저하)**의 핵심 요소입니다.

백엔드 개발자로서 "에러가 발생하면 어떻게 처리할까?"를 고민하는 것을 넘어, **"시스템 전체의 연쇄 부하를 어떻게 차단할까?"**를 고민할 때 Resilience4j와 Circuit Breaker는 당신의 가장 든든한 아군이 되어줄 것입니다.

---
# Architecture Tips
- **임계치 설정**: 너무 예민하면 안정적인 시스템이 자주 차단되고, 너무 둔감하면 차단 효과가 없습니다. 모니터링을 통한 튜닝이 필수입니다.
- **예외 필터링**: 비즈니스 예외(Validation Error 등)는 서킷 브레이크의 실패율 계산에 포함되지 않도록 `recordExceptions` 설정을 적절히 조절하십시오.

# Reference
- [Resilience4j Official Documentation](https://resilience4j.readme.io/docs/circuitbreaker)
- [Martin Fowler: CircuitBreaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Microsoft Azure: Circuit Breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker)
- [Netflix Tech Blog: Making the Netflix API Fault Tolerant with Hystrix](https://netflixtechblog.com/making-the-netflix-api-fault-tolerant-with-hystrix-5a024921b023)
