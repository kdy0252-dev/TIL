---
id: Quorum Read Repair와 Anti-Entropy
started: 2026-06-01
tags:
  - ✅DONE
  - Distributed-System
  - Quorum
group:
  - "[[CS]]"
---
# Quorum, Read Repair와 Anti-Entropy

## 1. 복제의 질문

Replica N개 중 몇 곳에 쓰고 몇 곳에서 읽어야 하는가를 `N`, `W`, `R`로 표현합니다.

```text
N = Replica 수
W = Write 성공에 필요한 수
R = Read 응답에 필요한 수
```

`W + R > N`이면 Read·Write 집합이 적어도 하나 겹치지만 이것만으로 Linearizability가 자동 보장되지는 않습니다.

---

## 2. Sloppy Quorum

장애 Node 대신 다른 Node에 임시 쓰기를 허용하면 가용성이 높아지지만 원래 Replica 집합과 교집합 보장이 약해집니다. Hinted Handoff로 나중에 전달합니다.

Quorum이라는 이름만 보고 강한 일관성을 단정하지 않습니다.

---

## 3. Conflict 판정

Timestamp LWW, Version Vector, Logical Clock, Application Merge를 사용할 수 있습니다. LWW는 단순하지만 Clock Drift로 정상 쓰기를 잃을 수 있습니다.

업무상 동시에 유효한 Version을 어떻게 합칠지 별도 정책이 필요합니다.

---

## 4. Read Repair

Read 시 여러 Replica Version을 비교하고 최신 값을 반환하면서 뒤처진 Replica를 갱신합니다.

장점은 자주 읽는 Key가 자연히 복구된다는 것이고, 단점은 Read Latency와 부하가 증가하며 읽지 않는 Key는 복구되지 않는다는 것입니다.

---

## 5. Anti-Entropy

Background에서 Replica의 데이터 요약을 비교해 차이를 복구합니다. Merkle Tree는 큰 데이터 집합을 Hash 계층으로 비교해 다른 범위를 좁힙니다.

Repair Traffic이 업무 I/O를 압박하지 않도록 Rate와 Window를 관리합니다.

---

## 6. Tombstone

삭제를 물리 제거하면 오래된 Replica의 값이 다시 살아날 수 있습니다. Tombstone을 충분히 전파한 뒤 제거해야 합니다. Repair보다 Tombstone 보존이 짧으면 Zombie Data가 생깁니다.

---

## 7. 일관성 수준 선택

- 사용자 프로필 조회: Stale 허용 가능
- 좌석·재고 확정: 조건부 쓰기나 단일 권위 필요
- 통계 집계: 최종 일관성과 Freshness SLO
- 인증·권한: 보수적인 일관성

전체 시스템에 하나의 Consistency를 적용하지 않습니다.

---

## 8. 장애 시나리오

Network Partition 중 양쪽 쓰기, Replica 장기 중단, Clock Drift, Tombstone GC, Repair 중 Node 재시작을 Test합니다. 가용성뿐 아니라 복구 뒤 Version 수렴과 유실을 봅니다.

---

## 9. 관측 지표

- Replica Lag와 Version 불일치
- Read Repair 수·Latency
- Hinted Handoff 적체
- Anti-entropy 진행률과 Bytes
- Tombstone 수와 GC 지연
- Conflict 발생·해결 방식

---

## 10. 완료 기준

- [ ] `W + R > N`의 보장과 한계를 설명합니다.
- [ ] Sloppy Quorum의 가용성 Trade-off를 이해합니다.
- [ ] Read Repair와 Background Repair 역할을 구분합니다.
- [ ] Tombstone 삭제 후 데이터 부활을 Test합니다.
- [ ] 업무별 허용 Staleness와 Conflict 정책이 있습니다.

# Reference

- [[Logical Clock과 Causal Ordering]]
- [[CRDT]]
- [[멱등성과 Reconciliation]]
