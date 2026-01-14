---
id: SQL 실행 전략 및 성능 최적화 가이드
started: 2026-01-14
tags:
  - ✅DONE
  - DBMS
  - SQL
  - jOOQ
  - Optimization
group:
  - "[[DBMS]]"
---
# SQL 및 jOOQ 실행 전략 최적화 가이드 (Performance Tuning Standard)

본 문서는 실무에서 발생하는 성능 저하 케이스를 분석하고, **커서(Cursor), 인덱스(Index), 조인(Join)** 의 최적 최적화 설계 방안을 전문적인 관점에서 제시한다. 단순한 문법적 지식을 넘어 데이터 인프라의 임계치를 확장하기 위한 기술적 전략을 담고 있다.

---
## Ⅰ. SQL 최적화 설계 원칙 및 기초 가이드라인
본격적인 사례 분석에 앞서, 모든 SQL 최적화의 근간이 되는 핵심 메커니즘과 범용적인 설계 원칙을 정리한다.
### 1. 인덱스(Index)의 본질: 검색 범위의 최소화
인덱스는 데이터의 물리적 위치를 기록한 별도의 정렬된 객체이다. 인덱스 최적화의 최종 목표는 **Index Full Scan**을 피하고, 탐색 비용을 최소화하는 **Index Range Scan** 또는 **Index Unique Scan**을 유도하는 데 있다.

- **B-Tree 아키텍처**: 대부분의 DBMS에서 사용하는 구조로, 등가( ` =`)와 범위(`>`, `<`, `BETWEEN`) 검색에 최적화되어 있다.
- **SARG (Searchable Argument) 준수**: 인덱스를 태우기 위해서는 조건절의 컬럼을 가공해서는 안 된다. 컬럼은 순수하게 유지하고 비교 대상을 가공하는 것이 정석이다.
- **선행 컬럼(Leading Column) 전략**: 결합 인덱스는 선행 컬럼이 조건절에 포함되어야만 유효하다. 카디널리티(데이터 중복도)가 낮은 필드보다는 검색 변별력이 높은 필드를 전면에 배치하는 것이 유리하다.

### 2. 조인(Join) 알고리즘: 데이터 결합 효율성
조인은 두 집합을 물리적으로 연결하는 과정으로, 데이터셋의 크기와 인덱스 가용성에 따라 적절한 알고리즘을 선택해야 한다.

- **Nested Loop Join (NL)**: 외부 레코드마다 내부 테이블을 탐색하는 방식이다. 소량의 드라이빙 테이블과 인덱스가 확보된 내부 테이블 간의 결합에 가장 최적화되어 있다.
- **Hash Join**: 대량의 데이터셋 간 결합에 유리하다. 한 테이블을 메모리 내 해시 테이블로 빌드한 뒤 매칭하므로, **work_mem**의 적절한 할당이 성능의 성패를 가른다.
- **Sort Merge Join**: 양측의 데이터를 정렬한 뒤 순차적으로 병합한다. 이미 조인 키로 정렬된 대용량 데이터이거나 범위 기반 조인이 필요한 특수 상황에서 선택된다.

### 3. 페이징 및 커서 제어: 리소스 점유의 최적화
커서는 데이터 셋의 흐름을 제어하는 논리적 포인터이다. 무분별한 페이징 설계는 DB CPU와 I/O 자원을 고갈시키는 주범이다.

- **오프셋(Offset) 방식**: 사용은 간편하나 페이지 심도가 깊어질수록 버려지는 데이터가 많아져 성능이 지수적으로 하락한다.
- **키셋(Keyset / Seek) 방식**: 마지막 조회 데이터의 식별자를 기준으로 다음 데이터를 탐색한다. 인덱스 점프를 통해 데이터 양에 관계없이 일정한 응답 속도(Constant Time)를 보장한다.

---
## Ⅱ. 실무 시나리오별 성능 개선 전략 (Case Study)

### SECTION 1. Indexing Tactics (인덱싱 정밀 튜닝)

### Case 01. 부분 인덱스(Partial Index)
- **유리한 상황**: 전체 데이터 중 특정 조건(예: 미결제, 활성 상태)에 해당하는 소량의 데이터만 주로 조회할 때.

#### [Bad] 전체 인덱스
```sql
CREATE INDEX idx_orders_status ON orders(status);
```

#### [Best] 부분 인덱스
```sql
CREATE INDEX idx_orders_active ON orders(id) 
WHERE status = 'PROCESSING';
```
- **성능 이득**: 인덱스 크기가 대폭 감소(90% 이상)하며, DML 성능 저하를 최소화하고 스캔 속도를 극대화함.

