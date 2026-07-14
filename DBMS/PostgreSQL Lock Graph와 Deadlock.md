---
id: PostgreSQL Lock Graph와 Deadlock
started: 2026-05-17
tags:
  - ✅DONE
  - PostgreSQL
  - Lock
group:
  - "[[DBMS]]"
---
# PostgreSQL Lock Graph와 Deadlock

## 1. 개요

Lock은 정합성을 지키지만 대기 관계가 길어지면 처리량과 P99를 무너뜨립니다. Deadlock은 Transaction들이 서로 가진 Lock을 기다리는 Cycle입니다.

```text
T1: Row A 보유 -> Row B 대기
T2: Row B 보유 -> Row A 대기
```

PostgreSQL은 Cycle을 감지해 Transaction 하나를 중단하지만 업무 Retry와 원인 제거는 애플리케이션 책임입니다.

---

## 2. Lock 종류

- Table-level Lock: DDL, DML과 Maintenance 충돌
- Row-level Lock: UPDATE, DELETE, `FOR UPDATE`
- Predicate Lock: Serializable의 충돌 감지
- Advisory Lock: 애플리케이션 정의 Lock
- Lightweight Lock: 내부 메모리 구조 동기화

`pg_locks`에 보이는 Lock과 실제 Row 대기 원인을 Query·Transaction과 연결해야 합니다.

---

## 3. Wait-for Graph

Node는 Backend Transaction이고 Edge는 “누가 누구를 기다리는가”입니다. `pg_blocking_pids(pid)`로 Blocker를 따라 Root Blocker를 찾습니다.

```sql
select pid, wait_event_type, wait_event,
       pg_blocking_pids(pid), query, xact_start
from pg_stat_activity
where wait_event_type is not null;
```

가장 오래 기다린 Query보다 모든 대기를 만든 Root Transaction을 먼저 봅니다.

---

## 4. Deadlock 원인

- Aggregate를 서로 다른 순서로 갱신
- 큰 Batch가 많은 Row를 오래 보유
- Foreign Key 검사와 Parent 삭제
- DDL과 장시간 DML 충돌
- 사용자 입력을 기다리는 열린 Transaction
- 외부 API 호출을 Transaction 안에서 수행

Lock 순서를 일정하게 만들고 Transaction을 짧게 유지하는 것이 기본 해결입니다.

---

## 5. Timeout

- `lock_timeout`: Lock 획득 대기 제한
- `statement_timeout`: Statement 전체 시간 제한
- `idle_in_transaction_session_timeout`: 열린 유휴 Transaction 제한
- `deadlock_timeout`: Deadlock 검사 시작 지연

Timeout은 피해를 제한하지만 원인을 제거하지 않습니다. 업무 Error로 변환하고 Retry 가능 여부를 분류합니다.

---

## 6. SKIP LOCKED

Outbox Worker는 `FOR UPDATE SKIP LOCKED`로 다른 Worker가 Claim한 Row를 건너뛸 수 있습니다. 병렬 처리에는 유리하지만 오래 잠긴 Row가 계속 건너뛰어지는 Starvation을 감시해야 합니다.

Oldest Pending Age와 Claim Lease를 함께 사용합니다.

---

## 7. DDL 운영

짧아 보이는 `ALTER TABLE`도 강한 Lock을 기다리며 뒤의 Query Queue를 막을 수 있습니다. `lock_timeout`을 짧게 두고, 큰 Index는 `CREATE INDEX CONCURRENTLY`, Constraint는 단계적 Validate를 검토합니다.

Migration 전 Lock Mode, Table Size와 Rollback을 확인합니다.

---

## 8. 관측과 대응

1. 사용자 영향과 대기 수를 확인합니다.
2. Root Blocker와 Transaction 시작 시간을 찾습니다.
3. Query, Client, 배포·Batch를 연결합니다.
4. 종료가 안전한지 Owner와 판단합니다.
5. Kill 후 Queue와 Replica Lag 회복을 봅니다.
6. Lock 순서·Transaction 범위를 수정합니다.

운영에서 무조건 `pg_terminate_backend`를 자동 실행하지 않습니다.

---

## 9. Test

두 Connection에서 반대 순서로 Row를 갱신해 Deadlock을 재현합니다. Application이 SQLSTATE를 Retryable Error로 분류하고 제한된 Backoff 후 전체 Transaction을 다시 수행하는지 검증합니다.

동일 Aggregate 동시 변경은 Optimistic Lock과 업무 충돌 응답도 비교합니다.

---

## 10. 완료 기준

- [ ] Root Blocker와 Wait-for Graph를 Query할 수 있습니다.
- [ ] Lock·Statement·Idle Timeout의 역할이 구분됩니다.
- [ ] Deadlock Retry가 Side Effect를 중복시키지 않습니다.
- [ ] DDL의 Lock Mode를 배포 전에 검토합니다.
- [ ] Lock Wait와 Long Transaction Alert·Runbook이 있습니다.

# Reference

- [PostgreSQL Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [Lock Monitoring](https://www.postgresql.org/docs/current/view-pg-locks.html)
- [[Isolation Level]]
