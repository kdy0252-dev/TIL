---
id: 커버링 인덱스
started: 2026-01-23
tags:
  - ✅DONE
group:
  - "[[커버링 인덱스]]"
---

# 커버링 인덱스(Covering Index)

데이터베이스 성능 최적화의 꽃이라고 불리는 **커버링 인덱스(Covering Index)**는 쿼리를 실행할 때 필요한 모든 데이터를 인덱스 자체에서만 찾아낼 수 있는 상태를 의미합니다. 본 문서에서는 커버링 인덱스의 개념부터 내부 작동 원리, 실제 적용 사례 및 성능 최적화 전략까지 상세하게 다룹니다.

---

## 1. 커버링 인덱스의 정의

### 1.1 기본 개념
일반적인 쿼리 실행 과정에서는 인덱스를 통해 데이터의 위치(RID 또는 Primary Key)를 찾은 후, 실제 데이터 페이지(Heap Memory 또는 Disk Block)에 접근하여 필요한 컬럼 값을 가져옵니다. 이를 **테이블 랜덤 액세스(Table Random Access)** 라고 합니다.

반면, **커버링 인덱스**는 쿼리에서 `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY` 등에 사용되는 모든 컬럼이 인덱스의 구성 요소로 포함되어 있어, 실제 테이블 데이터에 접근할 필요 없이 인덱스 페이지 내의 정보만으로 결과를 반환할 수 있는 상태를 말합니다.

### 1.2 왜 중요한가?
디스크 I/O 관점에서 테이블 랜덤 액세스는 매우 비용이 큰 작업입니다. 커버링 인덱스를 활용하면 이 단계를 완전히 생략할 수 있기 때문에, 처리 속도가 비약적으로 향상됩니다. 특히 대량의 데이터를 스캔해야 하는 통계성 쿼리나 페이징 처리에서 그 진가를 발휘합니다.

---

## 2. 인덱스 구조와 데이터 액세스의 이해

커버링 인덱스를 깊이 있게 이해하려면 먼저 B-Tree 인덱스의 물리적 구조를 알아야 합니다.

### 2.1 B-Tree 인덱스의 리프 노드 구성
- **MySQL (InnoDB):** 보조 인덱스(Secondary Index)의 리프 노드에는 인덱스 컬럼의 값과 해당 레코드의 **Primary Key** 값이 들어 있습니다. 만약 PK를 통해 데이터를 찾아야 한다면 클러스터링 인덱스(Clustered Index)로 한 번 더 접근(Key Lookup)해야 합니다.
- **PostgreSQL:** 인덱스의 리프 노드에는 인덱스 컬럼의 값과 해당 튜플의 물리적 위치 정보인 **TID(Tuple ID)** 가 포함됩니다. 필요한 컬럼이 인덱스에 없으면 TID를 이용해 Heap 영역을 읽습니다.

### 2.2 Table Full Scan vs Index Scan vs Covering Index Scan
1. **Table Full Scan:** 인덱스 없이 모든 데이터 페이지를 순차적으로 읽음. (가장 느림)
2. **Index Scan + Table Access:** 인덱스에서 조건을 만족하는 키를 찾은 후, 해당 키가 가리키는 테이블 레코드를 하나씩 방문함. (랜덤 I/O 발생)
3. **Covering Index Scan:** 인덱스 리프 노드만 스캔하고 종료. 테이블 방문 없음. (가장 빠름)

---

## 3. 커버링 인덱스의 작동 원리

### 3.1 랜덤 액세스의 저주와 탈출
디스크는 순차 읽기(Sequential Read)에는 강하지만 랜덤 읽기(Random Read)에는 취약합니다. 인덱스를 타고 테이블을 조회하는 행위는 물리적으로 여기저기 흩어진 블록을 찾아가는 랜덤 액세스입니다. 커버링 인덱스는 인덱스 페이지 자체를 순차적으로 읽는 방식으로 작동하므로 디스크 성능을 극대화할 수 있습니다.

