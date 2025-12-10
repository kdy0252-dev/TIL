---
id: DB 기본개념
started: 2025-05-08
tags:
  - ✅DONE
  - DB
group:
  - "[[DBMS]]"
---
# DB 기본개념 (Database Fundamentals)

## 1. 개요 (Overview)
**데이터베이스(Database, DB)**는 데이터를 효율적으로 저장, 검색, 수정, 삭제(CRUD)하기 위해 조직화된 데이터의 집합입니다. 이를 관리하는 소프트웨어를 **DBMS(Database Management System)**라고 합니다.
현대 IT 시스템의 근간이 되는 기술로, 관계형 데이터베이스(RDBMS)가 가장 널리 사용되며, 목적에 따라 NoSQL, NewSQL 등으로 분화되었습니다.

개발자로서 DB를 이해한다는 것은 단순히 SQL을 작성하는 것을 넘어, **데이터의 무결성(Integrity), 동시성(Concurrency), 성능(Performance)**을 어떻게 보장하는지 아키텍처 레벨에서 이해하는 것을 의미합니다.

---

## 2. 핵심 속성: ACID (트랜잭션의 4가지 성질)
트랜잭션(Transaction)은 데이터베이스의 상태를 변화시키는 하나의 논리적인 작업 단위입니다. 
신뢰성 있는 시스템을 위해 ACID 성질이 반드시 보장되어야 합니다.

1. **Atomicity (원자성)**
    - 트랜잭션 내의 모든 작업은 모두 성공하거나, 모두 실패해야 합니다 (All or Nothing).
    - **구현 기법**: **Undo Log** (트랜잭션 수행 중 오류 발생 시 실행 전 상태로 롤백).
2. **Consistency (일관성)**
    - 트랜잭션 수행 전후에 데이터베이스 제약조건(기본키, 외래키, 도메인 제약 등)을 위배하지 않아야 합니다.
    - 예: 잔액은 마이너스가 될 수 없다.
3. **Isolation (고립성/격리성)**
    - 여러 트랜잭션이 동시에 실행될 때, 서로의 연산에 끼어들거나 영향을 주지 않아야 합니다.
    - **구현 기법**: **Locking**, **MVCC** (Isolation Level 참조).
4. **Durability (영속성)**
    - 성공적으로 커밋된 트랜잭션의 결과는 시스템 장애(전원 차단 등)가 발생해도 영구적으로 보존되어야 합니다.
    - **구현 기법**: **Redo Log / WAL (Write Ahead Log)**. (데이터 파일에 쓰기 전에 로그 파일에 먼저 기록).

---

## 3. 데이터 모델링 및 정규화 (Normalization)
데이터 중복을 최소화하고 이상 현상(Anomaly: 삽입, 삭제, 갱신 이상)을 방지하기 위해 테이블을 분리하는 과정입니다.

### 3.1 주요 정규화 단계
- **제1정규형 (1NF)**: 모든 속성(Attribute)은 **원자값(Atomic Value)** 만을 가져야 한다. (반복 그룹 제어).
- **제2정규형 (2NF)**: 기본키가 복합키일 때, 부분 함수 종속을 제거한다. (완전 함수 종속 만족).
- **제3정규형 (3NF)**: 이행적 함수 종속을 제거한다. (A->B, B->C 이면 A->C 인 관계 분리).
- **BCNF (Boyce-Codd NF)**: 모든 결정자가 후보키여야 한다.

### 3.2 반정규화 (De-normalization)
- 정규화는 조회 시 조인(Join) 연산을 유발하여 성능 저하의 원인이 될 수 있습니다.
- 따라서 읽기 성능 최적화를 위해 의도적으로 테이블을 합치거나 중복 컬럼을 추가하는 것을 반정규화하고 합니다.
- **Trade-off**: 읽기 성능 UP vs 데이터 정합성 관리 비용 UP, 쓰기 성능 DOWN.

---

## 4. 인덱스(Index)의 원리
인덱스는 책의 '색인'과 같아서, **검색 속도($O(\log N)$)** 를 획기적으로 높여주지만, **추가적인 저장 공간**을 차지하고 **쓰기 성능($O(\log N)$ 비용 추가)** 을 떨어뜨립니다.

### 4.1 B-Tree (Balanced Tree)
- 대부분의 RDBMS가 사용하는 표준 인덱스 구조입니다.
- 최상위 루트(Root)에서 리프(Leaf)까지 항상 같은 깊이(Height)를 유지하여 균일한 검색 속도를 보장합니다.
- 리프 노드는 실제 데이터의 주소(ROWID)를 가리키거나(Clustered Index 제외), 정렬된 Linked List 형태로 연결되어 범위 검색(Range Scan)에 유리합니다.