---
### Case 02. 기능 인덱스(Expression Index)
- **유리한 상황**: 검색 조건에서 컬럼 가공(함수 사용)이 불가피할 때.

#### [Bad] 좌변 가공 (Index 무력화)
```sql
SELECT * FROM users WHERE LOWER(email) = 'test@example.com';
```

#### [Best] 기능 인덱스 활용
```sql
CREATE INDEX idx_user_email_lower ON users (LOWER(email));
```
```java
// jOOQ 구현
dsl.selectFrom(USERS)
   .where(lower(USERS.EMAIL).eq(email.toLowerCase()))
   .fetch();
```
- **성능 이득**: 함수 연산 결과를 미리 인덱싱하여 Full Scan을 지양하고 Index Scan을 유도함.

---
### Case 03. INCLUDE 커버링 인덱스
- **유리한 상황**: 조회 컬럼이 적고, 테이블 원본(Heap) 접근 횟수가 병목일 때.

#### [Bad] 일반 인덱스
```sql
CREATE INDEX idx_orders_user ON orders(user_id);
-- 조회 시 테이블 접근 발생 (Table Access)
```

#### [Best] INCLUDE 인덱스
```sql
CREATE INDEX idx_orders_covering ON orders(user_id) 
INCLUDE (total_price, ordered_at);
```
- **성능 이득**: **Index Only Scan**을 통해 테이블 데이터 블록 접근을 차단하여 I/O 비용 획기적 절감.

---
### Case 04. GIN Index (Array Searching)
- **유리한 상황**: 태그, 권한 등 배열 형태의 데이터를 검색할 때.

#### [Bad] LIKE 검색
```sql
SELECT * FROM posts WHERE tags LIKE '%#java%';
```

#### [Best] GIN Index & Overlap
```sql
CREATE INDEX idx_tags_gin ON posts USING GIN (tags);
-- WHERE tags @> ARRAY['java']
```
- **성능 이득**: 인덱스를 통한 비정형 데이터 검색 속도 수십 배 향상.

---
### Case 05. BRIN Index (Block Range Index)
- **유리한 상황**: 로그 파일처럼 데이터가 시간/ID 순으로 물리적으로 정렬되어 삽입되는 초대형 테이블.

#### [Bad] 일반 B-Tree Index
```sql
CREATE INDEX idx_logs_created ON big_logs(created_at);
-- 인덱스 크기가 수십 GB에 달함
```

#### [Best] BRIN Index
```sql
CREATE INDEX idx_logs_brin ON big_logs USING BRIN (created_at);
```
- **성능 이득**: B-Tree 대비 1% 미만의 인덱스 크기로 관리 비용은 낮추고 초대형 범위 검색 성능 확보.

---
## 2. Join & Subquery (조인 및 서브쿼리)

### Case 06. NOT EXISTS vs NOT IN
- **유리한 상황**: 서브쿼리 결과에 NULL이 포함될 수 있는 대량 데이터 필터링.

#### [Bad] NOT IN
```sql
SELECT * FROM users WHERE id NOT IN (SELECT user_id FROM blacklists);
```

#### [Best] NOT EXISTS
```sql
SELECT * FROM users u 
WHERE NOT EXISTS (SELECT 1 FROM blacklists b WHERE b.user_id = u.id);
```
- **성능 이득**: NULL 안정성 확보 및 옵티마이저가 Hash Anti-Join을 선택하기 유리해짐.

---
### Case 07. EXISTS vs DISTINCT Join
- **유리한 상황**: 1:N 관계에서 마스터 정보의 존재 여부만 확인할 때.

#### [Bad] DISTINCT Join
```sql
SELECT DISTINCT u.* FROM users u JOIN orders o ON u.id = o.user_id;
```

#### [Best] EXISTS Semi-Join
```sql
SELECT * FROM users u 
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id);
```
- **성능 이득**: 중복 데이터 생성 후 제거하는 부하를 방지하고 첫 번째 매칭에서 탐색 중단(Short-circuit).

---
### Case 08. LATERAL JOIN (Row-wise Optimization)
- **유리한 상황**: 행별로 Top-N 결과를 함께 조회해야 할 때.

#### [Bad] 상관 서브쿼리
```sql
SELECT u.name, (SELECT price FROM orders o WHERE o.user_id = u.id ORDER BY dt DESC LIMIT 1) FROM users u;
```

#### [Best] CROSS JOIN LATERAL
```sql
SELECT u.name, o.price 
FROM users u, 
LATERAL (SELECT price FROM orders WHERE user_id = u.id ORDER BY dt DESC LIMIT 1) o;
```
- **성능 이득**: 실행 계획에서 루프 조인 최적화가 적용되어 대량 조회 시 성능 임계치 상향.

