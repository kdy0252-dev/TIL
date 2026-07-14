---
id: Kubernetes Workload 신뢰성
started: 2026-07-10
tags:
  - ✅DONE
  - K8S
  - Reliability
group:
  - "[[Infra K8S]]"
---
# Kubernetes Workload 신뢰성

## 1. 개요 (Overview)
Container를 실행하는 것과 안전하게 운영하는 것은 다릅니다. Kubernetes Workload는 Probe, Resource Request, Scheduling, Graceful Shutdown과 Disruption 정책이 함께 설계되어야 합니다.

---

## 2. Probe

| Probe | 목적 |
|---|---|
| Startup | 긴 초기화 동안 Liveness 시작을 지연 |
| Liveness | 복구 불가능한 Process를 재시작 |
| Readiness | 신규 트래픽 수신 가능 여부 |

Liveness에 DB·외부 API 상태를 포함하면 의존성 장애 때 모든 Pod가 재시작될 수 있습니다. Readiness에는 Traffic Capacity를 반영할 수 있습니다.

---

## 3. Resource Request와 Limit
- Request는 Scheduler와 Cluster Autoscaler의 용량 계산 기준입니다.
- CPU Limit은 Throttling을 유발할 수 있습니다.
- Memory Limit 초과는 OOMKill로 이어집니다.
- JVM Heap만이 아니라 Metaspace, Thread Stack, Direct Memory를 포함합니다.

실측 Metric과 부하 테스트로 조정하고 복사한 기본값을 방치하지 않습니다.

---

## 4. Scheduling
Node Selector, Affinity, Taint·Toleration으로 Platform·Dev·QA·Prod Workload를 배치합니다. 너무 엄격한 조건은 적합한 Node가 없어 Pod를 Pending 상태로 만들 수 있습니다.

Topology Spread와 Pod Anti-affinity로 Replica가 같은 Node·AZ에 몰리지 않게 합니다.

---

## 5. Graceful Shutdown

```text
SIGTERM
  -> Readiness DOWN
  -> Endpoint 제거
  -> preStop / Deregistration 대기
  -> In-flight 요청 완료
  -> Process 종료
```

ALB Deregistration Delay, Spring Graceful Shutdown과 `terminationGracePeriodSeconds`를 일관되게 설정합니다.

---

## 6. Disruption
- PodDisruptionBudget은 자발적 중단 시 최소 가용 Replica를 보호합니다.
- Replica 1개에서 `minAvailable: 1`은 Node Drain을 막을 수 있습니다.
- Blue-Green 중 두 ReplicaSet의 Resource 합을 Cluster가 수용해야 합니다.
- Karpenter Consolidation과 Upgrade가 동시에 과도한 Pod를 제거하지 않게 합니다.

---

## 7. 실무 사례 적용 관점
사례의 Helm Chart는 Startup·Liveness·Readiness Probe, Resource, Node Selector, Affinity, 종료 유예와 Lifecycle Hook을 Values로 관리합니다. Argo Rollouts의 `minReadySeconds`와 Progress Deadline이 배포 성공 판단을 보완합니다.

---

## 8. Probe 설계 상세
Probe는 같은 Endpoint를 이름만 바꿔 사용하는 것이 아니라 서로 다른 질문에 답해야 합니다.

### Startup Probe
Liquibase, Cache Warm-up, Spring Context 초기화처럼 시작 시간이 긴 경우 사용합니다. Startup Probe가 성공하기 전에는 Liveness와 Readiness가 실행되지 않습니다.

```text
최대 시작 허용 시간
  = periodSeconds × failureThreshold
```

초기 지연과 실패 횟수를 무작정 크게 두면 실제 시작 실패를 늦게 발견합니다. Cold Start 분포를 측정해 설정합니다.

### Liveness Probe
Deadlock이나 Event Loop 정지처럼 Process 재시작으로 복구 가능한 상태만 포함합니다. DB·Redis·외부 API는 Process 재시작으로 복구되지 않으므로 Liveness에서 제외합니다.

### Readiness Probe
초기화, DB Backpressure, 필수 Local State처럼 현재 Traffic 수용 가능성을 표현합니다. 일시 실패 후 회복하면 Pod는 재시작 없이 Endpoint에 다시 포함됩니다.

