---
id: 멱등성과 Reconciliation
started: 2026-05-25
tags:
  - ✅DONE
  - Architecture
  - Reliability
  - Idempotency
group:
  - "[[Java Spring Architecture]]"
---
# 멱등성과 Reconciliation

## 1. 개요 (Overview)
분산 시스템에서 Timeout은 작업이 실패했다는 뜻이 아니라 **결과를 모른다**는 뜻입니다. Client가 재시도하면 첫 요청과 두 번째 요청이 모두 처리될 수 있습니다. **멱등성(Idempotency)**은 같은 의도를 여러 번 실행해도 최종 결과가 같도록 만들고, **Reconciliation**은 두 시스템의 상태를 주기적으로 비교하여 누락과 불일치를 복구합니다.

---

## 2. 멱등성 계층

| 계층 | 기법 |
|---|---|
| HTTP | Idempotency-Key와 결과 저장 |
| Database | Unique Constraint, Upsert, 상태 조건부 Update |
| Message | Event ID 처리 이력 |
| 외부 API | Provider Idempotency Key·Reference ID |
| Migration | Source ID → Target ID Mapping |

애플리케이션의 사전 조회만으로는 동시 요청을 막을 수 없습니다. 최종 방어선은 Database Unique Constraint나 원자적 조건부 쓰기여야 합니다.

---

## 3. Idempotency Key

```text
POST /payments
Idempotency-Key: payment:booking-100:attempt-1
```

서버는 Key, Request Fingerprint, 처리 상태와 Response를 저장합니다. 같은 Key에 다른 Payload가 들어오면 기존 결과를 반환하지 않고 충돌로 거부해야 합니다.

Key의 Scope, TTL, 사용자·Tenant 경계를 명확히 정해야 합니다.

---

## 4. Event Consumer 멱등성

```sql
insert into processed_event(event_id, processed_at)
values (:event_id, now())
on conflict (event_id) do nothing;
```

처리 이력 저장과 업무 데이터 변경을 같은 Transaction에 포함합니다. 이력이 이미 있으면 Event를 다시 적용하지 않습니다.

---

## 5. Reconciliation

```text
Source of Truth
  -> 대상 목록 Page 조회
  -> Local 상태와 비교
  -> Missing / Different / Duplicate 분류
  -> 자동 복구 가능한 Action 생성
  -> 충돌·실패 Report
```

Reconciliation은 실시간 처리의 대체가 아니라, 재시도만으로 복구하지 못한 장기 불일치를 수정하는 Safety Net입니다.

---

## 6. 실무 사례 적용 관점
- Cognito 사용자와 Local 회원 계정을 주기적으로 비교하고 누락·불일치·중복을 분류합니다.
- Outbox Event ID와 Marker를 사용해 Metrics 중복 반영을 방지합니다.
- Legacy Migration은 Source System·Schema·Legacy ID로 Target Mapping을 Upsert하여 재실행할 수 있습니다.
- S3 이동 경로 Migration은 결정적인 Target Key와 결과 기록으로 재시도합니다.

---

## 7. In-flight Deduplication과 차이
In-flight Deduplication은 **현재 동시에 실행 중인 요청**만 합칩니다. Process 재시작, 긴 시간 후 재시도, 다른 Instance의 중복 요청은 막지 못합니다. 쓰기 작업의 정확성은 영속적인 Idempotency 설계로 보장해야 합니다.

---

## 8. 멱등성 상태 머신

```text
RECEIVED
  -> PROCESSING
      -> SUCCEEDED + Response
      -> FAILED_RETRYABLE
      -> FAILED_FINAL
```

동일 Key가 `PROCESSING`일 때 즉시 409를 반환할지, 완료를 기다릴지, 202와 조회 URL을 반환할지 API 계약으로 정합니다.

## 9. Request Fingerprint
Idempotency Key만 같고 Payload가 다르면 기존 결과를 반환하면 안 됩니다.

```text
fingerprint = SHA-256(
  canonical method + path + tenant + normalized payload
)
```

JSON Field 순서, 공백, 기본값을 정규화합니다. 인증 Token처럼 요청마다 바뀌지만 업무 의미와 무관한 값은 제외합니다.

