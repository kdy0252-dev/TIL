---
id: In-flight Deduplication
started: 2026-05-29
tags:
  - ✅DONE
  - Architecture
  - Concurrency
  - Performance
group:
  - "[[Java Spring Design Pattern]]"
---
# In-flight Deduplication (동시 요청 중복 제거)

## 1. 개요 (Overview)
**In-flight Deduplication**은 동일한 키를 가진 작업이 이미 실행 중일 때 새 작업을 시작하지 않고, 기존 작업의 완료 결과를 여러 호출자가 함께 받는 동시성 제어 패턴입니다. **Request Coalescing**, **Request Collapsing**, **Singleflight**라고도 부릅니다.

예를 들어 상품 ID `100`을 조회하는 요청 1,000개가 동시에 들어오면, 일반적인 구현은 데이터베이스나 외부 API를 1,000번 호출합니다. In-flight Deduplication을 적용하면 첫 번째 요청만 실제 작업을 수행하고 나머지 999개 요청은 같은 완료 결과를 기다립니다.

이 패턴의 목적은 결과를 장기간 저장하는 것이 아니라, **실행 중인 동일 작업을 하나로 합쳐 순간적인 중복 부하를 줄이는 것**입니다.

---

## 2. 해결하려는 문제 (The Thundering Herd Problem)
캐시가 만료되거나 애플리케이션이 콜드 스타트한 직후 동일한 데이터를 요구하는 요청이 한꺼번에 들어올 수 있습니다. 모든 요청이 캐시 미스를 확인한 뒤 원본 저장소를 각각 호출하면 다음 문제가 발생합니다.

- **중복 연산**: 같은 쿼리나 외부 API 호출이 동시에 반복됩니다.
- **하위 시스템 과부하**: 데이터베이스, 외부 API, 파일 시스템에 순간 부하가 집중됩니다.
- **지연 시간 증가**: 커넥션 풀과 스레드 풀이 고갈되어 관련 없는 요청까지 느려집니다.
- **장애 증폭**: 타임아웃과 재시도가 겹치면 작은 지연이 연쇄 장애로 확대될 수 있습니다.

이를 **Thundering Herd** 또는 **Cache Stampede** 문제라고 합니다. In-flight Deduplication은 같은 키의 대기 요청을 하나의 실행에 합쳐 하위 시스템으로 전달되는 동시 호출 수를 줄입니다.

---

## 3. 동작 원리 (How It Works)
핵심은 `요청 키 -> 진행 중인 비동기 결과`를 보관하는 맵입니다.

1. 요청에서 작업을 식별할 수 있는 키를 생성합니다.
2. 키에 해당하는 진행 중 작업이 있는지 확인합니다.
3. 작업이 없으면 현재 요청이 **Leader**가 되어 작업을 시작하고 결과 객체를 맵에 등록합니다.
4. 작업이 있으면 후속 요청은 **Follower**가 되어 같은 결과 객체를 반환받습니다.
5. 작업이 성공하거나 실패하면 모든 호출자에게 동일한 결과가 전달됩니다.
6. 완료된 작업은 맵에서 제거합니다. 이후 같은 키의 요청은 새로운 작업을 시작합니다.

```text
Request A (key=100) ─┐
Request B (key=100) ─┼─> In-flight Map ─> 1회 실행 ─> 동일 결과 공유
Request C (key=100) ─┘

Request D (key=200) ───> In-flight Map ─> 별도 실행
```

키가 같은 요청만 합쳐지므로 `100`과 `200`에 대한 작업은 서로 막지 않고 병렬로 실행됩니다.

---

## 4. 비슷한 개념과의 차이 (Comparison)

| 개념 | 중복을 판단하는 범위 | 결과 보관 | 주요 목적 |
|---|---|---|---|
| In-flight Deduplication | 작업이 실행 중인 동안 | 완료 즉시 제거 | 동시 중복 실행 방지 |
| Cache | TTL 또는 퇴거 전까지 | 완료 후에도 보관 | 재사용을 통한 응답 속도 향상 |
| Idempotency Key | 요청의 유효 기간 동안 | 처리 결과 또는 처리 상태 보관 | 쓰기 요청의 중복 처리 방지 |
| Rate Limiting | 시간 구간과 호출 주체 기준 | 결과를 공유하지 않음 | 전체 요청량 제한 |
| Debounce | 짧은 시간 창 안의 연속 호출 | 보통 마지막 호출만 실행 | 연속 이벤트 축소 |

