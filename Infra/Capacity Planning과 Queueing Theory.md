---
id: Capacity Planning과 Queueing Theory
started: 2026-06-04
tags:
  - ✅DONE
  - Performance
  - Capacity-Planning
group:
  - "[[Infra]]"
---
# Capacity Planning과 Queueing Theory

## 1. Capacity Planning

Capacity Planning은 평균 사용량에 맞춰 Server 수를 고르는 일이 아니라 Peak, 성장, 장애 Headroom과 비용을 함께 모델링하는 일입니다.

---

## 2. Little's Law

안정된 시스템에서 다음 관계가 성립합니다.

```text
L = λ × W
동시 처리 수 = 도착률 × 평균 체류 시간
```

초당 100요청이 평균 0.2초 머물면 평균 동시 요청은 20입니다. 평균만으로 P99와 Burst를 설명할 수는 없습니다.

---

## 3. Utilization과 Queue

이용률이 100%에 가까워질수록 작은 변동도 Queue를 크게 만듭니다. CPU가 70%라는 숫자보다 도착·처리 시간의 변동, 병렬 Server 수와 Queue 정책을 함께 봅니다.

항상 100% 활용을 목표로 하면 장애 Headroom이 없습니다.

---

## 4. Bottleneck Law

End-to-End Capacity는 가장 작은 자원의 처리량으로 제한됩니다.

```text
HTTP Thread/Virtual Thread
  -> DB Pool
  -> DB CPU·Lock
  -> Redis
  -> 외부 API Rate Limit
```

Pod만 늘리면 DB Connection과 NAT Port를 먼저 고갈시킬 수 있습니다.

---

## 5. Workload Model

- 평상시 RPS와 시간대별 Peak
- 읽기·쓰기·업무 Journey 비율
- Payload와 데이터 크기
- Burst 지속 시간
- Tenant별 편향
- Retry와 Background Job

k6 Scenario는 이 모델에서 도출해야 합니다.

---

## 6. Headroom

Headroom은 성장뿐 아니라 Node·AZ 장애, Blue-Green 이중 Replica, Batch와 Traffic Failover를 흡수합니다.

```text
Required Capacity
  = Peak Demand × Growth × Failure Factor × Safety Margin
```

각 Factor의 근거와 Review 주기를 기록합니다.

---

## 7. Scaling 지연

HPA Metric Window, Pod Startup, Karpenter Node Provision, JVM Warm-up의 합보다 Burst가 짧으면 자동 확장이 늦습니다. 최소 Replica와 Pre-warming이 필요할 수 있습니다.

---

## 8. Queue Capacity

Queue는 일시 Burst를 흡수하지만 장애를 숨길 수 있습니다. Length뿐 아니라 Oldest Age, Arrival·Service Rate와 Drop을 봅니다. 무한 Queue보다 한도와 Load Shedding이 안전합니다.

---

## 9. 예측과 검증

Metric으로 성장 추세를 예측하고 k6 Load·Stress·Spike, Chaos Failure Scenario로 검증합니다. 예측값과 실제 결과 차이를 모델에 다시 반영합니다.

---

## 10. 완료 기준

- [ ] Critical Resource별 처리량과 Saturation 지표가 있습니다.
- [ ] Peak·성장·장애·배포 Headroom을 포함합니다.
- [ ] Scaling 지연보다 짧은 Burst 대응이 정의됩니다.
- [ ] Queue Age와 Drop 정책이 있습니다.
- [ ] 분기별 예측과 실제 사용량 오차를 Review합니다.

# Reference

- [[k6 부하 테스트와 성능 검증]]
- [[Backpressure와 Load Shedding]]
- [[Karpenter Node 자동 확장]]
