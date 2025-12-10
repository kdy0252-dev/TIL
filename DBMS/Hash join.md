---
id: Hash Join
started: 2025-05-11
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# Hash Join (해시 조인)

## 1. 개요 (Overview)
**Hash Join**은 관계형 데이터베이스(RDBMS)에서 두 개의 테이블을 결합(Join)하는 가장 효율적인 알고리즘 중 하나입니다.
주로 **대용량 데이터 집합**을 조인하거나, 적절한 인덱스가 없어 **Nested Loop Join**을 사용할 수 없을 때, 그리고 정렬(Sort)에 대한 오버헤드가 큰 **Sort Merge Join**을 대체하기 위해 사용됩니다.

해시 조인은 **해시 함수(Hash Function)** 를 사용하여 조인 키를 해시 값으로 변환하고, 이를 기반으로 **해시 테이블(Hash Table)** 을 생성하여 매칭시키는 방식을 취합니다. $O(N+M)$의 선형 시간 복잡도를 가지므로 대용량 처리 시 매우 강력한 성능을 발휘합니다.

### 1.1 역사와 도입
- 과거 Oracle 등의 DB는 Nested Loop Join과 Sort Merge Join만 지원했으나, Sort Merge Join의 과도한 정렬 부하(CPU, Memory)를 해결하기 위해 Hash Join이 도입되었습니다 (Oracle 7.3+).
- MySQL은 오랜 기간 Nested Loop Join(Block Nested Loop)만 지원하다가 버전 8.0.18부터 Hash Join을 공식 지원하기 시작했습니다.

---

## 2. 동작 메커니즘 (Internal Mechanism)

Hash Join은 크게 두 단계, **Build Phase(빌드 단계)** 와 **Probe Phase(탐색 단계)** 로 나뉩니다.

### 2.1 Build Phase (해시 테이블 생성)
1. 옵티마이저는 조인 대상인 두 테이블 중 **더 작은 테이블(Small Row source)** 을 **Build Input**으로 선택합니다.
    - *Tip*: 통계 정보가 정확해야 효율적인 Build Input을 선택할 수 있습니다.
2. Build Input을 스캔하면서 조인 키(Join Key)에 해시 함수를 적용합니다.
3. 생성된 해시 값과 실제 레코드의 데이터를 **메모리 내의 해시 영역(Hash Area)** 에 저장합니다.
    - 해시 테이블은 `Bucket` - `Chain` (Linked List) 구조로 구성되어 해시 충돌(Collision)을 처리합니다.
    - 메모리 공간(PGA, Work Mem)이 충분하다면 전체 Build Input이 메모리에 올라갑니다 (**In-Memory Hash Join**).

### 2.2 Probe Phase (매칭 및 결과 반환)
1. **큰 테이블(Large Row source)** 을 **Probe Input**으로 선택하여 흝기 시작합니다(Scan).
2. 각 Row의 조인 키에 동일한 해시 함수를 적용하여 해시 값을 얻습니다.
3. 이 해시 값을 이용해 메모리에 있는 해시 테이블의 해당 버킷을 찾습니다.
4. 버킷 내의 체인을 따라가며 실제 조인 키 값이 일치하는지 확인합니다.
5. 매칭에 성공하면 조인 성공으로 간주하고 결과 집합(Result Set)에 추가합니다.

---

## 3. 메모리 관리와 조인 방식 (Memory Management)

Hash Join의 성능은 **Build Input이 메모리에 온전히 들어가는가**에 따라 결정적으로 달라집니다.

### 3.1 In-Memory Hash Join (Optimal)
- **상황**: Build Input의 크기가 할당된 해시 메모리(Hash Area Size)보다 작은 경우.
- **동작**: 전체 Build Input이 메모리에 상주하므로 디스크 I/O 없이 CPU 연산만으로 매우 빠르게 수행됩니다.
- **Goal**: 튜닝의 목표는 항상 Optimal Hash Join을 만드는 것입니다.

### 3.2 Grace Hash Join (On-Disk / Spill to Disk)
- **상황**: Build Input이 너무 커서 메모리에 다 들어가지 못하는 경우.
- **동작 원리 (Divide and Conquer)**:
    1. **Partitioning**: 조인 키의 해시 값을 기준으로 Build Input과 Probe Input을 여러 개의 작은 **파티션(Partition)** 으로 나누어 디스크(Temp Tablespace)에 기록합니다. (Partition Pair 생성)
    2. 파티션 단위 조인: 각 파티션 쌍(Build Partition 1 - Probe Partition 1)을 하나씩 메모리로 로드하여 In-Memory Hash Join을 수행합니다.
- **성능 영향**: 디스크 I/O(Direct Path Write/Read)가 발생하여 성능이 급격히 저하됩니다. 하지만 Sort Merge Join 처럼 전체를 한 번에 정렬하는 것보다는 효율적입니다.

### 3.3 Hybrid Hash Join
- Grace Hash Join의 변형으로, 첫 번째 파티션은 메모리에 남겨두고 나머지 파티션만 디스크에 쓰는 방식입니다. 조금이라도 I/O를 줄이기 위해 고안되었습니다.

