---
id: DB Sharding 전략
started: 2025-05-03
tags:
  - ✅DONE
group:
  - "[[Java Spring DB]]"
---
# DB Sharding 전략 (Database Sharding Strategies)

## 1. 개요 (Overview)
서비스가 성장하여 단일 데이터베이스 서버의 스토리지 용량이나 처리량(Throughput) 한계에 도달하면, 우리는 **스케일 업(Scale-up, 수직 확장)** 을 고려합니다. 하지만 스케일 업은 비용이 기하급수적으로 증가하며 물리적인 한계가 명확합니다.

이때 선택할 수 있는 해결책이 **샤딩(Sharding)**, 즉 **스케일 아웃(Scale-out, 수평 확장)** 입니다. 샤딩은 거대한 데이터베이스를 '샤드(Shard)'라고 불리는 여러 개의 작은 파티션으로 나누어 여러 서버에 분산 저장하는 기술입니다. 이는 성능, 용량, 가용성 문제를 동시에 해결할 수 있는 강력한 방법이지만, 시스템 복잡도를 극도로 높이는 "최후의 수단"이기도 합니다.

---

## 2. 샤딩 키와 분산 전략 (Strategies)

샤딩의 성패는 **샤딩 키(Sharding Key)** 를 어떻게 선택하고, 어떤 **분산 알고리즘**을 사용하느냐에 달려 있습니다.

### 2.1 Key Based Sharding (Hash Sharding)
- **방식**: `Shard ID = Hash(Key) % Total Shards`
- **장점**: 구현이 매우 간단하고, 데이터가 샤드 간에 비교적 **균등하게 분산(Even Distribution)** 됩니다.
- **단점**: 서버(샤드)를 추가하거나 제거하면 해시 함수 결과가 달라져서, **전체 데이터의 재배치(Resharding)** 가 필요합니다. 이는 서비스 중단 없이 수행하기 어려운 대공사입니다.
- **보완**: **Consistent Hashing** (안정 해시) 알고리즘을 사용하면 노드 추가/삭제 시 이동해야 할 데이터를 최소화할 수 있습니다.

### 2.2 Range Based Sharding
- **방식**: 특정 값의 범위를 기준으로 나눕니다. (예: `user_id` 1\~100만은 A서버, 100만\~200만은 B서버 / 날짜별 분리).
- **장점**: 구현이 직관적이며, 특정 범위 쿼리(Range Query)에 유리합니다. 샤드 추가가 쉽습니다(새 범위는 새 서버에 할당).
- **단점**: **데이터 쏠림(Data Skew)** 현상이 발생하기 쉽습니다. 예를 들어 '최근 1달 데이터'만 조회 빈도가 높다면, 해당 샤드에만 부하가 집중되어(Hotspot) 분산 효과가 떨어집니다.

### 2.3 Directory Based Sharding
- **방식**: 별도의 **Lookup Server**를 두고, 어떤 키가 어느 샤드에 있는지 맵핑 테이블을 관리합니다.
- **장점**: 샤딩 키와 무관하게 데이터를 자유롭게 이동시킬 수 있어 유연합니다. 동적으로 샤드를 쪼개거나 합칠 수 있습니다.
- **단점**: Lookup Server가 성능 병목이 되거나 단일 장애 지점(SPOF)이 될 수 있습니다. (캐싱 필수).

---

## 3. 샤딩 도입 시 문제점 (Challenges)

데이터를 쪼개는 순간, 우리가 RDBMS에서 당연하게 여기던 기능들을 잃게 됩니다.

