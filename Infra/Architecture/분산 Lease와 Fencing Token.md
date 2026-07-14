---
id: 분산 Lease와 Fencing Token
started: 2026-06-04
tags:
  - ✅DONE
  - Distributed-System
  - Fencing-Token
group:
  - "[[Architecture]]"
---
# 분산 Lease와 Fencing Token

## 1. Lock과 Lease

Lock은 소유자가 해제할 때까지 권리를 부여하지만 Lease는 만료 시간이 있는 권리입니다. 분산 시스템에서는 Process Pause, Network Partition 때문에 소유자가 자신이 권리를 잃었다는 사실을 모를 수 있습니다.

---

## 2. 오래된 소유자 문제

```text
Worker A Lease 획득
  -> 긴 GC Pause
  -> Lease 만료
Worker B 새 Lease 획득 후 쓰기
  -> Worker A 복귀 후 다시 쓰기
```

A의 마지막 쓰기가 B의 최신 결과를 덮으면 Lock Service가 정상이어도 데이터가 깨집니다.

---

## 3. Fencing Token

Lease를 획득할 때마다 단조 증가 Token을 발급합니다.

```text
A token=41
B token=42
Storage가 42를 수락한 뒤 41의 쓰기를 거부
```

핵심은 Lock 획득이 아니라 최종 Storage가 Token을 비교해 오래된 Writer를 차단하는 것입니다.

---

## 4. 구현 모델

Table에 `fencing_token` 또는 `version`을 저장하고 조건부 갱신합니다.

```sql
update resource
set value = :value, fencing_token = :token
where id = :id and fencing_token < :token;
```

영향 Row가 0이면 권리를 잃은 Writer입니다. Token 발급과 업무 상태 변경의 Transaction 경계를 명확히 합니다.

---

## 5. Clock을 믿지 않는 이유

Client Wall Clock은 Drift와 조정이 발생합니다. `expires_at`만 비교해 권한을 증명하지 말고 Lock Service의 순서와 Storage의 Fencing을 사용합니다.

시간은 만료 판단에 쓰일 수 있지만 Writer 선후 관계의 유일한 근거로 쓰기 어렵습니다.

---

## 6. Redis Lock의 한계

`SET NX PX`와 Token 일치 삭제는 다른 소유자의 Lock을 지우는 문제를 막지만, 만료 뒤 오래된 Writer의 외부 Side Effect까지 차단하지는 못합니다.

외부 Provider가 Fencing Token을 받지 않으면 Idempotency Key, Provider 상태 조회와 Reconciliation을 결합합니다.

---

## 7. DB Claim과 Lease

Outbox의 `claimed_until`은 Lease입니다. Worker가 만료 뒤 완료 처리할 때 현재 Claim Token과 상태를 조건부 검사해야 합니다.

Oldest Job, Lease 만료, 중복 Claim과 Stale Completion 거부 수를 Metric으로 남깁니다.

---

## 8. Leader Election

Leader Lease도 같은 문제를 가집니다. Leader만 Scheduler를 실행해도 이전 Leader가 Pause 후 복귀할 수 있습니다. 중요한 쓰기는 Leader 여부 외에 Epoch/Fencing을 검증합니다.

Kubernetes Lease Object는 조정에 유용하지만 외부 DB 쓰기를 자동 보호하지 않습니다.

---

## 9. Test

1. Worker A가 Lease를 획득합니다.
2. A를 Pause합니다.
3. Lease 만료 후 B가 작업을 완료합니다.
4. A를 복귀시킵니다.
5. A의 오래된 쓰기가 거부되는지 확인합니다.

Network 지연과 DB Commit 지연도 같은 방식으로 주입합니다.

---

## 10. 완료 기준

- [ ] Lease 만료와 Lock 해제의 차이를 설명합니다.
- [ ] Token이 단조 증가하고 재사용되지 않습니다.
- [ ] Storage가 오래된 Token을 원자적으로 거부합니다.
- [ ] Stale Writer Test가 자동화되어 있습니다.
- [ ] 외부 Side Effect는 멱등성과 Reconciliation으로 보호합니다.

# Reference

- [[신뢰성 있는 비동기 처리]]
- [[멱등성과 Reconciliation]]
- [[RDS와 ElastiCache 데이터 계층]]
