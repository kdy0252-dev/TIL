---
id: Consistent Hashing과 데이터 재배치
started: 2026-05-30
tags:
  - ✅DONE
  - Distributed-System
  - Consistent-Hashing
group:
  - "[[CS]]"
---
# Consistent Hashing과 데이터 재배치

## 1. 문제

`hash(key) % nodeCount`는 Node 수가 바뀌면 대부분의 Key가 다른 Node로 이동합니다. Cache가 동시에 Miss하거나 Shard Migration이 폭증합니다.

Consistent Hashing은 Node 변경 때 인접 범위의 Key만 재배치합니다.

---

## 2. Hash Ring

Key와 Node를 같은 Hash 공간에 놓고 시계 방향의 첫 Node가 Key를 소유합니다.

```text
Node 추가 -> 앞 Node의 일부 범위만 이동
Node 제거 -> 다음 Node가 범위를 인수
```

이론적으로 이동량은 전체 Key 중 대략 `1/N` 수준입니다.

---

## 3. Virtual Node

Physical Node 하나를 Ring의 여러 지점에 배치합니다. Key 분포를 균등화하고 Node 용량에 따라 Virtual Node 수를 조절할 수 있습니다.

Virtual Node가 너무 많으면 Membership과 Routing Metadata, 이동 계획이 커집니다.

---

## 4. Replication

첫 Node뿐 아니라 다음 N개 Node에 Replica를 둡니다. 서로 다른 AZ·Rack에 배치되도록 Failure Domain을 인식해야 합니다. Ring에서 단순히 이웃이라고 물리 장애가 독립적인 것은 아닙니다.

---

## 5. Hot Key

분포가 균등해도 Traffic은 균등하지 않을 수 있습니다. 유명 Key 하나가 Node를 포화시킬 수 있습니다.

- Local Cache와 Request Coalescing
- Hot Key Replication
- Key Split
- Rate Limit
- Read Replica

Consistent Hashing은 Hot Key 해결책이 아닙니다.

---

## 6. Rendezvous Hashing

각 Key와 Node 조합의 점수를 계산해 가장 높은 Node를 선택합니다. Ring과 Virtual Node 없이도 비교적 균등하고 구현이 단순하지만 후보 Node 전체 계산 비용을 고려합니다.

---

## 7. 사례 적용

- 분산 Cache Key Routing
- Tenant를 Worker Partition에 배치
- WebSocket Session의 Sticky Routing
- Sharded Storage와 Consumer Assignment

영속 DB Sharding은 Rebalance, Transaction, Foreign Key, Backup까지 포함하므로 Hash 함수만으로 완성되지 않습니다.

---

## 8. Rebalance

이동 중 Old·New Owner가 동시에 존재합니다. Read fallback, Dual-write, Version과 Cutover 순서를 설계합니다. 대량 이동이 업무 Traffic을 압박하지 않도록 Rate Limit과 진행 Checkpoint를 둡니다.

---

## 9. Test와 지표

- Key 수 대비 Node별 분포와 표준 편차
- Node 추가·제거 시 이동 Key 비율
- Hot Key 상위 Traffic
- Rebalance 처리량과 업무 P99
- 장애 시 Replica 승격과 누락

---

## 10. 완료 기준

- [ ] Modulo Hash와 재배치량 차이를 설명합니다.
- [ ] Virtual Node와 가중치 Trade-off를 이해합니다.
- [ ] Failure Domain 기반 Replica 배치를 검증합니다.
- [ ] Rebalance 중 Read·Write 정합성 Test가 있습니다.
- [ ] Hot Key를 별도 지표로 감지합니다.

# Reference

- [[DB Sharding 전략]]
- [[In-flight Deduplication]]
