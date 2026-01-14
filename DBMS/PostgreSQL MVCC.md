---
id: PostgreSQL MVCC
started: 2026-01-15
tags:
  - ✅DONE
  - DBMS
  - PostgreSQL
  - MVCC
  - Concurrency
  - Architecture
group:
  - "[[DBMS]]"
---
# PostgreSQL MVCC
## 개요 (Executive Summary)

현대적인 데이터베이스 시스템에서 높은 동시성(High Concurrency)을 보장하는 것은 시스템 가용성의 핵심이다. PostgreSQL은 이를 달성하기 위해 **MVCC(Multi-Version Concurrency Control)** 기술을 채택하고 있다. MVCC는 읽기 작업과 쓰기 작업이 서로를 블로킹하지 않도록 설계되어 있어, 대규모 트래픽 환경에서도 안정적인 성능을 제공한다.

---
## MVCC의 기본 철학 및 존재 이유

### 1. Lock 기반 동시성 제어의 한계
전통적인 데이터베이스는 데이터 정합성을 위해 락(Lock)을 사용한다. 하지만 읽기 세션이 쓰기 세션을 기다리거나, 반대의 상황이 빈번하게 발생하면 전체 처리량(Throughput)이 급감한다.

### 2. "읽기는 쓰기를 막지 않고, 쓰기는 읽기를 막지 않는다"
MVCC의 핵심은 특정 시점의 데이터 스냅샷(Snapshot)을 제공하여, 여러 트랜잭션이 동일한 데이터의 서로 다른 버전(Version)을 동시에 보게 하는 것이다. 이를 통해 PostgreSQL은 읽기 작업에 물리적 락을 걸지 않고도 일관된 읽기를 보장한다.

---
## 내부 데이터 구조: 튜플 헤더 (Tuple Header Anatomy)

PostgreSQL은 모든 행(Tuple)에 대해 약 23-28바이트의 추가적인 메타데이터를 저장한다. 이 메타데이터가 MVCC 구현의 핵심이다.

### 1. 핵심 제어 필드
- **xmin**: 튜플을 삽입한 트랜잭션의 ID (XID)이다. 이 값은 해당 튜플이 생성된 시점을 나타낸다.
- **xmax**: 튜플을 삭제하거나 업데이트한 트랜잭션의 ID이다. 초기 생성 시에는 0으로 설정되며, 값이 존재한다면 해당 튜플은 '만료'되었거나 삭제 대기 중임을 의미한다.
- **cmin / cmax**: 단일 트랜잭션 내에서 여러 명령을 실행할 때의 순서를 관리하기 위한 Command Identifier이다.
- **ctid**: 튜플의 물리적 위치(페이지 번호 + 오프셋)를 나타내며, 업데이트 시 새로운 버전의 튜플 위치를 가리키는 링크로도 활용된다.

### 2. Hint Bits (성능 최적화 요인)
매번 시스템 카탈로그(clog)를 조회하여 트랜잭션의 상태(Commit/Rollback)를 확인하는 것은 비 효율적이다. 따라서 한 번 확인된 상태를 튜플 헤더의 비트 필드에 기록해 두는데, 이를 **Hint Bits**라 한다.

---
## 가시성 판단 로직 (Visibility Check Mechanism)

특정 트랜잭션이 특정 튜플을 볼 수 있는지 여부는 시스템 상의 트랜잭션 수명과 튜플 헤더의 정보를 대조하여 판단한다.

### 1. 시스템 트랜잭션 로그 (Commit Log, clog)
PostgreSQL은 모든 트랜잭션의 상태를 저장한다:
- `IN_PROGRESS`: 실행 중
- `COMMITTED`: 커밋 완료
- `ABORTED`: 롤백 완료

### 2. 가시성 판단 공식
- **xmin이 커밋되지 않음**: 누구에게도 보이지 않는다. (단, 본인이 생성한 것이라면 제외)
- **xmin이 커밋되었으나 xmax가 0임**: 모든 이에게 보인다.
- **xmin이 커밋되었으나 xmax가 실행 중임**: 현재 시점에서는 보인다.
- **xmin이 커밋되었으나 xmax가 이미 커밋됨**: 해당 튜플은 'Dead' 상태이므로 보이지 않는다.

---
## 스냅샷 관리 (Snapshot Management)

격리 수준에 따라 스냅샷을 생성하고 관리하는 방식이 달라진다.

### 1. Transaction Snapshot의 구성
스냅샷은 특정 시점의 시스템 상태를 캡처한 것으로, 다음 정보를 포함한다.
- **xmin**: 현재 살아있는 트랜잭션 중 가장 작은 ID. (이보다 작은 ID는 모두 커밋됨이 보장됨)
- **xmax**: 지금까지 할당된 적 없는 가장 큰 ID + 1. (이보다 크거나 같은 ID는 모두 미래의 트랜잭션임)
- **xip_list**: xmin과 xmax 사이에서 현재 진행 중인(InProgress) 트랜잭션들의 목록.

