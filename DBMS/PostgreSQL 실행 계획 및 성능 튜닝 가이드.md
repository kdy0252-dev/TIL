---
id: PostgreSQL 실행 계획 및 성능 튜닝 가이드
started: 2026-01-23
tags:
  - ✅DONE
group:
  - "[[PostgreSQL]]"
---

# PostgreSQL 실행 계획 및 성능 튜닝 가이드 (Java/JPA)

애플리케이션의 성능 병목 현상은 대부분 데이터베이스 I/O에서 발생합니다. 본 가이드에서는 PostgreSQL의 실행 계획(Execution Plan) 분석 방법과 Java(JDBC/JPA) 환경에서의 체계적인 성능 튜닝 프로세스를 다룹니다.

---

## 1. PostgreSQL 실행 계획(Execution Plan) 확인 및 분석

실행 계획은 쿼리가 어떻게 물리적으로 수행될지 DBMS가 결정한 로드맵입니다.

### 1.1 EXPLAIN 명령어 활용
가장 기본적인 도구는 `EXPLAIN`입니다.

- **EXPLAIN**: 실행 계획만 보여주며 실제로 쿼리를 수행하지는 않습니다.
- **EXPLAIN ANALYZE**: 쿼리를 **실제로 실행** 하여 각 단계별 수행 시간과 실제 행 수를 측정합니다. (주의: 수정/삭제 쿼리는 트랜잭션 처리가 필요함)
- **EXPLAIN (ANALYZE, BUFFERS)**: 메모리 버퍼 히트율까지 포함하여 I/O 비용을 정밀하게 분석할 때 사용합니다.

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders WHERE customer_id = 101 AND status = 'SHIPPED';
```

### 1.2 주요 지표 및 클루
- **Cost**: 쿼리 수행에 필요한 상대적 비용 단위. (startup cost .. total cost)
- **Actual Time**: 실제 소요 시간 (ms).
- **Rows**: 예상 행 수 vs 실제 행 수. 이 차이가 크면 통계 정보가 낡은 것이므로 `ANALYZE`가 필요합니다.
- **Scan Types**: 
    - `Seq Scan`: 전체 테이블 스캔 (잠재적 병목).
    - `Index Scan`: 인덱스를 타지만 데이터 블록도 읽음.
    - `Index Only Scan`: 커버링 인덱스가 동작 중임 (최상).
    - `Bitmap Index/Heap Scan`: 여러 인덱스 결과를 조합할 때 사용.

---

## 2. 성능 튜닝의 방향 및 로드맵

성능 튜닝은 **"덜 읽고, 덜 연산하고, 효율적으로 연결하는 것"** 입니다. 아래 순서대로 접근하는 것이 가장 효율적입니다.

### [1단계] 쿼리 자체의 문제 식별 (Application Side)
가장 먼저 확인해야 할 것은 **"내가 의도한 만큼만 읽고 있는가?"**입니다.
- **불필요한 컬럼 제거**: `SELECT *` 대신 필요한 컬럼만 명시.
- **조건절(WHERE) 최적화**: 인덱스를 타지 못하는 함수 사용, 타입 불일치 제거.
- **N+1 문제**: JPA 사용 시 가장 흔한 원인. 페치 조인(Fetch Join)으로 해결.

### [2단계] 인덱스 및 실행 계획 최적화 (DB Side)
인덱스만 잘 설계해도 90% 이상의 성능 문제는 해결됩니다.
- **복합 인덱스 설계**: 카디널리티가 높은 컬럼을 앞쪽에 배치.
- **커버링 인덱스 도입**: 테이블 access를 줄여 I/O 최소화.
- **함수 기반 인덱스**: 필득 가공이 불가피할 때 사용.

### [3단계] 조인 방식 및 연산 최적화
데이터량이 많을 때 조인 전략이 성능을 가릅니다.
- **Nested Loop**: 소량 데이터 조인 시 유리.
- **Hash Join**: 대량 데이터 조인 시 메모리에 해시 테이블을 만들어 수행.
- **Merge Join**: 두 테이블이 정렬되어 있을 때 유리.

---

## 3. Java JDBC/JPA 환경에서의 실전 튜닝

애플리케이션 레이어에서는 SQL이 암묵적으로 생성되는 경우가 많으므로 더 세밀한 관찰이 필요합니다.

### 3.1 로깅 및 모니터링
튜닝의 시작은 현상 파악입니다.

```yaml
# application.yml
spring:
  jpa:
    properties:
      hibernate:
        show_sql: true
        format_sql: true
        use_sql_comments: true # 쿼리 소스 파악 용이
        generate_statistics: true # 세션별 실행 통계 출력
logging:
  level:
    org.hibernate.SQL: debug
    org.hibernate.type.descriptor.sql.BasicBinder: trace # 파라미터 확인
```

### 3.2 JPA 성능 튜닝 포인트
1. **Fetch Join**: 연관된 엔티티를 한 번에 가져와 N+1 쿼리를 방지합니다.
   ```java
   @Query("select o from Order o join fetch o.member")
   List<Order> findAllWithMember();
   ```
2. **DTO Projection**: 커버링 인덱스 효율을 극대화하기 위해 엔티티가 아닌 필요한 필드만 담은 DTO로 조회합니다.
3. **Batch Size 설정**: `IN` 절을 통해 여러 데이터를 묶어서 조회합니다.
   ```yaml
   spring.jpa.properties.hibernate.default_batch_fetch_size: 100
   ```
4. **Read-Only Transaction**: `@Transactional(readOnly = true)`를 사용하여 스냅샷 저장 및 더티 체킹 오버헤드를 줄입니다.

### 3.3 JDBC 직접 호출 시 튜닝
1. **PreparedStatement 사용**: 쿼리 파싱 비용을 줄이고 실행 계획 캐시를 활용합니다.
2. **Fetch Size 조절**: 한 번에 가져올 로우(Row) 수를 설정하여 네트워크 라운드 트립을 제어합니다.
   ```java
   statement.setFetchSize(100);
   ```
3. **Batch Update**: 대량의 `INSERT/UPDATE` 시에는 반드시 `addBatch()`와 `executeBatch()`를 사용하여 통신 횟수를 줄입니다.

---

## 4. 튜닝 프로세스 요약 (Cheat Sheet)

1. **Slow Query 식별**: `pg_stat_statements`나 애플리케이션 로그를 통해 느린 쿼리 추출.
2. **EXPLAIN ANALYZE 실행**: 실제 병목 구간(Scan, Join, Aggregate) 확인.
3. **Access 패턴 분석**: `Seq Scan`이 발생하는 원인 파악 및 인덱스 추가/수정.
4. **어플리케이션 로직 검토**: 불필요한 호출(N+1), 과도한 데이터 로드(`SELECT *`) 제거.
5. **결과 검증**: 튜닝 후 다시 실행 계획을 확인하여 비용(Cost) 및 시간(Time) 비교.