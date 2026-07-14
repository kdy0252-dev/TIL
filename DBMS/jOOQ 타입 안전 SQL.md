---
id: jOOQ 타입 안전 SQL
started: 2026-05-19
tags:
  - ✅DONE
  - DBMS
  - Java
  - SQL
group:
  - "[[DBMS]]"
---
# jOOQ: 복잡한 통계 쿼리를 위한 타입 안전 SQL

## 1. 개요 (Overview)
**jOOQ**는 SQL의 표현력을 유지하면서 Java DSL로 Query를 작성하는 도구입니다. JPA가 Aggregate의 상태 변경과 Persistence Lifecycle에 강하다면, jOOQ는 복잡한 Join, 집계, Window Function과 조회 Projection에 적합합니다.

---

## 2. JPA와 jOOQ 선택

| 요구 | JPA | jOOQ |
|---|---|---|
| Aggregate 저장·변경 감지 | 적합 | 직접 처리 필요 |
| 단순 CRUD | 적합 | 가능하지만 장황할 수 있음 |
| 복잡한 통계·Window Function | 우회가 많음 | 적합 |
| SQL 제어·실행 계획 튜닝 | 제한적 | 적합 |
| Database-specific 기능 | Native Query 필요 | DSL로 표현 가능 |

한 프로젝트에서 Command는 JPA, 복잡한 Query는 jOOQ를 사용하는 조합이 가능합니다.

---

## 3. 기본 예제

```java
return dsl
        .select(
                WORKLOG.WORK_DATE,
                count().as("driving_count"),
                sum(WORKLOG.DISTANCE).as("total_distance")
        )
        .from(WORKLOG)
        .where(WORKLOG.WORK_DATE.between(startDate, endDate))
        .groupBy(WORKLOG.WORK_DATE)
        .orderBy(WORKLOG.WORK_DATE)
        .fetch(record -> new DailyWorklogRow(
                record.get(WORKLOG.WORK_DATE),
                record.get("driving_count", Integer.class),
                record.get("total_distance", Long.class)
        ));
```

조회 결과는 Domain Entity보다 Query 전용 Row나 Projection으로 매핑합니다.

---

## 4. 실무 사례 적용 관점
이 사례의 `metrics` 모듈은 테넌트별 `DSLContext`를 생성하여 업무 원본 Schema의 통계와 Outbox 데이터를 읽습니다. Adapter가 Tenant Context를 선택하고 jOOQ Query 결과를 Metrics의 Application Model로 변환합니다.

```text
Metrics Use Case
  -> Query Out Port
  -> EuTenantJooqExecutor
  -> tenant schema DSLContext
  -> SQL
  -> Projection / Snapshot
```

Schema 이름은 Bind Parameter로 전달할 수 없으므로 검증된 Tenant Registry에서만 선택하고 외부 입력을 Identifier로 직접 조합하지 않아야 합니다.

---

## 5. 트랜잭션과 성능
- Spring Transaction과 동일 DataSource를 사용하도록 구성합니다.
- 대량 조회는 `fetchSize`와 Streaming을 검토합니다.
- 쿼리 수가 많아지면 Generated Code 또는 공통 Table Alias 전략을 정합니다.
- SQL Logging에는 Bind Value의 개인정보 노출을 주의합니다.
- 실행 계획과 Index를 실제 데이터 분포로 검증합니다.

---

## 6. Code Generation과 Dynamic Schema
jOOQ는 DB Schema에서 Table·Column Type을 읽어 Q-Type과 유사한 Generated Class를 만들 수 있습니다.

```text
Database Schema
  -> jOOQ Code Generator
  -> Tables.WORKLOG
  -> 타입 안전 DSL
```

Schema-per-tenant처럼 Table 구조는 같고 Schema 이름만 다르면 Generated Table 정의와 Runtime Schema Mapping을 조합할 수 있습니다. 이 사례처럼 동적 Tenant Context가 중요한 경우 Identifier 검증과 DSLContext 생성 책임을 전용 Executor에 모읍니다.

## 7. Record Mapping

```java
record DailyMetric(LocalDate date, long count, BigDecimal fare) {
}

List<DailyMetric> result = query.fetch(Records.mapping(DailyMetric::new));
```