---
### Case 09. Anti-Join (LEFT JOIN + IS NULL)
- **유리한 상황**: 특정 집합에 포함되지 않은 데이터 수집.

#### [Bad] Full Outer Join 후 필터링
```sql
SELECT a.* FROM a FULL JOIN b ON a.id = b.a_id WHERE b.id IS NULL;
```

#### [Best] LEFT JOIN & IS NULL
```sql
SELECT a.* FROM a LEFT JOIN b ON a.id = b.a_id WHERE b.id IS NULL;
```
- **성능 이득**: 옵티마이저가 불필요한 Full Outer Scan을 피하고 Left Anti-Join으로 최적화.

---
### Case 10. Scalar Subquery to Join 변환
- **유리한 상황**: SELECT 절의 서브쿼리가 전체 성능의 병목일 때.

#### [Bad] SELECT절 서브쿼리
```sql
SELECT u.id, (SELECT count(*) FROM orders o WHERE o.user_id = u.id) FROM users u;
```

#### [Best] Group By Join
```sql
SELECT u.id, COUNT(o.id) 
FROM users u LEFT JOIN orders o ON u.id = o.user_id 
GROUP BY u.id;
```
- **성능 이득**: 행마다 쿼리가 실행되는 N+1 문제를 집합 연산으로 변환하여 I/O 최소화.

---
## 3. Pagination Strategy (페이징 최적화)

### Case 11. Keyset Pagination (Seek Method)
- **유리한 상황**: 무한 스크롤 등 대용량 데이터의 연속 조회.

#### [Bad] OFFSET
```sql
SELECT * FROM logs ORDER BY id DESC OFFSET 100000 LIMIT 20;
```

#### [Best] jOOQ seek()
```java
dsl.selectFrom(LOGS)
   .orderBy(LOGS.ID.desc())
   .seek(lastSeenId)
   .limit(20).fetch();
```
- **성능 이득**: I/O 낭비 없이 인덱스 리프에서 즉시 결과 반환(Constant Time).

---
### Case 12. Deferred Join (지연 조인)
- **유리한 상황**: Keyset이 불가능한 복잡한 소팅 조건에서 Large Offset 접근 시.

#### [Bad] 전체 데이터 로드 후 Offset
```sql
SELECT * FROM large_table ORDER BY score DESC OFFSET 10000 LIMIT 20;
```

#### [Best] ID만 먼저 필터링 후 Join
```sql
SELECT * FROM large_table t
JOIN (SELECT id FROM large_table ORDER BY score DESC OFFSET 10000 LIMIT 20) as ids ON t.id = ids.id;
```
- **성능 이득**: 데이터 원본(Table) 접근 횟수를 극한으로 줄여 응답 속도 보장.

---
### Case 13. Estimated Count
- **유리한 상황**: 전체 건수 조회가 불필요하게 정밀할 필요가 없는 UI 대시보드.

#### [Bad] SELECT COUNT(*)
```sql
SELECT COUNT(*) FROM huge_table;
-- 수 분 소요
```

#### [Best] 통계 정보 활용
```sql
SELECT reltuples::bigint FROM pg_class WHERE relname = 'huge_table';
```
- **성능 이득**: 0ms에 가까운 속도로 대략적인 전체 건수 반환.

---
### Case 14. Forward/Backward Keyset
- **유리한 상황**: 이전 페이지와 다음 페이지 이동이 모두 가능해야 할 때.

#### [Best] jOOQ seekBefore/seekAfter
```java
dsl.selectFrom(T).orderBy(T.ID.desc()).seekAfter(lastId).limit(20); // Next
dsl.selectFrom(T).orderBy(T.ID.asc()).seekAfter(firstId).limit(20); // Prev (결과 반전 필요)
```

---
### Case 15. Keyset with Nullable columns
- **유리한 상황**: 정렬 컬럼에 NULL이 포함될 수 있는 페이징.

#### [Best] NULLS LAST 정렬 보강
```sql
ORDER BY created_at DESC NULLS LAST, id DESC;
```
- **성능 이득**: 정렬 순서의 정석을 유지하여 페이징 시 데이터 누락 및 인덱스 파편화 방지.

---
## 4. Aggregation & Window (집계 및 윈도우)

### Case 16. FILTER Clause (SQL Standard)
- **유리한 상황**: 조건부 카운트/합계 다중 산출.

#### [Bad] CASE WHEN
```sql
SUM(CASE WHEN type = 'A' THEN 1 ELSE 0 END)
```

