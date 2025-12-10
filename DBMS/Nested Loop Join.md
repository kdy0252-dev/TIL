---
id: Nested Loop Join
started: 2025-05-23
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# Nested Loop Join (NL Join)

## 1. 개요 (Overview)
**Nested Loop Join (NL Join)**은 가장 기본적이고 전통적인 조인 바식으로, 프로그래밍의 **중첩 반복문(Double For Loop)**과 완전히 동일한 메커니즘으로 동작합니다.
OLTP(Online Transaction Processing) 시스템에서 **소량의 데이터를 실시간으로 조회**할 때 가장 빠른 응답 속도를 보장합니다.

NL 조인의 핵심은 **"Driving Table(Outer Table)의 처리 범위를 얼마나 줄일 수 있는가"** 와 **"Driven Table(Inner Table)의 조인 키에 인덱스가 존재하는가"** 입니다.
이 두 가지 조건에 따라 성능이 극적으로 달라지며, 대용량 데이터 처리에는 부적합한 경우가 많습니다.

---

## 2. 동작 메커니즘 (Internal Mechanism)

### 2.1 기본 알고리즘 (Basic Algorithm)
```java
// JAVA Pseudo Code로 보는 NL Join
for (Record outerRow : outerTable) { // 1. Outer Table 스캔
    for (Record innerRow : innerTable) { // 2. Inner Table 스캔
        if (outerRow.joinKey == innerRow.joinKey) { // 3. 조인 조건 비교
            result.add(combine(outerRow, innerRow)); // 4. 결과 반환
        }
    }
}
```
DB 내부에서는 Inner Table 스캔 시 **인덱스(Index)** 를 활용한다는 점이 일반 루프와 다릅니다.

### 2.2 상세 수행 과정
1. **Driving Table 결정**: 옵티마이저는 조건절(`WHERE`)을 통해 필터링된 결과 건수가 가장 적을 것으로 예상되는 테이블을 **Driving Table(선행 테이블)** 로 선택합니다.
2. **First Row Fetch**: Driving Table에서 조건에 맞는 첫 번째 행을 읽습니다.
3. **Index Probe**: 읽은 행의 조인 키(Join Key) 값을 가지고 **Driven Table(후행 테이블)** 의 인덱스를 탐색(Index Lookup)합니다.
4. **Random Access**: 인덱스 리프 노드에서 얻은 `ROWID`를 이용해 Driven Table의 실제 데이터 블록(Data Block)을 액세스합니다. (**Random I/O 발생 지점**)
    - 만약 인덱스에 필요한 모든 컬럼이 있다면(Covering Index), 테이블 액세스는 생략됩니다.
5. **Filter Check**: 테이블에서 읽은 데이터가 조인 조건 외의 다른 조건들도 만족하는지 확인합니다.
6. **Result Return**: 만족하면 운반 단위(Array Size)에 채워서 클라이언트에 전송합니다.
7. **Loop**: Driving Table의 모든 행을 다 읽을 때까지 2~6 과정을 반복합니다.

---

## 3. 성능 결정 요소 (Performance Factors)

### 3.1 Random Access 부하
NL Join의 가장 큰 병목은 **Random Access**입니다.
Driving Table이 1,000건이고 Driven Table의 매칭 건수가 1건이라면, Driven Table에 대해 최대 1,000번의 인덱스 탐색과 1,000번의 테이블 랜덤 액세스가 발생합니다.
만약 Driving Table이 100만 건이라면? 100만 번의 랜덤 I/O가 발생하여 DB 서버는 마비될 수 있습니다.
-> **"NL Join은 대용량 데이터 조인에 절대적으로 불리하다."**

### 3.2 조인 연결 고리 인덱스 (Join Key Index)
Driven Table의 조인 컬럼에 **인덱스**가 없으면 어떤 일이 일어날까요?
Driving Table의 **모든 로우마다** Driven Table을 **Full Table Scan** 해야 합니다. ($O(N \times M)$)
이는 재앙에 가까운 성능 저하를 초래하므로, **NL Join에서 후행 테이블의 인덱스는 필수**입니다.

### 3.3 조인 순서 (Join Order)
Driving Table은 무조건 **"필터링 후 건수가 적은 테이블"** 이어야 합니다.
- A 테이블(100건)과 B 테이블(100만 건)을 조인할 때:
    - A -> B (NL Join): A 100건에 대해 B 인덱스 100번 탐색. (빠름)
    - B -> A (NL Join): B 100만 건에 대해 A 인덱스 100만 번 탐색. (느림)
- 따라서 옵티마이저가 순서를 잘못 잡으면 힌트(`/*+ ORDERED */`, `/*+ LEADING(A) */`)로 교정해야 합니다.

---

## 4. 고급 조인 기법 (Advanced Techniques)

### 4.1 Block Nested Loop Join (BNL) - MySQL
Driven Table에 인덱스가 없을 때, 매번 풀 스캔하는 것을 방지하기 위한 기법입니다.
1. Driving Table에서 읽은 레코드를 메모리의 **Join Buffer**에 가득 찰 때까지 적재합니다.
2. Join Buffer가 다 차면, Driven Table을 **한 번 Full Scan** 합니다.
3. Driven Table의 한 행을 읽을 때마다 Join Buffer에 있는 **모든** 레코드와 비교합니다.
4. 결과적으로 Driven Table의 Full Scan 횟수를 1/N(버퍼 크기만큼)로 줄여줍니다.
> **Note**: MySQL 8.0.18부터는 BNL 대신 Hash Join이 사용되므로 BNL은 거의 사라지는 추세입니다.