### 3.4 Recursive Hash Join (Nested Hash Join)
- 만약 분할된(Partitioned) Build Partition 조차도 메모리보다 크다면?
- 해당 파티션을 다시 더 작은 서브 파티션으로 나누는 과정을 재귀적으로 수행합니다. 성능에 치명적입니다.

---

## 4. 장단점 비교 (Pros & Cons)

| 구분 | Hash Join | Sort Merge Join | Nested Loop Join |
| :--- | :--- | :--- | :--- |
| **선행 조건** | Equal Join (`=`) 필수 | Range Join (`<`, `>`) 가능 | 모든 조인 조건 가능 |
| **인덱스 유무** | 인덱스 불필요 (Full Scan 유리) | 인덱스 불필요 | **인덱스 필수** (Random Access) |
| **메모리 사용** | 해시 테이블 생성 비용 (높음) | 정렬 비용 (매우 높음) | 버퍼 캐시 사용 (낮음) |
| **대용량 처리** | **최우수** | 우수 (이미 정렬된 경우 최상) | 비효율적 (Random Access 부하) |
| **부분 범위 처리**| 불가능 (Build 완료 후 스캔) | 불가능 (정렬 완료 후 스캔) | **가능** (첫 행 즉시 반환) |

---

## 5. 실행 계획 분석 (Execution Plan Analysis)

### 5.1 Oracle Execution Plan
```text
-----------------------------------------------------------------------------------
| Id  | Operation          | Name    | Rows  | Bytes | Cost (%CPU)| Time     |
-----------------------------------------------------------------------------------
|   0 | SELECT STATEMENT   |         |  500K |    30M|  1500   (1)| 00:00:18 |
|*  1 |  HASH JOIN         |         |  500K |    30M|  1500   (1)| 00:00:18 | -- (2)
|   2 |   TABLE ACCESS FULL| DEPT    |   100 |  2000 |     5   (0)| 00:00:01 | -- (1) Build Input
|   3 |   TABLE ACCESS FULL| EMP     |    1M |    50M|  1450   (1)| 00:00:17 | -- (3) Probe Input
-----------------------------------------------------------------------------------
```
- **해석 순서**: 2 -> 1 -> 3 (실제로는 Build(2) -> Probe(3) 매칭)
- `DEPT` 테이블(작은 테이블)이 상위에 있으므로 Build Input으로 선정됨.
- `TABLE ACCESS FULL`: Hash Join은 주로 인덱스 스캔보다는 풀 테이블 스캔과 결합될 때 효율적입니다.
- **Wait Events**:
    - `direct path read temp` / `direct path write temp`: Grace Hash Join 발생 시 나타남. 메모리 부족 신호.

### 5.2 PostgreSQL Explain Analyze
```text
Hash Join  (cost=100.00..5000.00 rows=1000 width=100)
  Hash Cond: (emp.deptno = dept.deptno)
  ->  Seq Scan on emp  (cost=0.00..2000.00 rows=100000 width=50) -- Probe Input
  ->  Hash  (cost=50.00..50.00 rows=100 width=50)              -- Hash Table 생성
        ->  Seq Scan on dept  (cost=0.00..50.00 rows=100 width=50) -- Build Input
```
- 문맥상 아래쪽(`Hashtable -> dept`)이 먼저 실행되어 메모리에 로드됩니다.

---

## 6. 성능 튜닝 가이드 (Performance Tuning Guide)

Hash Join 성능 최적화를 위해 고려해야 할 핵심 요소들입니다.

### 6.1 Build Input 크기 최소화 (Swap Join Inputs)
- **원칙**: 무조건 **작은 집합**이 Build Input이 되어야 합니다.
- **이유**: Build Input이 작을수록 해시 테이블 생성 시간이 단축되고, 메모리 사용량이 줄어들어 In-Memory Join 확률이 높아집니다.
- **튜닝 방법**:
    - **통계 갱신**: `ANALYZE TABLE` (Oracle/Postgres) 등으로 최신 통계 유지.
    - **힌트 사용**:
        - Oracle: `/*+ LEADING(small_table) USE_HASH(large_table) */` 또는 `/*+ SWAP_JOIN_INPUTS(table_name) */`
        - MySQL: `JOIN_ORDER` 힌트 등 활용.

### 6.2 메모리 영역 튜닝 (Memory Sizing)
Build Input이 메모리보다 크면 디스크 스필(Disk Spill)이 발생하여 치명적입니다.
- **Oracle**:
    - `PGA_AGGREGATE_TARGET`: 전체 PGA 메모리 한도. 자동으로 `*_AREA_SIZE`를 조절하지만, 개별 세션의 최대 사용량 제한이 있습니다.
    - `_SMM_MAX_SIZE`: 히든 파라미터로 개별 세션 최대 작업 공간을 제어합니다. (전문가용)
- **PostgreSQL**:
    - `work_mem`: **매우 중요**. 쿼리의 각 노드(Sort, Hash)마다 할당되는 메모리 크기. 기본값(4MB 등)이 작으면 대용량 해시 조인 시 무조건 디스크로 갑니다. 세션 레벨에서 `SET work_mem = '64MB';` 등으로 늘려줄 필요가 있습니다.
