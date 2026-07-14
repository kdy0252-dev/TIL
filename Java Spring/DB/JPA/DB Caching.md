---
id: DB Caching
started: 2025-04-02
tags:
  - ✅DONE
  - JPA
  - Cache
group: "[[Java Spring DB]]"
---

# JPA와 Application Cache

Cache는 같은 계산이나 조회를 재사용해 지연과 하위 부하를 줄인다. 대신 원본과 Cache가 다른 시점의 값을 가질 수 있으므로 Key, TTL, 무효화, 장애와 Stampede 정책이 기능의 일부다.

## Cache 계층

| 계층 | 범위 | 수명 |
|---|---|---|
| JPA 1차 Cache | EntityManager/Persistence Context | Transaction 또는 Context |
| JPA 2차 Cache | SessionFactory | Process·Provider 설정 |
| Spring Cache | Method 결과 | Cache Provider 정책 |
| Distributed Cache | 여러 Instance | Redis 등 외부 저장소 정책 |

## JPA 1차 Cache

같은 Persistence Context에서 같은 ID Entity를 두 번 조회하면 동일한 Managed Instance를 재사용할 수 있다. 이를 Application TTL Cache처럼 사용하면 안 된다.

```java
@Transactional(readOnly = true)
public boolean usesSameManagedInstance(long bookingId) {
    BookingJpaEntity first = repository.getReferenceById(bookingId);
    BookingJpaEntity second = repository.getReferenceById(bookingId);
    return first == second;
}
```

Transaction이 끝나면 Entity는 Detached된다. OSIV를 켜서 Context를 Web 응답까지 늘리면 Lazy Loading은 편해지지만 Query 경계와 Connection 사용이 흐려질 수 있다.

## Cache-aside Service

Domain Entity 자체보다 Version이 명확한 읽기 Resource를 Cache한다.

```java
public record BookingCacheKey(String tenantId, long bookingId, long schemaVersion) {
}

@Service
@RequiredArgsConstructor
public class BookingQueryService {

    private static final long CACHE_SCHEMA_VERSION = 3L;

    private final BookingQueryPort bookingQueryPort;
    private final BookingCache bookingCache;

    public Either<BookingError, BookingResource> get(String tenantId, long bookingId) {
        BookingCacheKey key = new BookingCacheKey(tenantId, bookingId, CACHE_SCHEMA_VERSION);

        return bookingCache.get(key)
                           .<Either<BookingError, BookingResource>>map(Either::right)
                           .orElseGet(() -> bookingQueryPort.findResource(tenantId, bookingId)
                               .peek(resource -> bookingCache.put(key, resource)));
    }
}
```

Tenant, Locale, 권한과 Filter처럼 결과에 영향을 주는 값을 Key에 포함한다. Access Token 원문 같은 민감 값은 Key로 저장하지 않는다.

## Spring Cache Annotation

```java
@Service
@RequiredArgsConstructor
public class CenterPolicyQueryService {

    private final CenterPolicyQueryPort queryPort;

    @Cacheable(
        cacheNames = "center-policy",
        keyGenerator = "tenantCenterCacheKeyGenerator",
        unless = "#result == null"
    )
    public CenterPolicyResource get(String tenantId, long centerId) {
        return queryPort.findResource(tenantId, centerId)
                        .getOrElseThrow(CenterPolicyQueryException::new);
    }

    @CacheEvict(cacheNames = "center-policy", keyGenerator = "tenantCenterCacheKeyGenerator")
    public void evict(String tenantId, long centerId) {
        // Annotation이 Method 완료 후 Key를 제거한다.
    }
}
```

복잡한 SpEL Key는 Type 안전성이 낮으므로 `tenantCenterCacheKeyGenerator`가 `tenantId`, `centerId`와 Cache Schema Version으로 불변 Key를 만든다. Self Invocation은 Spring Proxy를 통과하지 않아 Annotation이 적용되지 않는다.

## 쓰기와 무효화

Database Commit 전에 Cache를 지우면 Transaction Rollback 후 Cache만 사라지고, Commit 전에 새 값을 넣으면 Rollback된 값이 노출될 수 있다. Commit 성공 후 무효화 Event를 발행한다.

```java
@Transactional
public Either<CenterPolicyError, CenterPolicyResource> update(UpdateCenterPolicyCommand command) {
    return centerPolicyPort.find(command.centerId())
                           .flatMap(policy -> policy.update(command.settings(), command.actor()))
                           .flatMap(centerPolicyPort::save)
                           .flatMap(saved -> outboxPort.append(CenterPolicyChanged.from(saved))
                                                       .map(ignored -> saved))
                           .map(CenterPolicyResource::from);
}
```

Consumer가 Cache Key를 지우며 Event 중복에 안전해야 한다. 강한 Read-after-write가 필요하면 쓰기 응답에 새 Resource를 직접 반환하고 Cache 일관성 요구를 별도로 정의한다.

## Stampede 방지

Hot Key 만료 순간 여러 요청이 동시에 원본을 호출할 수 있다.

- 동일 Instance에서는 In-flight Deduplication으로 요청을 합친다.
- TTL에 Jitter를 넣어 동시 만료를 분산한다.
- Soft TTL 동안 오래된 값을 제공하고 Background Refresh한다.
- 원본 장애 시 오래된 값을 허용할 업무인지 정한다.
- Key별·전체 동시 Load 수를 제한한다.

## Negative Cache

존재하지 않는 ID 조회도 공격이나 Bug로 반복될 수 있다. 짧은 TTL로 Not Found를 Cache할 수 있지만 생성 직후까지 오래된 부재가 보이지 않도록 TTL과 무효화를 분리한다.

## 관측 지표

- Hit/Miss/Load 성공·실패 비율
- Load Duration P95/P99
- Entry 수, Byte와 Eviction 원인
- Hot Key와 Key Cardinality
- Stampede 시 Follower 수
- 무효화 Event Lag
- 오래된 값 제공 횟수와 나이

Hit Rate가 높아도 값이 잘못되면 좋은 Cache가 아니다. 원본과 Cache Version을 Sampling 비교하는 Reconciliation도 고려한다.

## 기억할 점

Cache는 Annotation 하나가 아니라 일관성 정책이다. Cache할 읽기 Model, 완전한 Key, Commit 이후 무효화, Stampede·장애 시 동작과 관측 지표를 함께 설계해야 한다.

# Reference

- [Spring Cache Abstraction](https://docs.spring.io/spring-framework/reference/integration/cache.html)
- [[In-flight Deduplication]]
