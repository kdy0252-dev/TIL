---
id: KEDA Event-driven Autoscaling
started: 2026-07-04
tags:
  - ✅DONE
  - K8S
  - KEDA
group:
  - "[[Infra K8S]]"
---
# KEDA Event-driven Autoscaling

## 1. 개요

KEDA는 Queue Length, Consumer Lag, Schedule과 외부 Metric을 Kubernetes HPA로 연결합니다. CPU보다 업무 적체가 처리 수요를 잘 나타내는 Worker에 적합합니다.

---

## 2. 구성 요소

- `ScaledObject`: Deployment와 Trigger 연결
- `ScaledJob`: 적체량에 따라 Job 생성
- Scaler: Kafka, Prometheus, Redis 등 Metric 수집
- Metrics Adapter: HPA가 사용할 External Metric 제공

---

## 3. Queue 기반 계산

```text
필요 Replica ≈ Queue Length / Replica당 목표 적체량
```

메시지 처리 시간, 유입률과 Oldest Age를 함께 봅니다. Length가 짧아도 오래된 Poison Message가 있을 수 있습니다.

---

## 4. Scale to Zero

유휴 비용을 줄이지만 첫 Pod Startup만큼 처리 지연이 생깁니다. 즉시 처리가 필요한 Queue는 `minReplicaCount`를 유지합니다.

DB Migration이나 Leader Job처럼 동시에 여러 Replica가 실행되면 안 되는 Workload에는 별도 조정이 필요합니다.

---

## 5. Activation과 Hysteresis

작은 Queue 변화로 0↔1 또는 Replica 수가 계속 흔들리지 않게 Activation Threshold, Polling Interval, Cooldown과 HPA Stabilization을 조절합니다.

---

## 6. 처리량 한계

Worker를 늘려도 DB Connection, External API Rate Limit과 Partition 수를 넘을 수 없습니다. `maxReplicaCount`를 Downstream Capacity Budget으로 제한합니다.

Kafka Consumer는 Partition 수보다 많은 Replica가 유휴일 수 있습니다.

---

## 7. 실패와 Retry

KEDA는 처리 성공을 보장하지 않습니다. Visibility Timeout, Ack, Retry, DLQ와 Idempotency는 Consumer 책임입니다. 실패 Message가 Queue Length를 유지해 무한 Scale-out을 만들지 않게 합니다.

---

## 8. 인증

`TriggerAuthentication`과 `ClusterTriggerAuthentication`으로 Credential을 분리합니다. 가능하면 Workload Identity를 사용하고 Secret 값을 ScaledObject에 직접 넣지 않습니다.

---

## 9. 사례 적용

Outbox Oldest Age와 Pending 수, 통계 Batch Chunk를 Prometheus Scaler로 연결할 수 있습니다. Polling Worker 자체 처리율과 DB Budget을 측정한 뒤 적용합니다.

---

## 10. ScaledObject 예시

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: outbox-worker
spec:
  scaleTargetRef:
    name: outbox-worker
  minReplicaCount: 1
  maxReplicaCount: 8
  cooldownPeriod: 120
  triggers:
    - type: prometheus
      metadata:
        serverAddress: http://prometheus.monitoring.svc:9090
        metricName: outbox_oldest_age_seconds
        threshold: "30"
        query: max(outbox_oldest_age_seconds{service="worker"})
```

실제 Query가 반환하지 못할 때의 Fallback과 인증을 함께 설정합니다.

---

## 11. 장애 양상

- Prometheus 장애로 Metric을 읽지 못함
- Oldest Age가 해소되지 않아 Max Replica에 고정
- Scale-out이 DB Connection Storm을 유발
- Scale-in 중 처리 중 Message가 중단
- Cooldown이 짧아 Replica가 계속 흔들림
- Kafka Rebalance 시간이 처리 시간보다 길어짐

KEDA Operator와 Metrics Adapter 자체의 가용성도 감시합니다.

---

## 12. 실습

일정 속도로 Queue를 채우고 처리율, Replica, Oldest Age와 DB Pool을 관찰합니다. Provider 장애로 처리율을 낮춘 뒤 Max Replica와 Load Shedding이 Downstream을 보호하는지 확인합니다. 복구 뒤 Queue가 목표 시간 안에 Drain되는지도 측정합니다.

---

## 13. 완료 기준

- [ ] CPU보다 Queue Metric이 적절한 이유가 있습니다.
- [ ] 처리율·유입률·Oldest Age를 함께 봅니다.
- [ ] Scale-to-zero Cold Start가 SLO를 만족합니다.
- [ ] Max Replica가 Downstream 한도를 넘지 않습니다.
- [ ] Poison Message와 Metric 실패 시 동작을 Test합니다.

# Reference

- [KEDA Documentation](https://keda.sh/docs/)
- [[신뢰성 있는 비동기 처리]]
- [[Capacity Planning과 Queueing Theory]]
