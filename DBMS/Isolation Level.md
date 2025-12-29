---
id: Isolation Level
started: 2025-05-14
tags:
  - ✅DONE
group: []
---
# Isolation Level (트랜잭션 격리 수준)

## 1. 개요 (Overview)
**Isolation Level(격리 수준)** 은 트랜잭션의 ACID 성질 중 **Isolation** 을 보장하기 위한 설정으로, 동시에 여러 트랜잭션이 수행될 때 서로의 데이터에 미치는 영향을 제어하는 단계를 의미합니다.

데이터베이스는 동시성(Concurrency)과 무결성(Data Integrity)라는 상충되는 두 가지 목표를 달성해야 합니다.
- **격리 수준이 높으면**: 데이터 무결성은 완벽해지지만, 락킹(Locking)으로 인해 동시성이 떨어져 성능이 저하됩니다.
- **격리 수준이 낮으면**: 동시성은 높아지지만, **Dirty Read**, **Phantom Read** 등의 데이터 이상 현상(Anomaly)이 발생할 수 있습니다.

SQL 표준(ANSI/ISO SQL Standard)에서는 4가지 등급을 정의하고 있으며, 각 DBMS(Oracle, MySQL, PostgreSQL)마다 구현 방식과 기본값이 다릅니다.

---

## 2. 4가지 격리 수준 상세 비교 (Detail Comparison)

| Level | Name | Dirty Read | Non-Repeatable Read | Phantom Read | 특징 및 대표 DB |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **0** | **Read Uncommitted** | O | O | O | 커밋 전 데이터 읽기 허용. 정합성 깨짐. (SQL Server 등에서 명시적 사용 아니면 잘 안씀) |
| **1** | **Read Committed** | X | O | O | **Oracle, PostgreSQL, SQL Server 기본값**. 커밋된 데이터만 읽음. |
| **2** | **Repeatable Read** | X | X | O | **MySQL 기본값**. 트랜잭션 내 동일 조회 보장. Phantom Read 발생 가능(MySQL은 거의 방지). |
| **3** | **Serializable** | X | X | X | 완벽한 격리. 성능 저하 심함. |

---

## 3. 이상 현상 시나리오 (Anomalies Scenarios)

### 3.1 Dirty Read (오손 읽기)
- **정의**: 다른 트랜잭션이 수정(Insert/Update)했으나 아직 **커밋하지 않은(Uncommitted)** 데이터를 읽는 현상.
- **시나리오**:
    1. 트랜잭션 A: 계좌 잔액을 100원에서 200원으로 변경 (아직 커밋 안 함).
    2. 트랜잭션 B: 계좌 잔액 조회 -> 200원이 조회됨 (**Dirty Data**).
    3. 트랜잭션 A: 오류 발생으로 **Rollback** 수행 -> 잔액은 다시 100원이 됨.
    4. 트랜잭션 B: 200원인 줄 알고 인출 시도 -> **데이터 정합성 오류 발생**.
- **해결**: 최소 **Read Committed** 이상 설정 필요.

### 3.2 Non-Repeatable Read (반복 불가능한 읽기)
- **정의**: 한 트랜잭션 내에서 **같은 쿼리를 두 번** 실행했는데, 그 사이에 다른 트랜잭션이 **값을 수정(Update)하거나 삭제(Delete)** 하여 결과 값이 달라지는 현상.
- **시나리오**:
    1. 트랜잭션 A: `SELECT balance FROM account WHERE id=1;` -> 100원 조회.
    2. 트랜잭션 B: `UPDATE account SET balance=150 WHERE id=1;` 수행 및 **Commit**.
    3. 트랜잭션 A: `SELECT balance FROM account WHERE id=1;` -> 150원 조회. (**값이 바뀜**)
- **해결**: **Repeatable Read** 이상 설정 필요. (트랜잭션 시작 시점의 스냅샷을 읽어야 함)

### 3.3 Phantom Read (유령 읽기)
- **정의**: 한 트랜잭션 내에서 같은 쿼리(주로 Range Scan)를 두 번 실행했는데, 첫 번째에는 없던 결과 행이 **새로 생성(Insert)** 되어 나타나는 현상.
- **시나리오**:
    1. 트랜잭션 A: `SELECT * FROM users WHERE age > 20;` -> 2건 조회됨.
    2. 트랜잭션 B: `INSERT INTO users (name, age) VALUES ('C', 25);` 수행 및 **Commit**.
    3. 트랜잭션 A: 다시 `SELECT * FROM users WHERE age > 20;` 수행 -> 3건 조회됨. (**유령 데이터 출몰**)
- **해결**:
    - 일반적: **Serializable** 레벨 필요.
    - MySQL InnoDB: **Repeatable Read**에서도 **Next-Key Lock**을 통해 Phantom Read를 방지함.

---

## 4. MVCC와 격리 수준 구현 (MVCC Mechanism)

현대 RDBMS는 락(Lock)만으로 격리 수준을 구현하지 않고, **MVCC(Multi-Version Concurrency Control)** 기술을 사용합니다.
데이터를 덮어쓰는 게 아니라, 변경 전 데이터를 **Undo Log(Oracle/MySQL)** 나 **구 버전 Row(PostgreSQL)** 형태로 보관하여, 읽기 작업과 쓰기 작업이 서로를 방해하지 않게 합니다.

### 4.1 Read Committed에서의 MVCC
- 쿼리가 시작되는 시점마다 새로운 스냅샷을 뜹니다.
- 따라서 트랜잭션 중간에 다른 트랜잭션이 커밋하면, 다음 쿼리 시점에는 그 커밋된 최신 데이터를 읽어옵니다. (Non-Repeatable Read 발생)

