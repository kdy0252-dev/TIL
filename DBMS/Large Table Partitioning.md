---
id: Large Table Partitioning Strategy
started: 2026-01-15
tags:
  - ✅DONE
  - DBMS
  - PostgreSQL
  - Spring
  - Liquibase
  - Partitioning
group:
  - "[[DBMS]]"
---
# 대규모 테이블 파티셔닝 전략 가이드 (PostgreSQL, Spring, Liquibase)
## 0. 개요 (Executive Summary)

데이터량이 테라바이트(TB) 단위로 급증하는 대규모 서비스 환경에서, 단일 거대 테이블(Fat Table)은 인덱스 재구성 부하, Vacuum 지연, 백업 및 복구 성능 저하 등 다양한 운영 리스크를 유발한다. **테이블 파티셔닝(Table Partitioning)** 은 하나의 논리적 테이블을 물리적으로 여러 조각으로 나누어 관리함으로써, 조회 성능을 개선하고 관리 편의성을 극대화하는 핵심 전략이다.

본 문서는 **PostgreSQL의 선언적 파티셔닝**, **Java Spring의 영속성 계층 연동**, 그리고 **Liquibase를 통한 마이그레이션 자동화**를 통합하여 실무 환경에 즉시 적용 가능한 파티셔닝 아키텍처를 제시한다.

---

## 1. 파티셔닝 핵심 개념 및 선택 기준

PostgreSQL은 10 버전부터 **선언적 파티셔닝(Declarative Partitioning)** 을 지원하며, 데이터 분할 방식에 따라 크게 세 가지 전략을 선택할 수 있다.
### 1.1 Range Partitioning (범위 분할)
- **대상**: 날짜(time-series) 또는 순차적인 숫자 기반 데이터.
- **사례**: 로그 테이블, 결제 이력, 월별 통계.
- **특이사항**: 가장 빈번하게 사용되며, 오래된 데이터를 별도 보관(Archiving)하거나 삭제하기에 최적화되어 있다.
### 1.2 List Partitioning (목록 분할)
- **대상**: 명확한 카테고리나 지역, 상태 코드 등 이산적인 값을 가질 때.
- **사례**: 거점별 유저 정보, 서비스 도메인별 설정값.
### 1.3 Hash Partitioning (해시 분할)
- **대상**: 특정 범위나 목록으로 나누기 어렵고, 데이터 부하를 여러 파티션에 균등하게 분산시키고 싶을 때.
- **사례**: 대규모 유저 ID 기반의 워크로드 분산.

---
## 2. PostgreSQL 파티셔닝 구현 (DDL Standard)

PostgreSQL에서 파티셔닝을 설계할 때는 **Parent Table(논리적 껍데기)** 과 **Partition Table(실제 데이터 저장소)** 을 구분해야 한다.

### 2.1 Parent Table 정의 (Range 기반 예시)
```sql
CREATE TABLE orders (
    id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    order_date TIMESTAMP NOT NULL,
    total_amount DECIMAL(18,2),
    status VARCHAR(20),
    PRIMARY KEY (id, order_date) -- 파티션 키가 PK에 반드시 포함되어야 함
) PARTITION BY RANGE (order_date);
```

### 2.2 Partition Table 생성 (월별 분할)
```sql
CREATE TABLE orders_2024_01 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01 00:00:00') TO ('2024-02-01 00:00:00');

CREATE TABLE orders_2024_02 PARTITION OF orders
    FOR VALUES FROM ('2024-02-01 00:00:00') TO ('2024-03-01 00:00:00');
```

---
## 3. Java Spring (JPA / Querydsl) 연동 전략
애플리케이션 레벨에서 파티션 테이블을 인지할 필요는 없으나, **Partition Pruning(불필요한 파티션 건너뛰기)** 성능을 극대화하기 위한 설계가 필요하다.

### 3.1 Entity 매핑 시 주의사항
JPA를 사용할 때, 부모 테이블의 PK 제약 조건(파티션 키 포함)을 엔티티 객체에 정확히 반영해야 한다.

