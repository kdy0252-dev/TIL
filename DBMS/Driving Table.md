---
id: Driving Table
started: 2025-05-23
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# Driving Table (드라이빙 테이블)

## 1. 개요 (Overview)
**Driving Table**(선행 테이블, Outer Table)은 데이터베이스 Join 연산(특히 Nested Loop Join) 시 **가장 먼저 액세스되는 테이블**을 의미합니다.
Join 연산은 두 개 이상의 테이블을 연결하는 과정인데, 어떤 테이블을 먼저 읽느냐에 따라 전체 쿼리의 성능이 수십 배에서 수만 배까지 차이가 날 수 있습니다.

조인 성능 최적화(SQL Tuning)의 첫 번째 단계는 바로 **"Driving Table을 올바르게 선정하는 것"** 입니다.
Driving Table에서 추출된 데이터 건수만큼 Driven Table(후행 테이블, Inner Table)을 반복해서 탐색(Probe)해야 하기 때문입니다.

### 1.1 용어 정리
- **Driving Table (Outer Table)**: 조인의 주체가 되는 테이블. 먼저 액세스하여 결과를 추출함.
- **Driven Table (Inner Table)**: Driving Table의 결과값으로 검색되는 테이블. 나중에 액세스됨.

---

## 2. 동작 원리 및 중요성 (Mechanism)

### 2.1 Nested Loop Join에서의 역할
```java
// Driving Table(Outer) 루프
for (Row outer : DrivingTable) { 
    // Driven Table(Inner) 루프 (인덱스 탐색)
    for (Row inner : DrivenTable) { 
        if (outer.key == inner.key) { ... }
    }
}
```
위 슈도 코드에서 보듯이, **Outer 루프의 반복 횟수**가 전체 성능을 좌우합니다.
- Case A: Driving Table이 10건, Driven Table이 100만 건 (인덱스 있음)
    - 10번 Loop * 1번 인덱스 탐색 = 총 10번 탐색 (매우 빠름)
- Case B: Driving Table이 100만 건, Driven Table이 10건
    - 100만 번 Loop * 1번 인덱스 탐색 = 총 100만 번 탐색 (매우 느림)

따라서 **"조건절(WHERE)에 의해 필터링된 결과 건수가 가장 적은 테이블"** 이 Driving Table이 되어야 합니다.

### 2.2 Hash Join에서의 역할 (Build Input)
Hash Join에서는 Driving Table이라는 용어 대신 **Build Input**이라는 용어를 주로 사용합니다.
- 작은 테이블(Build Input)로 해시 테이블을 생성(Build)합니다.
- 큰 테이블(Probe Input)로 해시 테이블을 탐색(Probe)합니다.
- Build Input이 메모리(Hash Area)에 다 들어갈 수 있느냐 없느냐가 성능의 핵심이므로, 결과적으로 **작은 집합**이 선행되어야 한다는 원칙은 동일합니다.

---

## 3. Driving Table 선정 기준 (Selection Strategy)

옵티마이저(Optimizer)는 통계 정보(Statistics)를 바탕으로 비용(Cost)을 계산하여 자동으로 할당하지만, 힌트를 통해 강제할 수 있습니다.

### 3.1 최적의 선정 조건
1. **WHERE 절의 필터 조건이 강력한 테이블**: 조건에 의해 많은 데이터가 걸러져서 남은 행의 수가 적은 테이블.
2. **전체 행의 수(Table Rows)가 적은 테이블**: 코드성 테이블 등.
3. **Driven Table의 조인 키에 인덱스가 있는 경우**: Driven Table에 인덱스가 없다면 Driving Table을 아무리 잘 골라도 Full Table Scan을 해야 하므로 의미가 없습니다. (이 경우 Hash Join이나 BNL 고려)

### 3.2 힌트를 이용한 제어 (Oracle)
- **`/*+ ORDERED */`**: `FROM` 절에 기술된 순서대로 조인을 수행하라. (첫 번째가 Driving)
- **`/*+ LEADING(table_alias) */`**: 특정 테이블을 가장 먼저 드라이빙하라고 지정. (가장 많이 사용됨)
- **`/*+ USE_NL(A B) */`**: NL Join을 유도하면서 보통 LEADING과 함께 사용.