1. **조인(Join) 불가**: 서로 다른 샤드에 있는 테이블끼리는 조인을 할 수 없습니다. 애플리케이션 레벨에서 각각 조회 후 조립하거나, 데이터를 역정규화(De-normalization)해야 합니다.
2. **분산 트랜잭션**: 여러 샤드에 걸쳐 업데이트를 해야 한다면 ACID를 보장하기 어렵습니다. 2PC(Two-Phase Commit)는 너무 느립니다. 보통은 **SAGA 패턴**을 쓰거나, 트랜잭션 범위를 단일 샤드로 제한하도록 설계를 바꿉니다.
3. **Global Unique ID**: `AUTO_INCREMENT`를 사용할 수 없습니다. (각 샤드에서 1부터 시작하면 키 충돌 발생). **Twitter Snowflake**나 **UUID** 같은 전역 유일 키 생성 전략이 필요합니다.

---

## 4. 구현 예제 (Spring Boot + AbstractRoutingDataSource)

Spring에서는 `AbstractRoutingDataSource`를 사용하여 애플리케이션 레벨에서 동적으로 데이터소스를 결정할 수 있습니다.

### 4.1 샤딩 설정
```java
public enum ShardType {
    SHARD_0, SHARD_1;
}

public class ShardRoutingDataSource extends AbstractRoutingDataSource {
    @Override
    protected Object determineCurrentLookupKey() {
        // ThreadLocal에 저장된 Shard Key를 가져와서 결정
        Long userId = ShardContextHolder.getUserId();
        int shardIndex = (int) (userId % 2); // Modulo 2
        return shardIndex == 0 ? ShardType.SHARD_0 : ShardType.SHARD_1;
    }
}
```

### 4.2 데이터소스 빈 등록
```java
@Configuration
public class DataSourceConfig {

    @Bean
    public DataSource dataSource(@Qualifier("shard0") DataSource shard0,
                                 @Qualifier("shard1") DataSource shard1) {
        Map<Object, Object> targetDataSources = new HashMap<>();
        targetDataSources.put(ShardType.SHARD_0, shard0);
        targetDataSources.put(ShardType.SHARD_1, shard1);

        ShardRoutingDataSource routingDataSource = new ShardRoutingDataSource();
        routingDataSource.setTargetDataSources(targetDataSources);
        routingDataSource.setDefaultTargetDataSource(shard0); // 기본값

        return routingDataSource;
    }
}
```

### 4.3 AOP를 활용한 컨텍스트 설정
서비스 메서드 진입 시 `user_id`를 파싱하여 `ShardContextHolder`에 넣어주는 AOP를 작성하면 비즈니스 로직 침투 없이 샤딩을 처리할 수 있습니다.

```java
@Aspect
@Component
public class ShardingAspect {
    @Before("@annotation(sharding) && args(userId,..)")
    public void setShardKey(Sharding sharding, Long userId) {
        ShardContextHolder.setUserId(userId);
    }

    @After("@annotation(sharding)")
    public void clearShardKey(Sharding sharding) {
        ShardContextHolder.clear();
    }
}
```

---

## 5. 결론 및 대안 (Conclusion)

샤딩은 **복잡도 비용이 매우 높은 기술**입니다. 도입하기 전에 다음 단계들을 먼저 고려하세요.

1. **튜닝**: 인덱스 최적화, 쿼리 튜닝.
2. **캐싱**: Redis 등을 활용해 DB 부하 감소.
3. **읽기 분산**: Master-Slave Replication 사용.
4. **수직 분할**: 테이블을 도메인별로 쪼개기 (MSA).

이 모든 것을 다 했는데도 성능이 안 나올 때 샤딩을 도입해야 합니다. 최근에는 샤딩의 복잡성을 숨겨주는 **NewSQL (CockroachDB, TiDB)** 솔루션이나 AWS Aurora 같은 Managed 서비스를 사용하는 것도 좋은 대안입니다.

# Reference
- [Naver D2 - Database Sharding](https://d2.naver.com/helloworld/14822)
- [System Design Interview - Sharding](https://www.youtube.com/watch?v=5faMjKuB9bc)
- [Spring AbstractRoutingDataSource](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/jdbc/datasource/lookup/AbstractRoutingDataSource.html)