### 4.2 Repeatable Read에서의 MVCC
- **트랜잭션이 시작되는 시점(First Read)** 을 기준으로 스냅샷을 고정합니다.
- 트랜잭션 번호(Transaction ID)를 비교하여, 자신보다 이후에 시작된 트랜잭션이 변경한 데이터는 무시하고 Undo Log에 있는 **과거 버전**을 읽습니다.
- 이를 통해 락을 걸지 않고도(Consistent Read) 반복 읽기 정합성을 보장합니다.

---

## 5. DB별 특징 및 주의사항 (DB Specifics)

### 5.1 MySQL (InnoDB)
- **기본값**: **Repeatable Read**.
- **특징**:
    - **갭 락(Gap Lock)**: 인덱스 레코드 사이의 간격(Gap)에 락을 걸어서, 다른 트랜잭션이 그 사이에 데이터를 끼워 넣는 것(Insert)을 방지합니다.
    - **Next-Key Lock**: Record Lock + Gap Lock. 이를 통해 Repeatable Read 수준에서도 Phantom Read를 막습니다.
    - **주의**: 오라클처럼 생각하고 개발하면 데드락(Deadlock)을 자주 만날 수 있습니다. (갭 락 때문)

### 5.2 Oracle
- **기본값**: **Read Committed**.
- **특징**:
    - Repeatable Read 등급을 명시적으로 지원하지 않습니다. (Serializable로 넘어가야 함)
    - 하지만 `SELECT ... FOR UPDATE` 등을 적절히 사용하여 비관적 락(Pessimistic Lock)으로 해결하는 패턴이 많습니다.
    - Undo Segment를 매우 효율적으로 관리하여 MVCC 성능이 뛰어납니다.

### 5.3 PostgreSQL
- **기본값**: **Read Committed**.
- **특징**:
    - Update 시 새로운 Row를 Insert하고 기존 Row를 Dead Tuple로 마킹하는 방식(Append-only)을 씁니다.
    - 따라서 Vacuum(청소) 작업이 필수적입니다.
    - Repeatable Read 레벨에서 Serialization Anomaly(직렬화 이상)를 감지하면 오류를 뱉고 롤백시킵니다.

---

## 6. 예제 및 테스트 코드 (Example)

### 6.1 Spring Boot Transaction
```java
@Service
public class TransferService {

    // 1. 일반적인 조회/수정 (DB 기본값 따름 - 보통 Read Committed)
    @Transactional(isolation = Isolation.DEFAULT)
    public void defaultLogic() {
        // ...
    }

    // 2. 민감한 정산 로직 (MySQL에서는 Phantom 방지됨)
    // - 중간에 데이터가 바뀌면 안 될 때
    @Transactional(isolation = Isolation.REPEATABLE_READ) 
    public void strictLogic(Long accountId) {
        Account account = repository.findById(accountId).orElseThrow();
        // 긴 작업 수행...
        
        // 다시 조회해도 account의 잔액은 처음과 동일함을 보장
        Account checkAgain = repository.findById(accountId).orElseThrow();
    }

    // 3. 최고 수준 격리 (성능 주의)
    // - 동시 수정이 절대 발생하면 안 되는 경우
    @Transactional(isolation = Isolation.SERIALIZABLE)
    public void serializableLogic() {
        // 이 안에서의 SELECT는 암시적으로 공유 락(Shared Lock)을 걸 수 있음
    }
}
```

### 6.2 SQL 시뮬레이션

**시나리오: Repeatable Read 검증**

**Session A**:
```sql
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
START TRANSACTION;

SELECT balance FROM account WHERE id = 1; 
-- 결과: 1000
```

**Session B**:
```sql
START TRANSACTION;
UPDATE account SET balance = 2000 WHERE id = 1;
COMMIT;
-- Session B는 2000원으로 바꾸고 커밋 완료.
```

**Session A**:
```sql
-- 다시 조회
SELECT balance FROM account WHERE id = 1;
-- MySQL(RR): 1000 (트랜잭션 시작 시점 스냅샷 유지 - Undo Log 조회)
-- Oracle(RC): 2000 (커밋된 최신 값 조회 - Non-Repeatable Read 발생)
```

---

## 7. 운영 및 튜닝 포인트 (Operational Tips)

1. **격리 수준은 낮을수록 좋다?**: 성능 면에서는 그렇지만, 데이터 정합성이 깨져서 발생하는 비즈니스 비용(정산 오류 등)이 훨씬 클 수 있습니다. 기본값(Read Committed or Repeatable Read)을 유지하되, 꼭 필요한 곳에만 `For Update` 락이나 상위 레벨을 적용하세요.
2. **Deadlock 모니터링**: 격리 수준을 높이면 락 범위가 넓어져(Gap Lock 등) 데드락 발생 확률이 높아집니다. 애플리케이션 로그에서 `Deadlock found when trying to get lock` 에러를 주시해야 합니다.
3. **Long Transaction 방지**: 트랜잭션이 길어지면 MVCC를 위해 유지해야 하는 Undo Log(Postgres의 경우 Dead Tuple)가 무한정 쌓여 DB 성능 전체를 떨어뜨립니다. 가능한 트랜잭션은 짧게 유지하세요.

# Reference
- [Real MySQL 8.0](http://www.yes24.com/Product/Goods/103415627)
- [PostgreSQL Documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [Oracle Transaction isolation levels](https://docs.oracle.com/en/database/oracle/oracle-database/19/cncpt/data-concurrency-and-consistency.html)
[Isolation Level](https://mangkyu.tistory.com/299)