- **MySQL**:
    - `join_buffer_size`: 조인 버퍼의 크기. Block Nested Loop나 Hash Join(8.0+)에 사용됩니다.

### 6.3 해시 충돌 및 키 분포 (Data Skew)
- **문제**: 특정 조인 키(예: 'NULL'이나 특정 코드)에 데이터가 몰려 있으면(Skew), 특정 해시 버킷만 비대해져서 체인 탐색 속도가 느려집니다.
- **해결**:
    - 편중된 값은 조인 전에 필터링(`WHERE key IS NOT NULL`)하거나, Histogram 통계를 생성하여 옵티마이저가 인지하게 합니다.
    - 파티셔닝(Partitioning)을 통해 병렬 해시 조인(Parallel Hash Join)을 유도합니다.

### 6.4 Parallel Hash Join (병렬 처리)
대용량 테이블 조인 시 CPU 코어를 여러 개 사용하여 해시 테이블 생성과 탐색을 병렬로 수행합니다.
- **Oracle**: `/*+ PARALLEL(table_name 4) */`
- **Bloom Filter**: 병렬 조인이나 Exadata 등에서 Probe 단계 전 Build 단계에서 생성된 **Bloom Filter** 비트맵을 Probe 테이블 스캔 시점에 미리 적용하여, 조인되지 않을 행을 조기에 걸러내는 최적화가 동작하기도 합니다.

---

## 7. 주요 힌트 및 SQL 예제 (Hints & Examples)

### 7.1 Oracle Hints
```sql
-- 1. 강제로 Hash Join 유도
SELECT /*+ USE_HASH(e d) */ * 
FROM emp e, dept d 
WHERE e.deptno = d.deptno;

-- 2. Build Input 지정 (LEADING 힌트와 조합)
-- d(dept)를 먼저 읽어서(LEADING) Hash Build 하라
SELECT /*+ LEADING(d) USE_HASH(e) */ * 
FROM emp e, dept d 
WHERE e.deptno = d.deptno;

-- 3. 디스크 스왑 강제 제어 (특수)
-- 옵티마이저가 잘못된 테이블을 Build Input으로 잡았을 때 강제로 뒤집기
SELECT /*+ SWAP_JOIN_INPUTS(d) USE_HASH(e) */ * 
FROM emp e, dept d 
WHERE e.deptno = d.deptno;
```

### 7.2 MySQL (8.0.18+)
```sql
-- Hash Join은 힌트 없이도 동등 조인(=)에서 기본적으로 선택됩니다.
-- 강제로 BNL(Block Nested Loop) 등을 끄고 Hash Join을 유도하려면 최적화 스위치 제어 필요할 수 있음.
EXPLAIN FORMAT=TREE 
SELECT * 
FROM t1 
JOIN t2 ON t1.c1 = t2.c1;

-- Output 예시:
-- -> Inner hash join (t2.c1 = t1.c1)  (cost=...)
--     -> Table scan on t2  (cost=...)
--     -> Hash
--         -> Table scan on t1 (cost=...)
```

### 7.3 Tuning Case Study: "Temp Space 부족 오류 해결"
**증상**: 수억 건 조인 시 `ORA-01652: unable to extend temp segment` 오류 발생.
**분석**:
1. Build Input으로 선택된 테이블이 예상보다 큼 (통계 오류).
2. `PGA` 메모리가 부족하여 Temp DB로 데이터가 쏟아짐(Spill).
3. Temp Tablespace가 꽉 차서 쿼리 실패.
**조치**:
1. `WHERE` 절 조건 추가로 데이터 범위 축소.
2. `Check constraints` 등으로 `NULL` 데이터 제외.
3. 힌트를 사용하여 더 작은 테이블을 확실하게 Build Input으로 고정.
4. 필요 시 파티션 조인(Partition-wise Join)으로 유도하여 조인 단위를 쪼갬.

---

## 8. 결론 및 요약 (Conclusion)
- Hash Join은 **Equal Join** 환경에서 **대용량 데이터**를 처리할 때 가장 강력한 무기입니다.
- **Hash Area Size(메모리)** 확보와 **Build Input(작은 테이블) 선정**이 성능의 핵심입니다.
- 인덱스 유무와 상관없이 동작하므로, 인덱스 효율이 안 좋은 배치성 쿼리에서 적극 활용해야 합니다.
- 다만, OLTP 환경에서 소량의 데이터를 빈번하게 조회할 때는 오버헤드가 크므로 **Nested Loop Join**이 더 유리할 수 있음을 명심해야 합니다.

# Reference
- [Oracle Database Performance Tuning Guide](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/index.html)
- [PostgreSQL Documentation: Join Planner](https://www.postgresql.org/docs/current/planner-optimizer.html)
- [MySQL 8.0 Hash Join](https://dev.mysql.com/blog-archive/hash-join-in-mysql-8/)
- "Troubleshooting Oracle Performance" by Christian Antognini