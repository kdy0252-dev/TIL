---
id: Logical Clock과 Causal Ordering
started: 2026-05-31
tags:
  - ✅DONE
  - Distributed-System
  - Logical-Clock
group:
  - "[[CS]]"
---
# Logical Clock과 Causal Ordering

## 1. 문제

분산 Node의 Wall Clock은 완전히 일치하지 않습니다. Message A가 B의 원인이어도 Timestamp가 반대로 보일 수 있습니다. Logical Clock은 실제 시간 대신 Event의 선후 관계를 표현합니다.

---

## 2. Happens-before

다음이면 `a -> b`입니다.

- 같은 Process에서 a가 b보다 먼저 발생
- a가 Message 전송이고 b가 수신
- Transitive Relation이 성립

어느 방향도 증명되지 않으면 Concurrent Event입니다.

---

## 3. Lamport Clock

각 Process가 Counter를 유지합니다.

1. Local Event마다 증가
2. Message에 Counter 포함
3. 수신 시 `max(local, received) + 1`

`a -> b`이면 `L(a) < L(b)`지만 반대는 항상 성립하지 않습니다. Counter만으로 Concurrent를 판정할 수 없습니다.

---

## 4. Total Order

Lamport Timestamp와 Node ID를 조합하면 결정적 Total Order를 만들 수 있습니다. 이는 충돌 처리 순서를 정할 뿐 실제 인과 관계나 업무상 올바름을 자동 보장하지 않습니다.

---

## 5. Vector Clock

Node별 Counter Vector를 유지합니다. 모든 요소가 작거나 같고 하나 이상 작으면 선행 관계이며, 서로 크고 작은 요소가 섞이면 Concurrent입니다.

Node 수만큼 Metadata가 늘고 Membership 변경이 어렵다는 비용이 있습니다.

---

## 6. Version Vector

Replica별 버전을 추적해 객체 Version의 인과 관계를 판단합니다. Dynamo 계열 Conflict Detection과 CRDT에서 사용합니다. Concurrent Version을 발견해도 어떻게 Merge할지는 별도 업무 규칙입니다.

---

## 7. Hybrid Logical Clock

물리 시간과 Logical Counter를 결합해 실제 시간에 가까운 정렬과 인과 보존을 함께 추구합니다. Clock Drift Bound와 구현 복잡도를 이해해야 합니다.

Wall Clock Timestamp를 단순 비교하는 LWW보다 안전하지만 모든 Conflict를 없애지는 않습니다.

---

## 8. Event 시스템 적용

- Event에 Aggregate Version을 포함합니다.
- Consumer는 마지막 처리 Version을 기록합니다.
- Gap을 발견하면 재조회 또는 보류합니다.
- 서로 다른 Aggregate Event의 전역 순서를 가정하지 않습니다.
- Partition Key로 필요한 순서 범위를 제한합니다.

Kafka Offset은 Partition 내부 순서이지 전체 업무 인과 관계가 아닙니다.

---

## 9. 사례

예약 생성 뒤 취소 Event가 와야 한다면 같은 Aggregate ID로 순서를 유지하거나 Version을 검사합니다. 알림과 통계처럼 순서 허용 범위가 다른 Consumer는 별도 정책을 가집니다.

Outbox `created_at`만으로 정확한 순서를 증명하지 않습니다.

---

## 10. 완료 기준

- [ ] Wall Clock과 Logical Clock의 목적을 구분합니다.
- [ ] Lamport Clock의 역이 성립하지 않음을 설명합니다.
- [ ] Vector Clock으로 Concurrent Event를 판정합니다.
- [ ] 필요한 순서의 범위를 Aggregate·Partition으로 제한합니다.
- [ ] Gap, Duplicate와 Out-of-order Consumer Test가 있습니다.

# Reference

- [[CRDT]]
- [[신뢰성 있는 비동기 처리]]
- [[CQRS와 Event Sourcing]]
