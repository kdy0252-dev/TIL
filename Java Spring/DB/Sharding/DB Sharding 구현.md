---
id: DB Sharding
started: 2025-05-14
tags:
  - ⏳DOING
group:
  - "[[Java Spring DB]]"
---
# DB Sharding 구현
## Java Spring에서 DB 샤딩을 구현하는 방법
Java Spring에서 DB 샤딩을 구현하는 방법은 크게 2가지로 나뉜다.
- 직접 샤딩 알고리즘을 구현해서 Datasource를 선택.
- Middleware를 사용
![[Pasted image 20250514095847.png]]
직접 구현하는 것은 구현 난이도측면에서나 운영 측면에서 난이도는 높지만 자유로운 장점이 있다.
Middleware를 사용하는 것은 구현 난이도나 운영 난이도는 낮지만 자유도는 살짝 떨어지는 단점이 있다.

| 항목                 | 직접 커스텀                    | ShardingSphere              |
| ------------------ | ------------------------- | --------------------------- |
| **유연성**            | 최고 (원하는대로 코딩 가능)          | 룰 기반으로 설정 (대부분 커버)          |
| **개발 난이도**         | 높음                        | 매우 낮음                       |
| **운영 난이도**         | 높음 (pool, failover 직접 관리) | 낮음 (proxy처럼 동작)             |
| **복잡한 샤딩 로직**      | 가능                        | 일부 한계 (복잡한 join 등)          |
| **distributed TX** | 직접 구현 (보통 Saga)           | 자체 XA / BASE transaction 지원 |
| **Spring Boot 통합** | 완벽 (직접 코드로)               | 완벽 (starter + yml 설정)       |
| **대형 서비스 적용**      | 일부 (토스 등)                 | 일부 (쿠팡, 해외 기업 등)            |

샤딩을 할때는 일단 소프트웨어적인 설계가 필요하다.
### 1. 샤드 라우팅 (Shard Routing)
- 요청이 들어왔을 때 **어떤 샤드 DB로 보낼지 결정하는 라우팅 로직** 필요  
    예) userId, tenantId, orderId 등을 기준으로 hash, modulo, range partitioning 등 적용
- 보통 `AbstractRoutingDataSource`를 상속하거나, **샤드 context holder**를 둠
### 2. 트랜잭션 일관성
- **단일 샤드 트랜잭션**은 일반적인 Spring TX로 가능
- **다중 샤드 트랜잭션 (cross-shard TX)** 은 지원 안 됨 → **분산 트랜잭션 (2PC, Saga 패턴 등)** 필요
- 샤드 경계 넘어가는 작업은 되도록 피하거나, 보상 트랜잭션 설계
### 3. 데이터 일관성 고려
- 동일한 entity가 여러 샤드에 걸치지 않도록 **shard key 설계**
- 분산락은 보통 **중앙 lock server (Redis, ZooKeeper 등)**를 사용
- idempotent 설계 (같은 요청이 여러 번 와도 상태 일관성 유지)
### 4. ID Generation 전략
- 샤드별 auto increment 사용 시 **중복 위험**
- 보통 **Snowflake, UUID, Redis 기반 sequence** 등으로 global unique key 발급
### 5. Failover 및 샤드 추가 대비
- 샤드 수가 늘어나거나 줄어들 때 routing rule을 쉽게 변경 가능하게 설계
- 중간에 샤드 migration 필요 시 데이터 재분배 logic 필요
### 6. Monitoring & Logging
- 어느 샤드로 요청이 갔는지 로그 남기기
- 성능 지표, 오류 지표를 샤드 단위로 수집

## 1. 직접 구현
```css title="Sample Package Structure"
com.example.shardingdemo
├── config
│   ├── DataSourceConfig.java        → 샤딩 DataSource 설정
│   ├── RedissonConfig.java          → Redis 분산락 설정
│   └── ShardRoutingDataSource.java  → 샤드 라우팅
├── context
│   └── ShardContextHolder.java      → ThreadLocal로 샤드키 저장
├── domain
│   ├── Order.java                   → Entity
│   ├── OrderRepository.java         → JPA Repository
│   └── IdGenerator.java             → Snowflake 기반 ID 생성기
├── service
│   ├── DistributedLockService.java  → 분산락 서비스
│   └── OrderService.java            → 비즈니스 로직 + 샤딩 + 락 처리
├── controller
│   └── OrderController.java         → REST API 엔드포인트
└── ShardingDemoApplication.java     → SpringBoot main class
```
### 주요 클래스 예시
```java title="ShardContextHolder.java"
public class ShardContextHolder {
    private static final ThreadLocal<String> CONTEXT = new ThreadLocal<>();

    public static void setShardKey(String shardKey) {
        CONTEXT.set(shardKey);
    }

    public static String getShardKey() {
        return CONTEXT.get();
    }

    public static void clear() {
        CONTEXT.remove();
    }
}
```