### 4.2 Clustered vs Non-Clustered Index
- **Clustered Index**: 데이터 자체가 인덱스 순서대로 물리적으로 정렬되어 저장됩니다. (테이블 당 1개, 주로 PK). 범위 검색에 매우 빠름.
- **Non-Clustered Index**: 인덱스와 데이터가 분리되어 있으며, 인덱스 리프 노드가 데이터 페이지를 가리킵니다.

---

## 5. SQL 종류 및 실행 순서

### 5.1 SQL 분류
- **DDL (Data Definition Language)**: 구조 정의. `CREATE`, `ALTER`, `DROP`, `TRUNCATE`. (Auto Commit 되는 경우가 많음).
- **DML (Data Manipulation Language)**: 데이터 조작. `SELECT`, `INSERT`, `UPDATE`, `DELETE`. (트랜잭션 제어 대상).
- **DCL (Data Control Language)**: 권한 제어. `GRANT`, `REVOKE`.
- **TCL (Transaction Control Language)**: `COMMIT`, `ROLLBACK`, `SAVEPOINT`.

### 5.2 SELECT 문 실행 순서 (논리적 순서)
이 순서를 알아야 쿼리 작성 및 튜닝 시 오류를 피할 수 있습니다 (예: WHERE 절에서 Alias 사용 불가).
1. **FROM** (테이블 가져오기)
2. **ON / JOIN** (테이블 결합)
3. **WHERE** (행 필터링)
4. **GROUP BY** (그룹핑)
5. **HAVING** (그룹 필터링)
6. **SELECT** (컬럼 선택)
7. **DISTINCT** (중복 제거)
8. **ORDER BY** (정렬)
9. **LIMIT / OFFSET** (개수 제한)

---

## 6. 데이터베이스 아키텍처 구성 요소 (Internal)
DBMS가 어떻게 데이터를 저장하고 관리하는지 간단히 알아봅니다.

### 6.1 저장 엔진 (Storage Engine)
- 실제 디스크에 데이터를 저장하고 읽는 역할을 합니다.
- MySQL의 경우 플러그인 방식으로 교체 가능합니다.
    - **InnoDB**: 트랜잭션 지원, Row-level Locking, 외래키 지원. (사실 표준).
    - **MyISAM**: 트랜잭션 미지원, Table-level Locking. (과거 유산).

### 6.2 버퍼 관리자 (Buffer Manager)
- 디스크 I/O는 매우 느리므로, 자주 사용하는 데이터 블록을 메모리(**Buffer Pool**)에 캐싱합니다.
- `LRU (Least Recently Used)` 알고리즘 등을 사용하여 효율적으로 메모리를 관리합니다.
- DB 튜닝의 핵심은 **Disk I/O를 줄이고 Buffer Hit Ratio를 높이는 것**입니다.

### 6.3 로그 관리자 (Log Manager)
- **Undo Log**: 롤백과 MVCC를 위함. (트랜잭션의 이전 값 저장).
- **Redo Log**: 장애 복구를 위함. (변경된 내용을 순차적으로 기록).

---

## 7. 예제 (Example)

### 간단한 뱅킹 트랜잭션 시나리오
```sql
-- 트랜잭션 시작
START TRANSACTION;

    -- 1. A 계좌 확인 (Locking을 위해 FOR UPDATE)
    SELECT balance FROM accounts WHERE id = 1 FOR UPDATE;
    
    -- 2. 출금
    UPDATE accounts SET balance = balance - 10000 WHERE id = 1;
    
    -- 3. 입금
    UPDATE accounts SET balance = balance + 10000 WHERE id = 2;

-- 모든 과정이 성공하면 커밋
COMMIT;
-- 중간에 에러나면 ROLLBACK;
```

---

## 8. 최신 트렌드: NoSQL과 NewSQL
- **NoSQL (Not Only SQL)**:
    - 스키마가 없거나 유연함(Schemaless).
    - 수평적 확장(Scale-out)이 쉬움.
    - 예: MongoDB(Document), Redis(Key-Value), Cassandra(Column).
    - **CAP 이론**: 분산 환경에서 Consistency, Availability, Partition Tolerance를 모두 만족할 수 없다의 트레이드오프.
- **NewSQL**:
    - RDBMS의 SQL/ACID와 NoSQL의 확장성을 결합하려는 시도.
    - 예: CockroachDB, Google Spanner.

# Reference
- [Database System Concepts (Silberschatz)](https://www.db-book.com/)
- [Real MySQL 8.0](http://www.yes24.com/Product/Goods/103415627)
- [CMU 15-445/645 Intro to Database Systems](https://15445.courses.cs.cmu.edu/)
