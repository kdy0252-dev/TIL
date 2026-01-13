---
id: 레질리언스 패턴과 Resilience4j
started: 2026-01-13
tags:
  - ✅DONE
  - Java
  - Resilience
  - SpringBoot
group:
  - "[[Java]]"
---
# 레질리언스 패턴 가이드: 장애에 강한 분산 시스템 구축하기

## 1. 개요 (Introduction)

마이크로서비스 아키텍처(MSA)에서 서비스 간의 호출은 네트워크라는 불안정한 매개체를 통합니다. "네트워크는 항상 신뢰할 수 없다"는 가정 하에, 특정 서비스의 장애가 전체 시스템으로 번지는 **장애 전파(Cascading Failure)**를 막는 것은 백엔드 엔지니어의 핵심 역량입니다.

본 가이드에서는 시스템의 탄력성(Resilience)을 확보하기 위한 4대 핵심 패턴인 **Circuit Breaker, Bulkhead, Retry, Timeout**을 상세히 다루고, Java 진영의 표준 라이브러리인 **Resilience4j**를 이용한 실무 구현 사례를 소개합니다.

---

## 2. Circuit Breaker (서킷 브레이커)

장애가 발생한 지점으로의 호출을 강제로 차단하여 시스템을 보호하고, 장애 서비스가 회복할 시간을 벌어주는 패턴입니다.

### 2.1 동작 원리
- **CLOSED**: 정상 상태. 모든 요청 허용.
- **OPEN**: 실패율 임계치 초과 시. 요청을 즉시 차단(Fail-fast)하고 Fallback 실행.
- **HALF-OPEN**: 일정 시간 후 회복 여부 테스트. 소수의 요청만 보내 성공 시 CLOSED로 복귀.

### 2.2 실전 예제 코드
```java
@CircuitBreaker(name = "backendA", fallbackMethod = "fallback")
public String callBackendA() {
    return restTemplate.getForObject("http://backend-a/api", String.class);
}

public String fallback(Throwable t) {
    return "Fallback response: Backend A is currently unavailable.";
}
```

---

## 3. Bulkhead (벌크헤드)

함선의 격벽 구조에서 유래한 패턴으로, 리서스(스레드 풀, 커넥션 등)를 격리하여 특정 기능의 장애가 다른 기능의 리소스를 고갈시키지 않도록 방어합니다.

### 3.1 구현 방식
- **Semaphore Bulkhead**: 동시 실행 횟수만 제한합니다. 오버헤드가 적습니다.
- **Thread Pool Bulkhead**: 별도의 스레드 풀을 할당합니다. 타임아웃 제어가 쉽지만 컨텍스트 스위칭 비용이 발생합니다.

### 3.2 실전 예제 코드 (ThreadPool 방식)
```java
@Bulkhead(name = "orderService", type = Bulkhead.Type.THREADPOOL)
public CompletableFuture<String> processOrder() {
    return CompletableFuture.completedFuture(doHeavyWork());
}
```

---

## 4. Retry + Backoff (재시도와 백오프)

일시적인 네트워크 순단이나 타임아웃 시, 즉시 에러를 내지 않고 다시 시도하는 패턴입니다. 무분별한 재시도는 서버 과부하를 초래하므로 반드시 **Exponential Backoff(지수 백오프)**를 동반해야 합니다.

### 4.1 핵심 아이디어
- **Fixed Interval**: 일정한 간격으로 재시도.
- **Exponential Backoff**: 실패할 때마다 대기 시간을 2배씩 늘림 (예: 1s -> 2s -> 4s...).
- **Jitter**: 여러 클라이언트가 동시에 재시도하여 발생하는 병목(Thundering Herd)을 막기 위해 대기 시간에 랜덤값을 섞음.

### 4.2 실전 예제 코드
```java
@Retry(name = "externalApi", fallbackMethod = "retryFallback")
public String callWithRetry() {
    return externalClient.fetchData();
}
```

**YAML 설정 예시:**
```yaml
resilience4j.retry:
  instances:
    externalApi:
      maxAttempts: 3
      waitDuration: 500ms
      enableExponentialBackoff: true
      exponentialBackoffMultiplier: 2
```

---

## 5. Timeout (타임아웃)

상대 서비스의 응답이 늦어질 때 무한정 기다리지 않고 연결을 끊는 가장 기본적이고 강력한 패턴입니다. 지연된 호출이 시스템 전체의 스레드를 점유하는 것을 방지합니다.

### 5.1 타임아웃의 종류
- **Connect Timeout**: 서버와 연결을 맺는 데 걸리는 시간 제한.
- **Read Timeout**: 연결 후 데이터를 응답받는 데 걸리는 시간 제한.

### 5.2 실전 예제 코드 (TimeLimiter)
```java
@TimeLimiter(name = "slowService")
public CompletableFuture<String> callSlowService() {
    return CompletableFuture.supplyAsync(() -> {
        // 2초 이상 소요되는 로직
        return restTemplate.getForObject("/slow-api", String.class);
    });
}
```

---

## 6. Resilience4j 종합 설정 가이드

실무에서는 이 패턴들을 조합해서 사용합니다. 권장되는 필터 체인 순서는 다음과 같습니다.
> **Retry → CircuitBreaker → RateLimiter → TimeLimiter → Bulkhead**

### 6.1 통합 설정 (application.yml)
```yaml
resilience4j:
  circuitbreaker:
    instances:
      mainService:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 10s
  bulkhead:
    instances:
      mainService:
        maxConcurrentCalls: 5
  retry:
    instances:
      mainService:
        maxAttempts: 3
        waitDuration: 1s
  timelimiter:
    instances:
      mainService:
        timeoutDuration: 2s
```

---

## 7. 결론

레질리언스 패턴은 "언젠간 고장 날 시스템"을 "고장 나도 죽지 않는 시스템"으로 바꿔주는 마법입니다.
- **Circuit Breaker**로 장애 지점을 격리하고,
- **Bulkhead**로 리소스를 보호하며,
- **Retry**로 일시적 오류를 극복하고,
- **Timeout**으로 시스템 점유를 방지하십시오.

이러한 패턴들을 적절히 조합하여 구축한 시스템은 어떤 폭풍우 같은 장애 상황에서도 핵심 비즈니스 로직을 안전하게 지켜낼 수 있을 것입니다.

# Reference
- [Resilience4j Official Documentation](https://resilience4j.readme.io/docs/getting-started)
- [Baeldung: Guide to Resilience4j](https://www.baeldung.com/resilience4j)
- [Netflix Tech Blog: Fault Tolerance](https://netflixtechblog.com/)
- [Microsoft: Cloud Design Patterns (Resiliency)](https://learn.microsoft.com/en-us/azure/architecture/patterns/category/resiliency)
