---
id: Sort Merge Join
started: 2025-05-23
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# Sort Merge Join (정렬 병합 조인)

## 1. 개요 (Overview)
**Sort Merge Join**은 조인 대상인 두 테이블을 각각 조인 키(Join Key) 기준으로 **정렬(Sort)** 한 후, 정렬된 결과를 차례대로 읽으며 **병합(Merge)** 하여 조인을 수행하는 방식입니다.

Hash Join이 등장하기 전까지는 대용량 조인의 유일한 대안이었으며, 지금도 **Range Condition (<, >, BETWEEN)** 조인이나 **이미 정렬된 데이터**를 조인할 때는 Hash Join보다 강력한 성능을 발휘합니다.
Nested Loop Join과 달리 랜덤 액세스(Random Access)가 없으며, Hash Join과 달리 해시 테이블 생성을 위한 메모리 오버헤드가 없습니다(대신 정렬 메모리가 필요합니다).

---

## 2. 동작 메커니즘 (Internal Mechanism)

Sort Merge Join은 이름 그대로 **Sort Phase(정렬 단계)** 와 **Merge Phase(병합 단계)** 로 나뉩니다.

### 2.1 Sort Phase (정렬 단계)
1. **양쪽 테이블 정렬**: 조인 키 컬럼을 기준으로 선행 테이블(Outer)과 후행 테이블(Inner)을 각각 독립적으로 정렬합니다.
    - 정렬 작업은 메모리(Sort Area/PGA)에서 수행됩니다.
    - 메모리가 부족하면 임시 영역(Temp Tablespace)으로 데이터가 내려가며(Swap/Spill), 이때 I/O 부하가 발생합니다.
    - **Optimization**: 만약 조인 컬럼에 인덱스가 있거나, 이미 정렬된 상태(Clustered Index 등)라면 이 단계는 생략됩니다(Skipped). 이는 Sort Merge Join의 최대 강점입니다.

### 2.2 Merge Phase (병합 단계)
1. 정렬된 두 테이블의 포인터(Cursor)를 시작 지점에 둡니다.
2. 두 포인터가 가리키는 값을 비교합니다.
3. **값이 같으면(Match)**: 조인 결과에 포함시키고, Inner 테이블의 포인터를 다음으로 이동합니다. (Outer 값과 같은 Inner 값이 더 있을 수 있으므로)
4. **값이 다르면(Mismatch)**: 더 작은 값을 가진 쪽의 포인터를 다음으로 이동합니다(스캔 진행).
5. 어느 한 쪽의 포인터가 끝에 도달할 때까지 반복합니다.
> 이 과정은 한 번의 스캔(Single Pass)으로 완료되므로 매우 빠릅니다.

---

## 3. Sort Merge Join을 사용해야 하는 경우 (Use Cases)

Hash Join이 대부분의 대용량 동등 조인을 대체했지만, Sort Merge Join은 여전히 대체 불가능한 영역을 가지고 있습니다.

### 3.1 Range Join (범위 조인)
Hash Join은 해시 함수의 특성상 동등(`=`) 비교만 가능합니다.
하지만 `BETWEEN`, LIKE, `<`, `>` 등의 부등호 조건으로 대용량 데이터를 조인해야 한다면 Sort Merge Join이 유일한 해법입니다.
```sql
SELECT /*+ USE_MERGE(A B) */ *
FROM EMP A, SALGRADE B
WHERE A.SAL BETWEEN B.LOSAL AND B.HISAL;
```

### 3.2 이미 정렬된 데이터 (Pre-sorted Data)
조인 키 컬럼에 인덱스가 있거나, `ORDER BY` 절 등에 의해 이미 정렬된 데이터 집합을 조인할 때 유리합니다.
정렬 비용(Sort Cost)이 '0'이 되므로, 해시 테이블을 만드는 비용이 드는 Hash Join보다 빠를 수 있습니다.

### 3.3 Cartesian Product (교차 조인)
두 테이블 간의 연결 조건이 아예 없을 때(Cross Join), 옵티마이저는 주로 Sort Merge Join 방식을 사용합니다.

---

## 4. 메모리 관리와 성능 (Memory & Performance)

### 4.1 Sort Area Size
- 정렬 작업은 CPU와 메모리를 많이 사용합니다.
- Oracle의 `PGA_AGGREGATE_TARGET`, PostgreSQL의 `work_mem`이 충분해야 In-Memory Sort가 가능합니다.
- 정렬 데이터가 커서 디스크(Temp)로 넘어가면, 'One-pass' 혹은 'Multi-pass' Sort가 발생하여 I/O 성능이 급격히 떨어집니다.

### 4.2 Hash Join 대안으로서의 가치
- Hash Join은 Build Input이 메모리보다 크면 성능이 저하되지만, Spill이 발생해도 Partitioning을 통해 비교적 선형적인 성능 저하를 보입니다.
- 반면 Sort Merge Join은 정렬 비용이 $O(N \log N)$이므로 데이터 양이 늘어날수록 비용이 급격히 증가합니다.
- 따라서 **동등 조인(=) 상황에서는 Hash Join을 우선**하고, 특수 상황(범위 조인 등)에서만 Sort Merge Join을 고려하는 것이 일반적입니다.