### 2. 격리 수준별 스냅샷 생성 전략
- **Read Committed (Standard)**: 매 쿼리(Statement)가 시작될 때마다 새로운 스냅샷을 생성한다. 따라서 한 트랜잭션 내에서도 결과가 달라질 수 있다(Non-repeatable Read).
- **Repeatable Read**: 트랜잭션이 시작될 때 단 한 번의 스냅샷만 생성하고 고정한다. 이를 통해 트랜잭션 내내 일관된 데이터를 보장한다.
- **Serializable**: 실제 실행 순서를 분석하여 직렬화 가능성 위배 여부를 체크하는 SSI(Serializable Snapshot Isolation) 메커니즘을 추가로 가동한다.

---
## 물리적 업데이트 방식과 파급 효과

### 1. In-place Update 부재의 명암
PostgreSQL은 데이터를 직접 수정하지 않고 "새 행 삽입 + 구 행 만료" 방식을 취한다.
- **장점**: 대규모 읽기 쿼리가 돌아가는 중에도 쓰기 쿼리가 전혀 방해받지 않는다. 롤백이 매우 빠르다(단순히 clog 상태만 변경).
- **단점**: 인덱스 폭증 문제. 데이터가 업데이트될 때마다 모든 인덱스 항목이 새로운 위치를 가리키도록 업데이트되어야 한다(Write Amplification).

### 2. HOT (Heap Only Tuple) 최적화
인덱스 성능 저하를 막기 위한 핵심 기술이다.
- **조건**: 업데이트된 컬럼이 인덱스에 포함되지 않고, 새로운 튜플이 동일한 페이지(Page) 내에 보관될 때 발동한다.
- **동작**: 인덱스는 구버전 튜플을 가리키고, 구버전 튜플 헤더에서 신버전 튜플로 직접 체이닝(Chaining)한다. 이를 통해 인덱스 정보를 수정하지 않고도 업데이트를 처리한다.

---
## MVCC와 VACUUM
MVCC로 인해 필연적으로 발생하는 Dead Tuple은 누적될수록 시스템 성능을 갉아먹는다.
### 1. Bloat 및 공간 낭비
정리되지 않은 Dead Tuple은 테이블 부풀림(Bloat) 현상을 유발하며, 이는 Sequential Scan 성능을 저하시킨다.

### 2. 정주기적 청소의 필요성
- **VACUUM**: 앞서 설명한 xmin, xmax를 분석하여 더 이상 그 누구도 보지 못하게 된 튜플을 물리적으로 정리하고 공간을 비워준다.
- **Hint Bits 업데이트**: VACUUM은 스캔 과정에서 튜플들의 Hint Bits를 영구적으로 확정짓는 작업도 병행하여 쿼리 시의 부하를 줄인다.

---
## 실무적 고려사항 및 벤치마킹 포인트

### 1. 트랜잭션 시간의 제어
Long Running Transaction은 MVCC 환경에서 '독'이다. 하나라도 오래된 트랜잭션이 살아있으면 시스템 전체의 Dead Tuple 정리가 중단된다.

### 2. 모니터링 주요 지표
- `pg_stat_activity`의 `xact_start`: 가장 오래된 트랜잭션의 경과 시간 확인.
- `pg_stat_user_tables`의 `n_dead_tup`: 누적된 가비지 데이터량 측정.

---
## 동시성의 대가는 관리의 정밀함이다

PostgreSQL의 MVCC는 읽기 무중단이라는 강력한 이점을 제공하지만, 내부적으로는 여러 버전의 데이터를 관리하고 주기적으로 청소해야 하는 부하를 수반한다. 엔지니어는 MVCC의 튜플 구조와 가시성 판단 원리를 명확히 이해함으로써, 단순한 쿼리 튜닝을 넘어 시스템 전반의 효율을 극대화하는 설계를 수행할 수 있다.

# Reference
- **PostgreSQL 공식 문서**: [Concurrency Control - MVCC](https://www.postgresql.org/docs/current/mvcc.html)
- **Internals of PostgreSQL**: [Chapter 5. Concurrency Control](https://www.interdb.jp/pg/pgsql05.html)
- **Hironobu Suzuki**: [The Internals of PostgreSQL (Technological Standard)](https://www.postgresql.fastware.com/blog/internals-of-postgresql-concurrency-control)
- **Crunchy Data Blog**: [Understanding Postgres MVCC](https://www.crunchydata.com/blog/postgreSQL-mvcc)