---

## 4. 잘못된 선정 사례 및 튜닝 (Troubleshooting)

### 사례 1: 대용량 테이블이 Driving된 경우
- **상황**: 주문(Order) 테이블(1000만 건)과 회원(User) 테이블(10만 건) 조인.
- **잘못된 Plan**: 주문 테이블 전체를 스캔(Driving)하면서 회원 테이블 조인 -> 1000만 번 탐색.
- **해결**: `WHERE` 조건이 회원 쪽에 있다면(예: `User.Name = 'Kim'`), 회원을 먼저 읽어서(10건 추출) 주문 테이블을 인덱스로 접근하도록 변경. -> 10번 탐색.

### 사례 2: Driven Table에 인덱스가 없는 경우
- **상황**: A(10건) -> B(100만 건) 조인. 순서는 맞음. 하지만 B의 조인 키에 인덱스 없음.
- **결과**: A의 1건마다 B 전체 스캔(Full Scan). 총 10 * 100만 = 1000만 건 액세스.
- **해결**: 
    1. B 테이블 조인 키에 인덱스 생성.
    2. Hash Join으로 변경 (`/*+ USE_HASH(A B) */`) 하여 스캔 부하 감소.

---

## 5. DB별 실행 계획 예제 (Execution Plan)

### 5.1 Oracle
```sql
SELECT /*+ LEADING(D) USE_NL(E) */ *
FROM EMP E, DEPT D
WHERE E.DEPTNO = D.DEPTNO;
```
**Execution Plan**:
```text
-----------------------------------------------------------------------
| Id  | Operation                    | Name    | Rows  | Bytes | Cost |
-----------------------------------------------------------------------
|   0 | SELECT STATEMENT             |         |    14 |   500 |    5 |
|   1 |  NESTED LOOPS                |         |    14 |   500 |    5 |
|   2 |   TABLE ACCESS FULL          | DEPT    |     4 |    80 |    3 |  <-- Driving (선행)
|*  3 |   TABLE ACCESS BY INDEX ROWID| EMP     |     3 |    80 |    1 |  <-- Driven (후행)
|*  4 |    INDEX RANGE SCAN          | IDX_EMP |     5 |       |    0 |
-----------------------------------------------------------------------
```
- `DEPT`(Id 2)가 먼저 실행되었으므로 Driving Table입니다.
- `EMP`(Id 3, 4)는 `DEPT`에서 나온 건수만큼 반복 수행됩니다.

### 5.2 MySQL
```sql
EXPLAIN SELECT * 
FROM t1 JOIN t2 ON t1.id = t2.id;
```
**Output**:
```text
+----+-------------+-------+-------+---------------+---------+---------+-------+------+-------------+
| id | select_type | table | type  | possible_keys | key     | key_len | ref   | rows | Extra       |
+----+-------------+-------+-------+---------------+---------+---------+-------+------+-------------+
|  1 | SIMPLE      | t1    | ALL   | PRIMARY       | NULL    | NULL    | NULL  |  100 | Using where | <-- Driving
|  1 | SIMPLE      | t2    | eq_ref| PRIMARY       | PRIMARY | 4       | t1.id |    1 | NULL        | <-- Driven
+----+-------------+-------+-------+---------------+---------+---------+-------+------+-------------+
```
- 위쪽(`t1`)에 나오는 테이블이 Driving Table입니다.
- `rows` 컬럼을 보면 t1은 100건, t2는 1건(ref)으로 조인됨을 알 수 있습니다.

---

## 6. 결론 및 요약 (Conclusion)

1. **Driving Table**은 "작은 집합(Small Row Source)"이어야 한다.
2. 테이블 자체의 크기보다는 **WHERE 조건으로 필터링된 후의 건수**가 중요하다.
3. **Driven Table**에는 반드시 **조인 키 인덱스**가 있어야 NL Join이 성립한다.
4. 옵티마이저가 잘못 선택할 경우 `LEADING` 힌트 등으로 순서를 바로잡아야 한다.

# Reference
- [Oracle Docs: Choice of Driving Table](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/joins.html)
- [MySQL Optimizer Guide](https://dev.mysql.com/doc/refman/8.0/en/nested-loop-joins.html)