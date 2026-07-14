---
id: Bucket4j
started: 2025-06-25
tags:
  - ✅DONE
group: []
---

# Bucket4j Rate Limiter

Rate Limit은 일정 시간 동안 허용할 요청량을 제한해 한 사용자의 폭주가 전체 Service 장애로 번지는 것을 막는다. Bucket4j는 Token Bucket Algorithm을 구현한다.

## Token Bucket 기초

Bucket 용량이 100이고 초당 20 Token을 보충한다고 하자. 요청 하나가 Token 하나를 소비한다.

- 순간적으로 최대 100개 요청을 허용한다.
- 소진 후에는 초당 약 20개만 통과한다.
- Token이 없으면 HTTP 429와 재시도 가능 시점을 반환한다.

`fixedWindow`보다 순간 Burst를 허용하면서 평균 처리량을 제어하기 쉽다. 하지만 DB Connection, 외부 API처럼 비용이 다른 작업은 Endpoint별 정책이 필요하다.

## Production에서 먼저 결정할 것

1. Key: 인증된 Tenant/User/API Client 중 무엇을 제한할지 정한다.
2. Scope: Endpoint별 제한과 전체 Service 보호 제한을 나눈다.
3. Store: 여러 Pod라면 Redis 같은 공유 Store를 사용한다.
4. Failure Policy: Store 장애 시 통과시킬지 막을지 업무 위험에 따라 정한다.
5. Response: `Retry-After`와 표준 Error Body를 제공한다.

IP만 Key로 쓰면 NAT 뒤 정상 사용자들이 함께 차단되고 Proxy Header를 위조할 수 있다. 인증 Principal을 우선하고, IP는 신뢰 Proxy 설정 이후 보조 신호로 사용한다.

## Transport와 정책 분리

```java
public record RateLimitKey(long tenantId, long userId, String operation) {
}

public record RateLimitDecision(
    boolean allowed,
    long remainingTokens,
    Duration retryAfter
) {
}

public interface RateLimitPort {

    Either<RateLimitError, RateLimitDecision> consume(RateLimitKey key);
}
```

Application Port가 Bucket4j와 HTTP를 모르도록 하면 정책 Test와 저장소 교체가 쉬워진다.

## Bucket4j Adapter

```java
@Component
@RequiredArgsConstructor
public class Bucket4jRateLimitAdapter implements RateLimitPort {

    private static final long CAPACITY = 100;
    private static final long REFILL_TOKENS = 20;
    private static final Duration REFILL_INTERVAL = Duration.ofSeconds(1);

    private final ProxyManager<String> proxyManager;

    @Override
    public Either<RateLimitError, RateLimitDecision> consume(RateLimitKey key) {
        return Try.of(() -> proxyManager.builder()
                .build(cacheKey(key), this::configuration)
                .tryConsumeAndReturnRemaining(1))
            .toEither()
            .mapLeft(cause -> new RateLimitError.StoreFailure(key, cause))
            .map(this::toDecision);
    }

    private BucketConfiguration configuration() {
        Bandwidth bandwidth = Bandwidth.builder()
            .capacity(CAPACITY)
            .refillGreedy(REFILL_TOKENS, REFILL_INTERVAL)
            .build();

        return BucketConfiguration.builder()
            .addLimit(bandwidth)
            .build();
    }

    private RateLimitDecision toDecision(ConsumptionProbe probe) {
        return new RateLimitDecision(
            probe.isConsumed(),
            probe.getRemainingTokens(),
            Duration.ofNanos(probe.getNanosToWaitForRefill())
        );
    }

    private String cacheKey(RateLimitKey key) {
        return "%d:%d:%s".formatted(key.tenantId(), key.userId(), key.operation());
    }
}
```

여러 제한을 따로 `tryConsume()`하면 첫 Bucket만 소비된 뒤 두 번째에서 실패할 수 있다. 사용자 제한과 Global 제한을 원자적으로 묶어야 한다면 Redis Script나 Gateway의 계층형 Rate Limit 기능을 사용한다.

## Web Adapter

```java
@Component
@RequiredArgsConstructor
public class RateLimitInterceptor implements HandlerInterceptor {

    private final RateLimitPort rateLimitPort;

    @Override
    public boolean preHandle(
        HttpServletRequest request,
        HttpServletResponse response,
        Object handler
    ) {
        return Optional.of(handler)
            .filter(HandlerMethod.class::isInstance)
            .map(HandlerMethod.class::cast)
            .flatMap(this::operation)
            .map(operation -> enforce(request, response, operation))
            .orElse(true);
    }

    private boolean enforce(
        HttpServletRequest request,
        HttpServletResponse response,
        String operation
    ) {
        AuthenticatedUser user = AuthenticatedUser.from(request);
        RateLimitKey key = new RateLimitKey(user.tenantId(), user.userId(), operation);

        return rateLimitPort.consume(key)
            .fold(
                error -> failClosed(response, error),
                decision -> writeDecision(response, decision)
            );
    }

    private boolean writeDecision(HttpServletResponse response, RateLimitDecision decision) {
        response.setHeader(
            "RateLimit-Remaining",
            Long.toString(decision.remainingTokens())
        );

        return decision.allowed()
            || reject(response, decision.retryAfter());
    }

    private boolean reject(HttpServletResponse response, Duration retryAfter) {
        response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value());
        response.setHeader("Retry-After", Long.toString(Math.max(1, retryAfter.toSeconds())));
        return false;
    }
}
```

예제는 간결성을 위해 Body 작성을 생략했다. 실제 API에서는 공통 Exception Handler 또는 Error Response Writer로 `application/problem+json` Body를 일관되게 쓴다.

## 실패 정책

- 로그인 시도, 결제처럼 남용 위험이 크면 Store 장애 시 차단하는 Fail Closed를 고려한다.
- 일반 조회처럼 가용성이 더 중요하면 Local 비상 제한을 적용한 Fail Open을 고려한다.
- 오류를 조용히 통과시키지 말고 Store 오류율과 우회 요청 수를 Metric으로 남긴다.

## 검증

- 같은 Key의 Burst가 Capacity까지만 허용되는지 Test한다.
- 시간이 흐른 뒤 Token이 정책대로 보충되는지 가상 Clock으로 Test한다.
- 서로 다른 Tenant Key가 격리되는지 Test한다.
- 여러 Instance에서 총 허용량이 하나의 정책으로 적용되는지 통합 Test한다.
- Redis Timeout 때 선택한 Failure Policy가 적용되는지 Test한다.
- 허용·거절 수, Store 지연, Key Cardinality와 429 비율을 관측한다.

## 기억할 점

Rate Limiter는 `ConcurrentHashMap<IP, Bucket>` 예제가 아니라 분산 Key, 원자성, 장애 정책과 Client 재시도 계약을 포함한 운영 기능이다.

# Reference

- [Bucket4j Documentation](https://bucket4j.com/)
- [RFC 6585 - HTTP 429](https://www.rfc-editor.org/rfc/rfc6585)