### 3.2 Index-Only Scan (PostgreSQL/Oracle)
PostgreSQL에서는 이를 `Index-Only Scan`이라고 부릅니다. 인덱스만 보고 결과를 내보낼 수 있을 때 실행 계획에 이 방식이 표시됩니다. 다만 PostgreSQL은 MVCC(Multi-Version Concurrency Control)를 관리하기 위해 `Visibility Map`을 확인하여 해당 튜플이 모든 트랜잭션에게 유효한지 체크하며, 유효하지 않다면 드물게 테이블을 방문하기도 합니다.

---

## 4. 실제 성능 비교 및 SQL 예시

예제 테이블 `orders`를 가정해 봅시다.

```sql
CREATE TABLE orders (
    order_id INT PRIMARY KEY,
    customer_id INT,
    order_date DATE,
    status VARCHAR(20),
    total_amount DECIMAL(10, 2),
    INDEX idx_cust_date (customer_id, order_date)
);
```

### 4.1 커버링 인덱스가 적용되지 않는 경우
```sql
-- 쿼리 A
SELECT status
FROM orders
WHERE customer_id = 101 AND order_date >= '2023-01-01';
```
- 인덱스 `idx_cust_date`는 `customer_id`와 `order_date`만 들고 있습니다.
- `status` 값을 가져오기 위해서는 인덱스 정보를 가지고 다시 테이블 본체를 읽어야 합니다.

### 4.2 커버링 인덱스가 적용되는 경우
```sql
-- 쿼리 B
SELECT customer_id, order_date
FROM orders
WHERE customer_id = 101 AND order_date >= '2023-01-01';
```
- `SELECT` 절의 `customer_id`, `order_date`가 모두 인덱스에 포함되어 있습니다.
- DBMS는 인덱스 노드만 읽고 즉시 결과를 반환합니다.

### 4.3 최적화: 인덱스 수정
만약 쿼리 A가 빈번하게 발생한다면 인덱스를 다음과 같이 수정하여 커버링 인덱스로 만들 수 있습니다.
```sql
-- status를 인덱스 끝에 추가
CREATE INDEX idx_cust_date_status ON orders (customer_id, order_date, status);
```

---

## 5. 실행 계획(Execution Plan) 분석

각 DBMS별로 커버링 인덱스가 적용되었는지 확인하는 방법입니다.

### 5.1 MySQL (EXPLAIN)
- `Extra` 컬럼에 **"Using index"**라는 문구가 표시됩니다.
- 주의: "Using index condition"과는 다릅니다. 이는 Index Condition Pushdown(ICP)를 나타내며, 커버링 인덱스는 아닙니다.

### 5.2 PostgreSQL (EXPLAIN ANALYZE)
- `Index Scan` 대신 **"Index Only Scan"**이 표시됩니다.
- `Heap Fetches` 값이 0에 가까울수록 진정한 커버링 인덱스의 효과를 보고 있는 것입니다.

---

## 6. 특정 DBMS별 구현의 차이

### 6.1 PostgreSQL의 INCLUDE 절 (Covering Index)
PostgreSQL 11부터는 `INCLUDE` 절을 지원합니다.
```sql
CREATE INDEX idx_cust_id_include ON orders (customer_id) INCLUDE (order_date, status);
```
- `customer_id`는 B-Tree의 정렬 키(Search Key)로 사용됩니다.
- `order_date`, `status`는 리프 노드에 저장만 되고 정렬에 관여하지 않습니다.
- 장점: 인덱스 깊이(Depth)가 깊어지는 것을 방지하면서 커버링 인덱스 효과를 누릴 수 있습니다.

### 6.2 MySQL의 클러스터링 인덱스 활용
MySQL InnoDB에서는 모든 세컨더리 인덱스가 암묵적으로 PK를 포함하고 있습니다.
따라서 `(A, B)` 인덱스가 있다면 `SELECT PK FROM table WHERE A=? AND B=?` 쿼리는 별도의 조치 없이도 커버링 인덱스가 됩니다.

---

## 7. 정렬(ORDER BY) 및 그룹화(GROUP BY)에서의 활용