```java title="ShardRoutingDataSource.java"
public class ShardRoutingDataSource extends AbstractRoutingDataSource {
    @Override
    protected Object determineCurrentLookupKey() {
        return ShardContextHolder.getShardKey();
    }
}
```

```java title="DataSourceConfig.java"
@Configuration
public class DataSourceConfig {

    @Bean
    public DataSource dataSource(
            @Qualifier("shard1DataSource") DataSource shard1,
            @Qualifier("shard2DataSource") DataSource shard2) {
        
        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put("shard1", shard1);
        targetDataSources.put("shard2", shard2);

        ShardRoutingDataSource routingDataSource = new ShardRoutingDataSource();
        routingDataSource.setTargetDataSources(targetDataSources);
        routingDataSource.setDefaultTargetDataSource(shard1);
        return routingDataSource;
    }

    @Bean(name = "shard1DataSource")
    @ConfigurationProperties(prefix = "spring.datasource.shard1")
    public DataSource shard1DataSource() {
        return DataSourceBuilder.create().build();
    }

    @Bean(name = "shard2DataSource")
    @ConfigurationProperties(prefix = "spring.datasource.shard2")
    public DataSource shard2DataSource() {
        return DataSourceBuilder.create().build();
    }
}
```

```java title="RedissonConfig.java"
@Configuration
public class RedissonConfig {
    @Bean
    public RedissonClient redissonClient() {
        Config config = new Config();
        config.useSingleServer().setAddress("redis://localhost:6379");
        return Redisson.create(config);
    }
}
```

```java title="Order.java"
@Entity
public class Order {
    @Id
    private Long id;
    private Long userId;
    private String itemName;

    protected Order() {}

    public Order(Long id, Long userId, String itemName) {
        this.id = id;
        this.userId = userId;
        this.itemName = itemName;
    }
}
```

```java title="DistributedLockService.java"
@Service
public class DistributedLockService {
    private final RedissonClient redissonClient;

    public DistributedLockService(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public void lock(String key, Runnable action) {
        RLock lock = redissonClient.getLock(key);
        try {
            if (lock.tryLock(5, 10, TimeUnit.SECONDS)) {
                action.run();
            } else {
                throw new IllegalStateException("Lock not acquired");
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException(e);
        } finally {
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

```java title="IdGenerator.java"
@Component
public class IdGenerator {
    private final Snowflake snowflake = IdUtil.getSnowflake(1, 1);

    public long generateId() {
        return snowflake.nextId();
    }
}
```

```java title="OrderService.java"
@Service
public class OrderService {
    private final OrderRepository orderRepository;
    private final DistributedLockService lockService;
    private final IdGenerator idGenerator;

    public OrderService(OrderRepository orderRepository,
                        DistributedLockService lockService,
                        IdGenerator idGenerator) {
        this.orderRepository = orderRepository;
        this.lockService = lockService;
        this.idGenerator = idGenerator;
    }