In-flight Deduplication은 캐시 없이도 사용할 수 있습니다. 다만 캐시 미스가 집중되는 구간을 보호하기 위해 캐시와 함께 사용하는 경우가 많습니다.

> [!IMPORTANT]
> 결제나 주문 생성 같은 쓰기 작업은 단순히 동시에 실행 중인 요청만 합쳐서는 재시도 중복을 막을 수 없습니다. 프로세스 재시작 이후에도 중복 처리를 방지해야 하므로 영속적인 **Idempotency Key**를 사용해야 합니다.

---

## 5. Java 구현 (CompletableFuture)
다음 구현은 동일한 JVM 안에서 키별로 하나의 작업만 실행합니다. `putIfAbsent`로 Leader를 원자적으로 선출하고, 성공과 실패 모두에서 등록한 작업을 제거합니다.

```java
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;
import java.util.function.Supplier;

public final class InFlightDeduplicator<K, V> {

    private final ConcurrentHashMap<K, CompletableFuture<V>> inFlight =
            new ConcurrentHashMap<>();
    private final Executor executor;

    public InFlightDeduplicator(Executor executor) {
        this.executor = Objects.requireNonNull(executor);
    }

    public CompletionStage<V> execute(K key, Supplier<V> task) {
        Objects.requireNonNull(key);
        Objects.requireNonNull(task);

        CompletableFuture<V> candidate = new CompletableFuture<>();
        CompletableFuture<V> existing = inFlight.putIfAbsent(key, candidate);

        if (existing != null) {
            return existing.minimalCompletionStage();
        }

        try {
            executor.execute(() -> run(key, candidate, task));
        } catch (RuntimeException exception) {
            inFlight.remove(key, candidate);
            candidate.completeExceptionally(exception);
        }

        return candidate.minimalCompletionStage();
    }

    private void run(K key, CompletableFuture<V> result, Supplier<V> task) {
        try {
            result.complete(task.get());
        } catch (Throwable throwable) {
            result.completeExceptionally(throwable);
        } finally {
            inFlight.remove(key, result);
        }
    }

    public int inFlightCount() {
        return inFlight.size();
    }
}
```

### 5.1 `remove(key, result)`를 사용하는 이유
단순히 `remove(key)`를 호출하면 키에 새로운 작업이 등록된 뒤 이전 작업의 완료 콜백이 실행되는 경합 상황에서 새 작업을 잘못 제거할 수 있습니다. 키와 값이 모두 일치할 때만 제거해야 자신이 등록한 작업만 안전하게 정리할 수 있습니다.

### 5.2 결과 객체를 직접 노출하지 않는 이유
호출자에게 내부 `CompletableFuture`를 그대로 반환하면 Follower가 `cancel()`이나 `complete()`를 호출하여 모든 호출자의 공유 작업에 영향을 줄 수 있습니다. `minimalCompletionStage()`로 읽기 중심의 뷰를 반환하여 내부 완료 권한을 제한합니다.

---

## 6. Spring Service 적용 예시
조회 서비스에 적용할 때는 사용자별 권한과 응답 변형 요소까지 키에 포함해야 합니다.

```java
public record ProductRequestKey(Long productId, String locale, String tenantId) {
}
```

```java
@Configuration
public class InFlightConfiguration {

    @Bean
    public InFlightDeduplicator<ProductRequestKey, ProductResponse> productDeduplicator(
            @Qualifier("productExecutor") Executor productExecutor
    ) {
        return new InFlightDeduplicator<>(productExecutor);
    }
}
```

```java
@Service
@RequiredArgsConstructor
public class ProductQueryService {

    private final ProductClient productClient;
    private final InFlightDeduplicator<ProductRequestKey, ProductResponse> deduplicator;

    public CompletionStage<ProductResponse> getProduct(
            Long productId,
            String locale,
            String tenantId
    ) {
        ProductRequestKey key = new ProductRequestKey(productId, locale, tenantId);

        return deduplicator.execute(
                key,
                () -> productClient.getProduct(productId, locale, tenantId)
        );
    }
}
```