#### [Best] FILTER
```sql
COUNT(*) FILTER (WHERE type = 'A')
```
- **성능 이득**: 엔진 수준에서 가독성 및 필터 탐색 최적화.

---
### Case 17. 행 간 연산을 위한 LAG/LEAD
- **유리한 상황**: 이전/다음 행과의 데이터 비교 분석.

#### [Bad] Self Join
```sql
SELECT curr.val - prev.val FROM t curr JOIN t prev ON curr.id = prev.id + 1;
```

#### [Best] LAG() Window Function
```sql
SELECT val - LAG(val) OVER (ORDER BY id) FROM t;
```
- **성능 이득**: 테이블 스캔을 1회로 단축하여 리소스 소모 50% 절감.

---
### Case 18. ROLLUP을 통한 다차원 집계
- **유리한 상황**: 소계와 총계를 한 번에 조회해야 하는 정산 쿼리.

#### [Bad] UNION ALL 여러 번
```sql
SELECT cat, sum(val) FROM t GROUP BY cat
UNION ALL
SELECT NULL, sum(val) FROM t;
```

#### [Best] GROUP BY ROLLUP
```sql
GROUP BY ROLLUP(category, sub_category)
```
- **성능 이득**: 단일 정렬/해시 연산으로 모든 집계 결과 산출.

---
### Case 19. Filtered Window Aggregate
- **유리한 상황**: 누적 합산 중 특정 조건만 포함.

#### [Best]
```sql
SUM(amt) OVER (PARTITION BY user_id ORDER BY dt ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
```

---
### Case 20. Percentile Calculation (정밀도 제어)
- **유리한 상황**: 백분위수 산출 시.

#### [Best] percent_rank() vs percentile_cont()
- **Rationale**: 정렬 기반 정밀 연산이 필요한 상황에서 윈도우 함수를 통해 분산 처리 유도.

---
## 5. DML & Batch (데이터 조작)

### Case 21. UPSERT (ON CONFLICT)
- **유리한 상황**: 중복 키 유입 시 업데이트 수행.

#### [Bad] SELECT then INSERT/UPDATE
```java
if (exists()) update() else insert();
```

#### [Best] jOOQ onConflict()
```java
dsl.insertInto(T).values(...).onConflict(T.ID).doUpdate().set(...)
```
- **성능 이득**: 네트워크 왕복 1회로 단축 및 동시성 정합성 확보.

---
### Case 22. jOOQ batchInsert()
- **유리한 상황**: 수천 건 이상의 데이터 삽입.

#### [Bad] Loop execute()
```java
for (var r : records) r.execute();
```

#### [Best] Batch 실행
```java
dsl.batchInsert(records).execute();
```
- **성능 이득**: 드라이버 레벨에서 `PreparedStatement` 재사용 및 통신 횟수 획기적 축소.

---
### Case 23. Windowed Chunk Deletion
- **유리한 상황**: 수억 건 이상의 로그 데이터 삭제 시 트랜잭션 로그 폭증 방지.

#### [Bad] 대량 DELETE
```sql
DELETE FROM logs WHERE created_at < '2023-01-01';
-- Table Lock 및 WAL 폭증
```

#### [Best] Chunk 기반 삭제
```sql
DELETE FROM logs WHERE id IN (SELECT id FROM logs WHERE ... LIMIT 5000);
-- 반복 실행
```
- **성능 이득**: 짧은 트랜잭션 유지로 서비스 가용성 확보 및 락 점유 최소화.

---
### Case 24. RETURNING 절 활용
- **유리한 상황**: 삽입된 자동증가 PK나 계산된 컬럼을 즉시 가져와야 할 때.

#### [Bad] INSERT 후 다시 SELECT
```java
insert(r); select(id);
```

#### [Best] RETURNING
```sql
INSERT INTO t (val) VALUES (1) RETURNING id;
```
- **성능 이득**: DB 내부에서 즉시 반환하여 추가적인 Index Scan 오버헤드 제거.

---
### Case 25. TEMP TABLE Bulk Load
- **유리한 상황**: 대량의 정합성 체크 혹은 매칭 작업 시.

#### [Best]
```sql
CREATE TEMPORARY TABLE t_tmp ON COMMIT DROP AS ...
-- COPY 명령어로 대량 인입 후 Join 처리
```

---
## 6. Searching & Patterns (검색 최적화)

### Case 26. Full-Text Search (tsvector)
- **유리한 상황**: 대량의 텍스트 내 키워드 검색.

#### [Bad] LIKE '%word%'
```sql
WHERE content LIKE '%java%';
```