### 4.2 Batched Key Access (BKA) & Multi-Range Read (MRR)
랜덤 액세스의 비효율을 줄이기 위한 최적화입니다.
- **MRR**: 인덱스를 통해 얻은 ROWID들을 **정렬**하여, 디스크 블록을 순차적으로(Sequential) 읽을 수 있게 합니다.
- **BKA**: Driving Table의 키들을 버퍼에 모으고(Batch), MRR 기능을 사용하여 Driven Table을 한꺼번에 조인합니다. 랜덤 I/O를 획기적으로 줄여줍니다.

### 4.3 Prefetching (Oracle)
Oracle은 `TABLE ACCESS BY INDEX ROWID` 시, 다음에 읽을 블록들을 미리 예측하여 디스크에서 읽어오는 **Prefetching** 기능을 통해 랜덤 액세스 대기 시간을 줄입니다. 실행 계획에 `TABLE ACCESS BY INDEX ROWID BATCHED` 로 나타납니다.

---

## 5. 실행 계획 및 튜닝 (Execution & Tuning)

### 5.1 Oracle Execution Plan
```text
--------------------------------------------------------------------------------------
| Id  | Operation                    | Name    | Rows  | Bytes | Cost (%CPU)| Time     |
--------------------------------------------------------------------------------------
|   0 | SELECT STATEMENT             |         |     5 |   200 |    10   (0)| 00:00:01 |
|   1 |  NESTED LOOPS                |         |     5 |   200 |    10   (0)| 00:00:01 | -- (3)
|   2 |   TABLE ACCESS BY INDEX ROWID| EMP     |     5 |   100 |     5   (0)| 00:00:01 | -- (1) Driving
|*  3 |    INDEX RANGE SCAN          | IDX_EMP |     5 |       |     2   (0)| 00:00:01 |
|   4 |   TABLE ACCESS BY INDEX ROWID| DEPT    |     1 |    20 |     1   (0)| 00:00:01 | -- (2) Driven
|*  5 |    INDEX UNIQUE SCAN         | PK_DEPT |     1 |       |     0   (0)| 00:00:01 |
--------------------------------------------------------------------------------------
```
- **해석**:
    - ID 3(`IDX_EMP`) -> ID 2(`EMP`): Driving Table 액세스.
    - ID 1(`NESTED LOOPS`): 루프 시작.
    - ID 5(`PK_DEPT`) -> ID 4(`DEPT`): Driving의 각 행마다 Driven 인덱스 탐색 및 테이블 액세스.
    - Driven Table(`DEPT`) 접근 시 `INDEX UNIQUE SCAN`을 사용하므로 매우 효율적임.

### 5.2 튜닝 포인트
1. **인덱스 유무 확인**: Driven Table의 조인 컬럼(`DEPT.DEPTNO`)에 인덱스가 있는가?
2. **부분 범위 처리 활용**: 화면 페이징 쿼리 등에서 `ROWNUM <= 10` 조건을 준다면, 전체 데이터를 다 읽지 않고 앞부분만 읽고 멈출 수 있는 NL Join이 Hash/Merge Join보다 훨씬 유리합니다.
3. **조인 순서 변경**:
    - `/*+ LEADING(table_name) */` 힌트로 Driving Table을 변경해 봅니다.
    - Driving Table은 "조건에 의해 많이 걸러지는 테이블"이어야 합니다.

---

## 6. 장단점 요약 (Summary)

| 구분 | 특징 |
| :--- | :--- |
| **적합한 데이터량** | **소량** (수십 ~ 수천 건 내외) |
| **응답성** | **First Row 반환 속도가 가장 빠름** (실시간 서비스 최적) |
| **메모리 사용** | 별도의 조인 메모리가 거의 필요 없음 (버퍼 캐시만 이용) |
| **CPU 사용** | 비교 연산이 적어 CPU 부하 낮음 (단, I/O 대기시간이 문제) |
| **최악의 시나리오** | Driving Table이 매우 크거나, Driven Table 인덱스가 없는 경우 |

## 7. 비교: NL Join vs Hash Join
- **NL Join**:
    - 랜덤 액세스(Random Access) 위주.
    - 소량 데이터, OLTP, 응답 속도 중요.
    - 인덱스 필수.
- **Hash Join**:
    - 해시 테이블 구성, CPU 연산 위주.
    - 대량 데이터, DW/Batch, 처리량(Throughput) 중요.
    - 인덱스 불필요.

## 8. 실전 Tip: "언제 NL Join을 써야 하는가?"
- **게시판 목록 조회**: 페이징 처리가 있고 유저가 앞 페이지만 주로 볼 때.
- **상세 조회**: Key-Value 형태의 단건 조회나 소량의 연관 데이터 조회.
- **코드성 테이블 조인**: 코드 테이블(매우 작음)과 메인 테이블 조인 시, 코드 테이블을 메모리에 캐싱하고 NL로 붙이면 빠름.

# Reference
- [Oracle Docs: Nested Loop Joins](https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/joins.html#GUID-17DB6695-18AD-4343-98D7-175F38E88F96)
- [Real MySQL 8.0: Nested Loop Join](http://www.yes24.com/Product/Goods/103415627)