커버링 인덱스는 데이터 추출뿐만 아니라 연산 성능 최적화에도 탁월합니다.

### 7.1 인덱스를 이용한 정렬 생략
```sql
SELECT order_id, order_date
FROM orders
WHERE customer_id = 101
ORDER BY order_date;
```
인덱스가 `(customer_id, order_date)` 순서로 되어 있다면, DBMS는 이미 정렬된 인덱스 리스트를 읽기만 하면 되므로 별도의 **Filesort(정렬 작업)** 를 수행하지 않습니다.

### 7.2 정렬과 커버링의 결합
정렬에 사용되는 컬럼과 `SELECT`에서 뽑는 컬럼이 모두 인덱스에 포함되면 최상의 성능을 냅니다. CPU 연산(정렬)과 I/O(테이블 접근)를 동시에 제거하기 때문입니다.

---

## 8. 페이징 쿼리 최적화 (Late Row Lookups)

게시판과 같이 대량의 데이터를 페이징 처리할 때 `OFFSET`이 커질수록 성능이 급격히 떨어집니다.

### 8.1 문제 상황
```sql
SELECT * FROM orders ORDER BY order_id LIMIT 100000, 10;
```
- 앞의 10만 건을 다 읽어서 버려야 하므로 엄청난 Table Access가 발생합니다.

### 8.2 커버링 인덱스를 활용한 지연 조인(Deferred Join)
```sql
SELECT t.*
FROM orders t
JOIN (
    SELECT order_id
    FROM orders
    ORDER BY order_id
    LIMIT 100000, 10
) temp ON t.order_id = temp.order_id;
```
1. 내부 서브쿼리에서는 `order_id`만 사용하므로 커버링 인덱스를 통해 빠르게 10만 건을 스캔하여 대상 PK 10개만 추출합니다.
2. 외부 쿼리에서 추출된 10개의 PK에 대해서만 실제 테이블 접근을 수행합니다.
3. 이를 통해 불필요한 테이블 액세스를 10만 번에서 10번으로 줄일 수 있습니다.

---

## 9. 복합 인덱스 설계 시 컬럼 순서의 미학

커버링 인덱스를 효과적으로 구축하기 위해서는 복합 인덱스의 컬럼 순서 설정이 매우 중요합니다.

### 9.1 카디널리티(Cardinality) 고려
일반적으로 카디널리티가 높은(중복도가 낮은) 컬럼을 앞쪽에 배치하는 것이 인덱스 스캔 범위를 줄이는 데 유리합니다. 하지만 이는 `WHERE` 절의 필터 조건에 따라 달라질 수 있습니다.

### 9.2 등치(=) 조건과 범위(<, >, BETWEEN) 조건
- `=` 조건으로 사용되는 컬럼을 인덱스 앞쪽에 배치합니다.
- 범위 조건으로 사용되는 컬럼은 인덱스 뒤쪽에 배치합니다.
- **이유:** 범위 조건 뒤에 있는 컬럼은 인덱스를 통한 정렬 및 커버링 효과를 보기가 어렵기 때문입니다.

### 9.3 쿼리 공통 분모 찾기
여러 쿼리에서 공통적으로 사용되는 컬럼을 인덱스의 선두 컬럼으로 설정하면, 하나의 인덱스로 여러 쿼리를 커버할 수 있어 관리 비용이 줄어듭니다.

---

## 10. 인덱스 스킵 스캔(Index Skip Scan)과 커버링 인덱스

최신 DBMS(MySQL 8.0+, Oracle 등)는 선두 컬럼이 `WHERE` 절에 없더라도 인덱스를 활용할 수 있는 **Index Skip Scan** 을 지원합니다.

### 10.1 작동 방식
인덱스가 `(gender, age)`로 구성되어 있을 때, `SELECT age FROM users WHERE age = 25` 쿼리를 실행하면 원래는 인덱스를 타지 못합니다. 하지만 Skip Scan은 `gender`의 유니크한 값(M, F)을 확인한 후, 각 그룹 내에서 `age = 25`인 데이터를 찾습니다.