`productId`만 키로 사용하면 서로 다른 테넌트나 언어의 요청이 같은 결과를 공유할 수 있습니다. **결과를 달라지게 하는 모든 입력**을 키에 포함하되, 비밀번호나 액세스 토큰 같은 민감 정보 원문을 키로 저장하지 않아야 합니다.

---

## 7. 동시성 테스트 (Concurrency Test)
테스트에서는 같은 키에 대한 다수의 동시 요청이 하나의 실제 작업만 실행하는지 검증해야 합니다.

```java
@Test
void executesOnlyOnceForConcurrentRequestsWithSameKey() {
    ExecutorService executor = Executors.newFixedThreadPool(8);
    InFlightDeduplicator<String, String> deduplicator =
            new InFlightDeduplicator<>(executor);
    AtomicInteger executionCount = new AtomicInteger();
    CountDownLatch release = new CountDownLatch(1);

    try {
        List<CompletionStage<String>> requests = IntStream.range(0, 100)
                .mapToObj(index -> deduplicator.execute("product:100", () -> {
                    executionCount.incrementAndGet();
                    await(release);
                    return "result";
                }))
                .toList();

        release.countDown();

        List<String> results = requests.stream()
                .map(CompletionStage::toCompletableFuture)
                .map(CompletableFuture::join)
                .toList();

        assertThat(results).containsOnly("result");
        assertThat(executionCount).hasValue(1);
        assertThat(deduplicator.inFlightCount()).isZero();
    } finally {
        executor.shutdownNow();
    }
}

private static void await(CountDownLatch latch) {
    try {
        latch.await();
    } catch (InterruptedException exception) {
        Thread.currentThread().interrupt();
        throw new IllegalStateException(exception);
    }
}
```

추가로 다음 시나리오를 검증해야 합니다.

- 서로 다른 키는 각각 한 번씩 병렬 실행되는가?
- Leader가 실패하면 모든 Follower가 같은 실패를 전달받는가?
- 실패 후 같은 키로 다시 요청하면 새 작업이 실행되는가?
- 작업 완료 후 `inFlight` 항목이 제거되는가?
- 타임아웃이나 실행기 거부 시 항목이 남지 않는가?

---

## 8. 운영 시 주의사항 (Operational Considerations)

### 8.1 키 설계와 격리
잘못된 키는 다른 사용자의 데이터를 공유하는 보안 문제를 일으킬 수 있습니다. 테넌트, 사용자 권한, 로케일, 필터, 버전처럼 결과에 영향을 주는 입력을 정규화하여 키에 반영해야 합니다.

반대로 요청 ID나 현재 시각처럼 매번 달라지는 값을 포함하면 모든 키가 고유해져 중복 제거 효과가 사라집니다.

### 8.2 실패 공유
Leader의 실패도 모든 Follower에게 공유됩니다. 이는 중복 실패 호출을 막는 장점이 있지만 하나의 일시적 실패가 여러 요청에 전파된다는 뜻이기도 합니다. 타임아웃, 제한된 재시도, Circuit Breaker와 조합하되 재시도로 다시 Thundering Herd가 발생하지 않도록 Jitter를 적용해야 합니다.

### 8.3 취소 정책
Follower 한 명의 연결이 끊겼다고 공유 작업을 취소하면 아직 결과를 기다리는 다른 호출자도 실패합니다. 개별 호출자의 취소와 공유 작업의 취소를 분리하고, 모든 대기자가 사라졌을 때 작업을 취소할지는 별도의 정책으로 결정해야 합니다.

### 8.4 메모리와 무한 대기
완료되지 않는 작업은 맵에 계속 남습니다. 하위 호출에 타임아웃을 적용하고, 전체 진행 중 키 수와 키별 대기자 수를 제한해야 합니다. 키의 종류가 무제한이면 공격이나 트래픽 급증으로 메모리가 고갈될 수 있습니다.

### 8.5 단일 인스턴스의 한계
`ConcurrentHashMap` 구현은 **현재 JVM 내부에서만** 중복을 제거합니다. 애플리케이션 인스턴스가 10개라면 같은 키의 하위 호출이 최대 10개 실행될 수 있습니다.