Column 순서와 Constructor 순서가 맞아야 하는 Mapping은 필드 추가 시 실수하기 쉽습니다. 명시적인 Alias와 Mapper를 사용하고 Test로 Result Shape을 검증합니다.

## 8. Window Function
통계에서는 Group By만으로 표현하기 어려운 누적·순위·이전 값 비교가 필요합니다.

```java
Field<BigDecimal> cumulativeFare = sum(PAYMENT.FARE)
        .over(partitionBy(PAYMENT.TENANT_ID)
                .orderBy(PAYMENT.PAID_AT))
        .as("cumulative_fare");
```

jOOQ는 SQL 구조를 그대로 표현하므로 Native Query 문자열보다 조합과 Refactoring이 쉽습니다.

## 9. Batch와 Streaming
- 대량 Insert·Update는 jOOQ Batch API와 JDBC Batch Size를 사용합니다.
- 대량 Read는 Cursor·Stream을 사용하되 Transaction과 Connection 수명을 명시합니다.
- Stream을 닫기 전까지 Connection이 반환되지 않을 수 있습니다.
- 전체 결과를 `fetch()`한 뒤 Java에서 Grouping하지 말고 가능한 집계는 DB에서 수행합니다.

## 10. Query Timeout과 Cancellation
복잡한 통계 Query에는 Statement Timeout을 설정합니다. HTTP 요청 취소가 JDBC Query 취소로 항상 이어진다고 가정하지 않습니다. Timeout 뒤에도 DB에서 Query가 실행 중인지 `pg_stat_activity`로 확인합니다.

Online Query와 Batch Query의 Pool·Timeout을 분리하면 긴 통계가 업무 API Connection을 고갈시키는 것을 막을 수 있습니다.

## 11. SQL Injection과 Identifier
Value는 Bind Parameter로 안전하게 전달하지만 Table·Schema·Sort Column 같은 Identifier는 Bind할 수 없습니다. 외부 문자열을 `.formatted()`로 조합하지 않고 Registry·Enum·Generated Type으로 제한합니다.

## 12. JPA와 같은 Transaction 사용
동일 DataSource와 Spring Transaction Manager를 사용하면 JPA 변경과 jOOQ Query를 한 Transaction에 포함할 수 있습니다. 다만 JPA Persistence Context의 미Flush 변경은 jOOQ에서 보이지 않을 수 있습니다.

```text
JPA Entity 변경
  -> 필요 시 flush
  -> jOOQ Query
```

두 기술을 같은 Use Case에서 섞을 때 Flush 순서와 Cache 일관성을 Test합니다.

## 13. 테스트 전략
- PostgreSQL Testcontainers로 실제 Dialect를 검증합니다.
- Generated SQL과 Bind 값을 필요 시 확인합니다.
- Tenant Schema 전환과 Connection 반환을 테스트합니다.
- 빈 결과, Null Aggregate, Time Zone 경계를 확인합니다.
- Production 규모 Data로 Explain Analyze를 비교합니다.

---

## 14. 실무 사례 적용 진단과 개선 과제

Metrics Module은 복잡한 Ledger·Aggregation SQL에 jOOQ를 사용하지만 일부 SQL 문자열과 생성 Code의 Schema Version 정합성을 계속 관리해야 합니다. 동적 Tenant Schema와 Generated Table이 어긋나면 Compile은 성공해도 Runtime 오류가 날 수 있습니다.

Migration 적용 후 Code Generation을 CI에서 재현하고 생성물 Drift를 검사합니다. Identifier는 Allowlist로 제한하고 Value는 Bind Parameter를 사용합니다. 대량 집계 Query에는 Statement Timeout, 실행 계획 Snapshot, Chunk Size와 재시작 지점을 둡니다.

완료 기준은 Changelog와 Generated Code 불일치가 CI에서 실패하고, 주요 집계 SQL의 실행 계획·P95가 데이터 규모별로 관리되며, 실패 Chunk만 멱등 재처리할 수 있는 상태입니다.

---

# Reference
- [jOOQ Manual](https://www.jooq.org/doc/latest/manual/)
- [[SQL 실행 전략 및 성능 최적화 가이드]]
- [[Projection과 Hydration]]