#### [Best] ts_vector & ts_query
```sql
WHERE to_tsvector('english', content) @@ to_tsquery('english', 'java');
```
- **성능 이득**: 인덱싱된 텍스트 검색을 통해 수백 배의 성능 향상.

---
### Case 27. JSONB path_ops Index
- **유리한 상황**: 복잡한 JSON 데이터 내 특정 경로 검색.

#### [Bad] 일반 jsonb_ops
```sql
CREATE INDEX idx_json ON metadata USING GIN (info);
```

#### [Best] jsonb_path_ops
```sql
CREATE INDEX idx_json_path ON metadata USING GIN (info jsonb_path_ops);
```
- **성능 이득**: 인덱스 크기가 작아지고 범용 `@>` 연산 검색 속도 극대화.

---
### Case 28. 접두사 검색 최적화
- **유리한 상황**: `LIKE 'ABC%'` 형태의 검색.

#### [Best] text_pattern_ops
```sql
CREATE INDEX idx_name_prefix ON users (name text_pattern_ops);
```
- **성능 이득**: C-Collation 환경이 아니더라도 B-Tree 인덱스를 통한 Range 스캔 보장.

---
### Case 29. Regular Expression Index
- **유리한 상황**: 정규표현식 검색 시.

#### [Best] pg_trgm (Trigram) 확장 사용
```sql
CREATE INDEX idx_trgm ON t USING GIN (content gin_trgm_ops);
-- WHERE content ~ 'regexp'
```

---
### Case 30. Phonetic Search (Soundex)
- **유리한 상황**: 발음이 비슷한 이름 검색.

#### [Best] fuzzystrmatch 확장 활용
```sql
WHERE soundex(name) = soundex('Antigravity');
```

---
## 7. Logic & Optimizer Tuning (로직 조율)

### Case 31. CTE Materialization 제어
- **유리한 상황**: 복잡한 쿼리 분리 후 Filter Push-down 유도.

#### [Best] NOT MATERIALIZED
```sql
WITH sub AS NOT MATERIALIZED (SELECT * FROM big) SELECT * FROM sub WHERE id = 1;
```

---
### Case 32. Case-Insensitive Collation
- **유리한 상황**: 모든 문자열 검색이 대소문자 구분이 없을 때.

#### [Best]
```sql
CREATE TABLE t (name text COLLATE "icu" (deterministic=false));
```
- **성능 이득**: `LOWER()` 함수 사용 없이도 인덱스 검색 및 정렬 속도 유지.

---
### Case 33. In-List to Join 변환
- **유리한 상황**: `IN (...)` 절의 파라미터가 수천 개 이상일 때.

#### [Bad] 초대형 IN Clause
```sql
WHERE id IN (1, 2, ..., 10000)
```

#### [Best] VALUES / UNNEST Join
```java
// jOOQ unnest 활용
dsl.selectFrom(T).where(T.ID.in(dsl.select(unnest(ids)))).fetch();
```
- **성능 이득**: 파싱 오버헤드 감소 및 해시 조인 선택 유도.

---
### Case 34. Scalar Subquery Caching 유도
- **유리한 상황**: 조인 대신 스칼라 서브쿼리가 더 효율적인 희소 데이터 조회.

#### [Best] SELECT절 위치 조절
- **Rationale**: 결정론적 함수의 경우 커널이 결과를 캐싱하여 반복 연산을 줄이는 효과 활용.

---
### Case 35. Recursive CTE Depth 제한
- **유리한 상황**: 계층형 쿼리의 무한 루프 방지 및 성능 제어.

---
## 8. Advanced Concurrency (고급 동시성)

### Case 36. SKIP LOCKED (Job Queue)
- **유리한 상황**: 고성능 메시지 큐 시스템 구현.

#### [Best] jOOQ skipLocked()
```java
dsl.selectFrom(Q).forUpdate().skipLocked().fetchLimit(1);
```
- **성능 이득**: 경합 없는 동시 처리 인스턴스 확장 가능.

---
### Case 37. Advisory Lock (Lock partitioning)
- **유리한 상황**: 특정 비즈니스 키에 대한 정밀한 분산 락.

#### [Best] pg_advisory_xact_lock()
```sql
SELECT pg_advisory_xact_lock(hash_id);
```

---
### Case 38. Parallel Query Tuning
- **유리한 상황**: 대용량 배치 집계 전용.

#### [Best]
```sql
SET max_parallel_workers_per_gather = 4;
```

---
각 사례의 성능 차이는 데이터의 카디널리티와 스토리지 스펙에 따라 달라질 수 있습니다. 반드시 실제 운영 환경에 맞는 방식을 사용해야합니다.