클러스터 전체에서 한 번만 실행하려면 요청을 같은 인스턴스로 라우팅하거나, 프록시·외부 캐시의 Request Coalescing 기능을 사용하거나, 분산 조정 계층을 별도로 설계해야 합니다. 분산 락만 추가하면 Follower에게 결과를 전달하는 문제, Leader 장애, 락 만료, Fencing Token까지 처리해야 하므로 요구 수준을 먼저 확인해야 합니다.

### 8.6 관측 지표
다음 지표를 수집하면 패턴의 효과와 병목을 확인할 수 있습니다.

- `inflight.active`: 현재 실행 중인 고유 키 수
- `inflight.leader.count`: 실제 작업을 시작한 요청 수
- `inflight.follower.count`: 기존 작업에 합류한 요청 수
- `inflight.coalescing.ratio`: 전체 요청 중 Follower 비율
- `inflight.wait.duration`: Follower의 대기 시간
- 실제 하위 시스템 호출 수와 실패율

---

## 9. 적용 기준 (When to Use)

### 적합한 경우
- 동일한 조회 키에 트래픽이 집중되는 Hot Key가 존재합니다.
- 작업 비용이 크고 같은 입력에 대해 같은 결과를 반환합니다.
- 캐시 만료나 콜드 스타트 시 하위 시스템 부하가 급증합니다.
- 짧은 시간 동안 결과를 공유해도 데이터 정합성과 권한 문제가 없습니다.

### 피해야 하는 경우
- 요청마다 부수 효과가 반드시 한 번씩 발생해야 합니다.
- 같은 입력이어도 호출 시점이나 사용자 컨텍스트에 따라 결과가 달라집니다.
- 대부분의 요청 키가 고유하여 합쳐질 가능성이 거의 없습니다.
- 작업 시간이 매우 길고 하나의 실패가 많은 요청에 전파되는 것이 위험합니다.

---

## 10. 결론
In-flight Deduplication은 동일한 작업이 동시에 몰릴 때 **한 요청만 실제 작업을 수행하고 나머지는 그 결과를 공유**하게 하는 단순하고 효과적인 패턴입니다. 캐시와 달리 완료된 결과를 보관하지 않으므로 데이터의 신선도를 유지하면서 순간적인 중복 부하를 줄일 수 있습니다.

구현 자체보다 중요한 것은 정확한 키 설계, 실패와 취소 정책, 타임아웃, 인스턴스 범위의 명확화입니다. 특히 단일 JVM 구현을 클러스터 전체 보장으로 오해하지 않아야 하며, 쓰기 요청의 중복 처리는 영속적인 멱등성 설계로 분리해야 합니다.

---

## 18. 실무 사례 적용 진단과 개선 과제

이 사례에는 동일 조회를 합치는 구현과 Cache Stampede를 줄일 수 있는 구조가 있지만 적용 범위와 Key Cardinality, 대기자 수, Leader 실패가 공통 Metric으로 관리되지는 않습니다. 이 패턴은 단일 JVM 범위이므로 Pod가 여러 개일 때 Cluster 전체 중복 호출은 그대로 남습니다.

우선 외부 Map·주소 조회처럼 비용이 크고 동일 Key가 실제로 겹치는 경로만 후보로 측정합니다. `inflight_size`, leader/follower 수, 대기 시간, 실패 공유 수를 추가하고 Key 정규화와 최대 Map 크기를 둡니다. Cluster-wide 제어가 필요하면 무거운 분산 Lock보다 Provider Idempotency, 짧은 Cache, Request Coalescing Gateway를 먼저 비교합니다.

완료 기준은 동시 N개 동일 요청에서 실제 Upstream 호출이 1회이고 Leader 실패·Timeout 뒤 Entry가 제거되며, 서로 다른 Tenant·권한 Context가 같은 Key로 합쳐지지 않는 Test가 통과하는 상태입니다.

---

# Reference
- [Go singleflight Package](https://pkg.go.dev/golang.org/x/sync/singleflight)
- [AWS Builders' Library: Caching challenges and strategies](https://aws.amazon.com/builders-library/caching-challenges-and-strategies/)
- [Caffeine Cache](https://github.com/ben-manes/caffeine)