## 10. 저장 Transaction
Idempotency Record와 업무 변경을 같은 Transaction에 저장해야 합니다.

```text
BEGIN
  -> Key를 Unique Insert 또는 Lock
  -> 업무 처리
  -> Result 저장
COMMIT
```

처리 전에 Key만 Commit하면 업무 실패 뒤 Key가 영구적으로 막힐 수 있습니다. 긴 외부 호출이 포함되면 상태와 Lease를 분리해 설계합니다.

## 11. TTL과 보관 기간
TTL은 Client가 재시도할 수 있는 최대 시간보다 길어야 합니다. 결제처럼 장기 중복이 치명적인 작업은 업무 Reference의 Unique Constraint를 영구 방어선으로 둡니다.

Response Body 전체 보관 비용, 개인정보 Retention과 Schema Evolution을 고려합니다.

## 12. Consumer 처리 Transaction

```text
BEGIN
  -> processed_event Unique Insert
  -> 업무 상태 변경
COMMIT
Ack
```

Ack가 실패해 Event가 재전달되어도 Unique Insert가 중복 적용을 막습니다. 외부 API 호출이 있다면 Outbox로 다음 단계에 넘깁니다.

## 13. Reconciliation 비교 전략
- Full Scan: 정확하지만 비용 큼
- Updated-since Cursor: 효율적이지만 누락 가능
- Checksum·Count: 빠른 이상 감지, 상세 원인 추가 조회 필요
- Event Log Replay: 변경 이력 필요
- 표본 검사: 저비용이지만 완전성 없음

주기적 증분 비교에 가끔 Full Scan을 조합하면 Cursor 누락을 보완할 수 있습니다.

## 14. 자동 복구와 수동 검토

| 차이 | 자동화 가능성 |
|---|---|
| Local 누락·Source 존재 | 생성 가능 |
| 동일 Key의 필드 차이 | Source of Truth가 명확하면 수정 |
| 중복 사용자 | 병합 판단이 필요해 수동 검토 |
| 양쪽에서 각각 변경 | 충돌 정책 필요 |

Reconciliation이 파괴적인 삭제를 자동 수행할 때는 Dry-run, 승인과 감사 Log를 둡니다.

## 15. 관측 지표
- Idempotency Hit·Conflict·In-progress 수
- Key 처리 시간과 만료 수
- Reconciliation Scan 대상·불일치·자동 복구·수동 대기 수
- 마지막 성공 Cursor와 실행 시각
- 동일 불일치의 반복 발생 수

## 16. 테스트
- 같은 Key의 동시 요청에서 한 번만 처리됩니다.
- 같은 Key·다른 Payload는 충돌합니다.
- Process가 처리 중 죽어도 Lease 이후 복구됩니다.
- Event Ack 실패 후 재전달에도 중복 적용되지 않습니다.
- Reconciliation을 여러 번 실행해도 결과가 안정적입니다.
- Source 삭제·중복·양방향 변경 Conflict를 검증합니다.

---

## 17. 실무 사례 적용 진단과 개선 과제

Outbox와 Event Ledger에는 중복 처리 방지 기반이 있고 일부 외부 연동도 상태를 보존합니다. 다만 모든 Side Effect가 동일한 Idempotency Key와 Request Fingerprint 규칙을 사용하지 않으며, 외부 성공 후 내부 상태 저장 실패 시 중복 호출 가능성을 명시한 코드 경로도 있습니다.

해결하려면 업무 Operation별 멱등성 키의 Source·Scope·TTL을 표준화하고 DB Unique Constraint로 원자성을 보장합니다. 외부 Provider가 멱등 키를 지원하지 않으면 Provider 조회를 통한 Reconciliation 또는 내부 Fencing State를 추가합니다.

완료 기준은 같은 요청을 동시·순차 재전송해도 결과가 하나이고 Payload가 다른 키 재사용은 거부되며, 외부 성공/내부 실패를 주입한 Test에서 자동 또는 수동 Reconciliation으로 수렴하는 상태입니다.

---

# Reference
- [[In-flight Deduplication]]
- [[신뢰성 있는 비동기 처리]]
- [[Transactional Outbox 패턴]]