### 10.2 커버링 인덱스와의 시너지
선두 컬럼의 유니크 값 개수가 적다면, Skip Scan을 통해 테이블 접근 없이 인덱스만으로 결과를 반환할 수 있습니다. 이는 "인덱스를 잘못 만들었다"고 생각했던 상황에서도 DBMS의 지능적인 처리로 성능 이득을 볼 수 있게 해줍니다.

---

## 11. 애플리케이션 레벨의 최적화 전략

데이터베이스 설계뿐만 아니라 애플리케이션(Java/Spring 등) 개발 시에도 커버링 인덱스를 염두에 두어야 합니다.

### 11.1 과도한 DTO 매핑 주의
`SELECT *`를 지양하고 필요한 컬럼만 명시적으로 조회하는 습관을 들여야 합니다. JPA(Entity)를 사용할 때도 가급적이면 필요한 필드만 조회하는 `Projections` 기능을 활용하여 커버링 인덱스가 동작할 물리적 기반을 마련해야 합니다.

### 11.2 비즈니스 로직의 분리
때로는 대량의 데이터를 한꺼번에 조회하는 대신, 커버링 인덱스로 ID 리스트만 먼저 뽑아온 뒤 비즈니스 로직에 따라 필요한 시점에 상세 정보를 조회(Lazy Loading 또는 별도 쿼리)하는 것이 전체 리소스 소모 면에서 유리할 수 있습니다.

---

## 12. 안티 패턴: 커버링 인덱스를 남용할 때 발생하는 문제

### 12.1 인덱스 비대화 (Index Bloat)
인덱스는 메모리(Buffer Pool)에 상주할 때 가장 빠릅니다. 모든 요구사항을 들어주기 위해 컬럼을 계속 추가하다 보면 인덱스 크기가 테이블 크기와 비슷해지기도 합니다. 이는 메모리 부족 현상을 야기하고 전체 시스템의 캐싱 효율을 떨어뜨립니다.

### 12.2 업데이트 지옥
커버링 인덱스에 포함된 컬럼이 번번하게 업데이트된다면, 데이터가 변경될 때마다 인덱스 페이지도 함께 수정되어야 합니다. 이는 쓰기 락(Write Lock) 경합을 유발하고 트랜잭션 처리 시간을 늘립니다.

### 12.3 데이터 중복
인덱스는 결국 데이터의 복사본입니다. 너무 많은 커버링 인덱스는 저장 공간 소모를 가속화하고 백업/복구 시간을 늘리는 주범이 됩니다.

---

## 13. 모니터링 및 튜닝 실무

### 13.1 Slow Query Log 분석
슬로우 쿼리 로그에서 `rows_sent`와 `rows_examined`의 비율을 확인하십시오. `rows_examined`가 훨씬 크다면 인덱스가 제대로 동작하지 않거나 테이블 랜덤 액세스가 과도한 것입니다. 이때 커버링 인덱스 도입을 검토해야 합니다.

### 13.2 Handler_read_* 상태 변수 (MySQL)
- `Handler_read_key`: 인덱스를 통해 읽은 횟수
- `Handler_read_next`: 인덱스 순서대로 읽은 횟수
이 지표들이 높고 CPU 사용량이 안정적이라면 인덱스가 잘 설계된 것입니다.

---

## 14. 함수 사용 시 인덱스 무력화 해결 (PostgreSQL)

일반적인 B-Tree 인덱스는 컬럼의 원본 값을 기준으로 정렬되어 있습니다. 따라서 `WHERE` 절에서 컬럼을 함수로 감싸 가공하면, DBMS는 인덱스에 저장된 값과 비교할 수 없어 **Sequential Scan** 을 수행하게 됩니다. 이 문제를 해결하기 위해 PostgreSQL에서는 **함수 기반 인덱스(Expression Index)** 를 지원합니다.

### 14.1 사례: 대소문자 구분 없는 검색
가장 흔한 사례는 대문자나 소문자로 변환하여 데이터를 검색하는 경우입니다.