---

## 5. 실행 계획 분석 (Execution Plan)

### 5.1 Oracle Example
```text
----------------------------------------------------------------------------
| Id  | Operation           | Name | Rows  | Bytes | Cost (%CPU)| Time     |
----------------------------------------------------------------------------
|   0 | SELECT STATEMENT    |      |    14 |   500 |     5  (20)| 00:00:01 |
|   1 |  MERGE JOIN         |      |    14 |   500 |     5  (20)| 00:00:01 | -- (3) Merge
|   2 |   SORT JOIN         |      |     4 |    80 |     2  (50)| 00:00:01 | -- (1) Sort A
|   3 |    TABLE ACCESS FULL| DEPT |     4 |    80 |     1   (0)| 00:00:01 | 
|*  4 |   SORT JOIN         |      |    14 |   400 |     2  (50)| 00:00:01 | -- (2) Sort B
|   5 |    TABLE ACCESS FULL| EMP  |    14 |   400 |     1   (0)| 00:00:01 |
----------------------------------------------------------------------------
```
- **Id 2, 4**: `SORT JOIN` 오퍼레이션이 양쪽 테이블에 대해 발생합니다. (정렬 수행)
- **Id 1**: `MERGE JOIN` 오퍼레이션으로 병합합니다.
- 만약 인덱스를 이용하여 정렬을 생략했다면 `SORT JOIN` 단계가 사라집니다.

### 5.2 PostgreSQL Example
```text
Merge Join  (cost=100.00..200.00 rows=100 width=100)
  Merge Cond: (t1.id = t2.id)
  ->  Sort  (cost=50.00..52.00 rows=100 width=50)       -- Sort A
        Sort Key: t1.id
        ->  Seq Scan on t1  (cost=0.00..20.00 ...)
  ->  Sort  (cost=50.00..52.00 rows=100 width=50)       -- Sort B
        Sort Key: t2.id
        ->  Seq Scan on t2  (cost=0.00..20.00 ...)
```
- PostgreSQL에서도 명시적으로 `Sort` 노드가 나타납니다.

---

## 6. 비교: Hash vs Sort Merge vs Nested Loop

| 특징 | Hash Join | Sort Merge Join | Nested Loop Join |
| :--- | :--- | :--- | :--- |
| **조인 조건** | **Equal(=) Only** | **Equal(=), Range(>, <, Between)** | 모든 조건 가능 |
| **핵심 부하** | 해시 테이블 생성 (CPU/Mem) | 데이터 정렬 (CPU/Mem/Temp) | 랜덤 액세스 (I/O) |
| **사전 정렬** | 무관함 | **정렬되어 있으면 매우 빠름** | 무관함 (인덱스 정렬 활용 가능) |
| **대용량 성능**| **일반적으로 최상** | Hash 다음으로 우수 (비등 조인 시 유일) | 대용량 시 최악 |
| **부분 범위** | 불가능 | 불가능 (정렬 완료 후 진행) | 가능 |

---

## 7. 성능 튜닝 및 힌트 (Tuning & Hints)

### 7.1 인덱스를 활용한 Sort 생략
Sort Merge Join 튜닝의 핵심은 **Sort 연산을 없애는 것**입니다.
```sql
-- emp.deptno에 인덱스가 있다면 정렬 없이 바로 읽음
SELECT /*+ USE_MERGE(d e) */ *
FROM dept d, emp e
WHERE d.deptno = e.deptno
AND d.deptno > 10;
```
위 쿼리에서 `deptno`로 정렬된 인덱스를 타게 되면 `SORT JOIN` 단계 없이 바로 `MERGE JOIN`으로 진입하여 성능이 비약적으로 향상됩니다.

### 7.2 힌트 사용법
- **Oracle**:
    - `/*+ USE_MERGE(table_alias) */`: 해당 테이블을 포함한 조인을 SMJ로 수행.
    - `/*+ NO_USE_TASH(table_alias) */`: Hash Join을 막아서 간접 유도.
- **MySQL**:
    - MySQL은 전통적으로 Nested Loop 방식에 집중했으나, 최근 버전에서는 Hash Join을 선호합니다. Sort Merge Join을 강제하는 힌트는 제한적일 수 있습니다. (Optimizer Switch 조절 필요)

---

## 8. 결론 (Conclusion)
- **Hash Join**이 대세인 현대 아키텍처에서도 **Sort Merge Join**은 **Range Join**과 **Order By 최적화** 상황에서 여전히 빛을 발합니다.
- 특히 인덱스 설계를 잘하여 Sort 단계를 생략할 수 있다면, 대용량 데이터를 아주 적은 시스템 리소스로 처리할 수 있는 효율적인 방식입니다.
- 개발자는 무조건 Hash Join만 고집하지 말고, 데이터의 정렬 상태와 조인 조건을 면밀히 파악하여 Sort Merge Join의 가능성을 열어두어야 합니다.

# Reference
- [Oracle 19c Tuning Guide: Joins](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/joins.html)
- [PostgreSQL Documentation: Merge Join](https://wiki.postgresql.org/wiki/Merge_Join)