    public void createOrder(Long userId, String itemName) {
        String shardKey = "shard" + (userId % 2);
        ShardContextHolder.setShardKey(shardKey);
        try {
            lockService.lock("order_" + userId, () -> {
                Order order = new Order(idGenerator.generateId(), userId, itemName);
                orderRepository.save(order);
            });
        } finally {
            ShardContextHolder.clear();
        }
    }
}
```

```java title="OrderController.java"
@RestController
@RequestMapping("/orders")
public class OrderController {
    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    public ResponseEntity<String> createOrder(@RequestParam Long userId, @RequestParam String itemName) {
        orderService.createOrder(userId, itemName);
        return ResponseEntity.ok("Order Created");
    }
}
```
## 2. Apache ShardingSphere 사용
### 의존성 추가
```kotlin title="build.gradle.kts"
implementation("org.apache.shardingsphere:shardingsphere-jdbc-core-spring-boot-starter:5.x.x")
```

### application.yml 설정
```yaml title="application.yml"
spring:
  shardingsphere:
    datasource:
      names: shard1, shard2
      shard1:
        type: com.zaxxer.hikari.HikariDataSource
        driver-class-name: org.h2.Driver
        jdbc-url: jdbc:h2:mem:shard1;DB_CLOSE_DELAY=-1
        username: sa
        password:
      shard2:
        type: com.zaxxer.hikari.HikariDataSource
        driver-class-name: org.h2.Driver
        jdbc-url: jdbc:h2:mem:shard2;DB_CLOSE_DELAY=-1
        username: sa
        password:

    rules:
      sharding:
        tables:
          order:
            actual-data-nodes: shard$->{1..2}.order
            table-strategy:
              standard:
                sharding-column: user_id
                sharding-algorithm-name: order_inline
        sharding-algorithms:
          order_inline:
            type: INLINE
            props:
              algorithm-expression: shard${user_id % 2}
```
- `user_id % 2`로 자동 routing
- application code에 shard context holder 필요 없음
- DDL, DML, transaction 모두 지원

```java title="OrderService"
@Service
public class OrderService {
    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public void createOrder(Long userId, String itemName) {
        Order order = new Order(userId, itemName);
        orderRepository.save(order); // 자동으로 ShardingSphere가 routing
    }
}
```

## 주의사항
### 1. 다중 샤드에 걸친 원자적 작업이 필요한 경우
예를 들어 다음과 같습니다.
#### 예시 A: 사용자 이체 시스템
- `userA`의 계좌는 `shard1`
- `userB`의 계좌는 `shard2`
- `userA → userB`로 돈을 이체할 때  
    → `shard1`에서 출금 + `shard2`에서 입금 **둘 중 하나라도 실패하면 rollback** 해야 함
이게 대표적인 **distributed transaction (2PC 또는 Saga)** 케이스입니다.
#### 예시 B: 다중 테넌트 → 공통 자원 연동
- 테넌트 DB (샤드 DB) + 공통 시스템 DB를 동시에 update해야 하는 경우  
    예) tenant user의 상태 update + 공통 marketing table 업데이트
#### 예시 C: 데이터 재배치 (Shard Rebalancing)
- 샤드 migration 작업 중 **기존 샤드 → 신규 샤드로 데이터를 이동**하면서 consistency 보장을 원할 때
### 2. 다중 샤드 트랜잭션의 문제
#### 단점
- **성능 저하**: 2개 이상의 샤드 DB에 동시에 Lock + prepare + commit 과정 필요 → 지연 심각
- **복잡한 장애 처리**: 한 DB commit 성공, 다른 DB 실패 → 복구 로직 (compensation, rollback) 필요
- **운영 부담**: DB, 코드, 인프라 모두 복잡도 급증
그래서 **실제 대규모 서비스 (ex. 카카오, 네이버, 토스, 쿠팡)**에서는 **가능하면 피하고 설계 단계에서 회피**합니다.
#### 대안: 다중 샤드 트랜잭션을 피하는 방법

| 방법                       | 설명                                                             |
| ------------------------ | -------------------------------------------------------------- |
| **Shard Key 잘 잡기**       | 모든 데이터가 하나의 샤드로만 가도록 설계                                        |
| **Saga 패턴**              | 각 샤드에서 local transaction + 보상 트랜잭션으로 eventually consistency 확보 |
| **Eventual Consistency** | 엄격한 ACID 대신 데이터 일관성을 나중에 맞추는 방법                                |
### 3. 현실적인 샤딩 모델
샤딩 설계 시 다음 중 하나로 정리합니다.

| 모델                                 | 설명                                | 장점                           | 단점                      |
| ---------------------------------- | --------------------------------- | ---------------------------- | ----------------------- |
| **Strong Shard Key**               | 사용자, tenant 등 특정 business key로 샤딩 | 다중 샤드 트랜잭션 거의 없음             | key 잘못 잡으면 hot shard 발생 |
| **Loose Shard Key + Saga**         | 샤드 경계 넘을 수 있음을 인정하고 Saga로 보상 처리   | 분산성 확보 + 복잡성 관리              | 개발 난이도 증가               |
| **Global Data + Local Shard Data** | 공통 데이터는 중앙 DB, 나머지는 샤드            | 일부 data만 central consistency | central DB 장애 시 치명적     |


# Reference