```sql
-- 인덱스가 타지 않는 쿼리
SELECT * FROM users WHERE LOWER(email) = 'test@example.com';
```
`email` 컬럼에 인덱스가 있더라도, `LOWER(email)`의 결과값은 인덱스에 저장된 원본 `email` 값과 다르기 때문에 인덱스를 사용할 수 없습니다.

### 14.2 해결: 함수 기반 인덱스 생성
PostgreSQL에서는 인덱스 생성 시 표현식(Expression)을 직접 사용할 수 있습니다.

```sql
-- 함수 기반 인덱스 생성
CREATE INDEX idx_users_email_lower ON users (LOWER(email));
```
이제 DBMS는 인덱스 페이지에 `LOWER(email)` 연산의 결과값을 미리 정렬하여 저장합니다. 따라서 위에서 실패했던 쿼리도 **Index Scan** 이 가능해집니다.

### 14.3 주의사항: 함수 기반 인덱스의 제약
1. **정합성 보장**: 함수 기반 인덱스에 사용되는 함수는 반드시 **IMMUTABLE** (입력값이 같으면 항시 결과값이 같은) 함수여야 합니다. (예: `LOWER()`, `UPPER()`, `COALESCE()` 등)
    - `NOW()`나 `RANDOM()` 같은 함수는 인덱스에 사용할 수 없습니다.
2. **쿼리 일치성**: 쿼리의 `WHERE` 절에 사용된 표현식이 인덱스 정의와 **한 글자도 틀리지 않고 정확히 일치** 해야 합니다.
    - 인덱스는 `LOWER(email)`인데 쿼리는 `UPPER(email)`이면 인덱스를 타지 않습니다.
3. **유지 비용**: 일반 인덱스와 마찬가지로 데이터가 `INSERT`/`UPDATE`될 때마다 함수 연산을 수행하고 그 결과를 인덱스에 반영해야 하므로, 쓰기 작업 시 약간의 오버헤드가 발생합니다.

---

## 15. 실전 트러블슈팅 사례 요약: "왜 Index Only Scan이 안 될까?"

위의 함수 사용 외에도 `Index Only Scan`이 실패하는 주요 원인은 다음과 같습니다.

1. **Visibility Map 미갱신:** VACUUM이 오랫동안 실행되지 않아 DBMS가 해당 페이지의 데이터가 모든 트랜잭션에게 유효한지 확신하지 못할 때 발생합니다. `ANALYZE` 또는 `VACUUM`을 실행하면 해결됩니다.
2. **데이터 타입 불일치:** `VARCHAR` 컬럼을 정수형 값(`WHERE col = 123`)으로 조회하면 묵시적 형변환이 발생하여 인덱스 사용이 제한됩니다. 타입을 명시적으로 맞춰주거나 캐스팅(`::text`)을 활용해야 합니다.
3. **불필요한 컬럼 포함:** `SELECT *`를 사용하면 인덱스에 포함되지 않은 컬럼이 하나라도 있는 한 무조건 테이블 방문(Heap Fetch)이 발생합니다.

## 15. 요약

커버링 인덱스는 단순한 튜닝 기법을 넘어 **"데이터 로드 효율성"** 을 극대화하는 설계 철학입니다.

### 핵심 요약:
1. **정의:** 쿼리의 모든 컬럼이 인덱스에 포함되어 테이블 접근을 생략하는 상태.
2. **효과:** 랜덤 I/O 제거, CPU 정렬 부하 감소, 페이징 성능 획기적 개선.
3. **설계 전략:** `=` 조건 컬럼을 전면에, 범위 조건 및 정렬 컬럼을 후면에 배치.
4. **주의:** 쓰기 성능과 인덱스 크기 사이의 트레이드오프(Trade-off)를 항상 고려.

데이터베이스 성능 문제는 대부분 저장 장치와의 대화(I/O)에서 발생합니다. 커버링 인덱스를 통해 이 대화 시간을 최소화하는 것이 가장 스마트한 최적화의 첫걸음입니다.