## 9. Resource 계산 예시
요청 처리량과 한 요청의 평균 CPU 시간을 알면 필요한 CPU의 시작점을 추정할 수 있습니다.

```text
필요 CPU Core ≈ 초당 요청 수 × 요청당 CPU Seconds
```

Memory는 정상 부하의 Peak뿐 아니라 Deployment 중 Old·New Replica가 공존하는 상황과 Batch Peak를 측정합니다. Request를 너무 낮게 잡으면 Node가 과밀 배치되고, Limit을 너무 낮게 잡으면 CPU Throttling이나 OOMKill이 발생합니다.

## 10. Scheduling과 장애 도메인
Replica가 여러 개여도 한 Node나 Availability Zone에 몰리면 장애 격리가 되지 않습니다.

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: core-app
```

Hard Constraint는 가용 Node가 부족할 때 모든 Pod를 Pending으로 만들 수 있습니다. 가용성 요구와 Cluster 규모에 따라 `DoNotSchedule`과 `ScheduleAnyway`를 선택합니다.

## 11. 종료 Timeline

```text
T0: Pod Termination 시작
T0: preStop Hook 실행
T0~Tn: EndpointSlice·ALB에서 Target 제거 전파
Tn: SIGTERM 전달
Tn~Tend: Spring이 신규 요청 거부, In-flight 완료
Tend: Process 종료
Deadline: SIGKILL
```

preStop에서 고정 Sleep만 사용할 경우 실제 전파 시간과 무관하게 배포가 느려집니다. ALB Deregistration, Endpoint 제거와 Application Graceful Shutdown을 관측해 조정합니다.

## 12. Rollout Capacity
Blue-Green은 Stable과 Preview가 동시에 떠야 하므로 평시보다 최대 두 배의 Resource가 필요할 수 있습니다. Cluster 여유가 없으면 새 Pod가 Pending이 되어 배포가 멈춥니다.

Karpenter Provisioning 시간, Image Pull, Startup Probe를 `progressDeadlineSeconds` 안에 포함해 계산합니다.

## 13. 장애 시나리오
- **CrashLoopBackOff**: Container Log, Exit Code, Liveness, Config·Secret을 확인합니다.
- **OOMKilled**: Heap뿐 아니라 Native Memory와 Limit을 확인합니다.
- **Pending**: Resource 부족, Node Selector, Taint, PVC Zone을 확인합니다.
- **Ready지만 5xx**: Readiness가 실제 업무 준비 상태를 반영하는지 확인합니다.
- **종료 중 요청 실패**: Deregistration Delay와 Graceful Shutdown Timeline을 확인합니다.

## 14. 검증 방법
- Pod를 수동 삭제해 무중단 회복을 확인합니다.
- Node Drain으로 PDB와 Replica 분산을 검증합니다.
- DB Connection을 포화시켜 Readiness 전환을 확인합니다.
- CPU·Memory 부하에서 Throttling과 OOM 여유를 측정합니다.
- Blue-Green 시 Old·New Version의 동시 Resource 사용량을 확인합니다.

---

## 15. 배포 사례 적용 진단과 개선 과제

Rollout Template에는 Probe와 Resource가 있으나 저장소 전수 검색에서 Application `PodDisruptionBudget`, `NetworkPolicy`, `ResourceQuota`, `LimitRange` 선언이 확인되지 않았습니다. 공유 Cluster에서 Node Drain과 환경 간 Resource 경쟁을 견디기에는 부족합니다.

Prod Workload부터 `minAvailable/maxUnavailable`, Topology Spread, PriorityClass를 SLO에 맞게 추가하고 Namespace별 Quota·Default Limit을 둡니다. Default-deny NetworkPolicy 뒤 필요한 Ingress/Egress만 열며 Rollout Preview Replica까지 Capacity 계산에 포함합니다.

완료 기준은 Node Drain·AZ 격리 중 최소 가용 Replica가 유지되고, 한 환경의 부하가 다른 환경 Pod를 축출하지 않으며, 허용되지 않은 Namespace 간 통신이 자동 Test에서 차단되는 상태입니다.

---

# Reference
- [Kubernetes Configure Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [[Argo Rollouts Blue-Green 배포]]