```java
@Entity
@Getter
@Table(name = "orders")
public class Order {
    @EmbeddedId
    private OrderId id; // PK와 파티션 키를 포함한 복합키 구성 권장

    private Long userId;
    private BigDecimal totalAmount;
    // ...
}

@Embeddable
@NoArgsConstructor
@AllArgsConstructor
public class OrderId implements Serializable {
    private Long id;
    private LocalDateTime orderDate; // 파티션 키
}
```

### 3.2 Partition Pruning 활성화를 위한 쿼리
옵티마이저가 특정 파티션만 읽게 하려면 모든 쿼리의 `WHERE` 절에 **파티션 키**가 명시적으로 포함되어야 한다.

```java
// Querydsl 예시
public List<Order> findRecentOrders(Long orderId, LocalDateTime orderDate) {
    return queryFactory
        .selectFrom(order)
        .where(
            order.id.id.eq(orderId), 
            order.id.orderDate.eq(orderDate) // 파티션 키 조건 필수!
        )
        .fetch();
}
```

---
## 4. Liquibase를 이용한 형상 관리 및 마이그레이션

파티셔닝 환경에서 가장 큰 고충은 **미래의 파티션을 미리 생성**하는 관리 작업이다. 이를 Liquibase ChangeSet과 DB 내 Procedures를 결합하여 자동화한다.

### 4.1 Liquibase ChangeSet 구성 (부모 테이블 및 프로시저)
```xml
<changeSet id="create-orders-parent" author="antigravity">
    <sql>
        CREATE TABLE orders (
            id BIGINT NOT NULL,
            order_date TIMESTAMP NOT NULL,
            PRIMARY KEY (id, order_date)
        ) PARTITION BY RANGE (order_date);
    </sql>
</changeSet>

<changeSet id="partition-auto-creator-proc" author="antigravity">
    <sql splitStatements="false">
        CREATE OR REPLACE FUNCTION create_next_month_partition() RETURNS void AS $$
        DECLARE
            next_month_start DATE := date_trunc('month', current_date + interval '1 month');
            next_month_end DATE := date_trunc('month', current_date + interval '2 month');
            partition_name TEXT := 'orders_' || to_char(next_month_start, 'YYYY_MM');
        BEGIN
            EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF orders 
                            FOR VALUES FROM (%L) TO (%L)', 
                            partition_name, next_month_start, next_month_end);
        END;
        $$ LANGUAGE plpgsql;
    </sql>
</changeSet>
```

### 4.2 스케줄링 연동
위에서 정의한 프로시저를 매달 말일 혹은 여유 있게 실행하도록 DB 내부 스케줄러(pg_cron 등)나 애플리케이션의 `@Scheduled` 작업을 통해 연동한다.

---
## 5. 파티셔닝 운영 전략 및 유지보수

### 5.1 Partition Pruning (최적화의 정수)
- **원리**: 쿼리의 WHERE 절 조건을 보고 실행 시점에 대상 파티션만 스캔하는 기술.
- **확인**: `EXPLAIN ANALYZE` 실행 시 `Append` 노드 하위에 소수의 파티션만 나열되는지 확인.

### 2. Detach & Archive (데이터 생명주기 관리)
오래된 데이터는 `DETACH PARTITION` 명령어로 부모 테이블에서 분리한 후, 별도의 히스토리 DB로 옮기거나 압축하여 저장 공간을 효율화한다.
```sql
ALTER TABLE orders DETACH PARTITION orders_2022_12;
```

---
## 파티셔닝은 만능 해결책이 아니다
파티셔닝은 성능을 얻는 대신 다음과 같은 비용이 발생함을 인지해야 한다.
- **인덱스 전파**: 인덱스도 각 파티션마다 별도로 생성되어 전체 인덱스 관리 비용 증가.
- **무결성 제약**: 파티션 키를 포함하지 않는 유니크 제약 조건을 생성하기 어려움.
- **복잡성**: 쿼리 작성 시 항상 파티션 키를 상기해야 함.

# Reference
- **PostgreSQL Docs**: [Table Partitioning Guide (ver 17)](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- **Spring Boot/JPA**: [Handling Multi-tenancy and Partitioning](https://docs.spring.io/spring-data/jpa/docs/current/reference/html/)
- **Liquibase Best Practice**: [Managing Postgres Partitions with Liquibase](https://www.liquibase.com/blog/postgresql-partitioning)
