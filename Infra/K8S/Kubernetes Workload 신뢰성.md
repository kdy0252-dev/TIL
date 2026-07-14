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

## 7. Helm Values로 운영 정책 분리하기

Helm Chart Template은 Probe, Resource, Node Selector, Affinity, Topology Spread, 종료 유예와 Lifecycle Hook을 공통 구조로 제공하고 환경별 Values가 실제 정책을 결정하도록 만들 수 있습니다. Argo Rollouts의 `minReadySeconds`와 Progress Deadline은 새 Replica가 충분히 안정된 뒤 배포 성공으로 판단하도록 보완합니다.

운영 Values에서 `node-role: prod` Selector를 선언하면 운영 Pod를 지정 Worker Node Pool에 한정할 수 있습니다. Replica가 2개 이상인 핵심 Workload에는 Hostname Topology Spread를 추가해 동일 Node 장애에 함께 영향받지 않도록 합니다. Node 역할 격리와 Pod 분산은 목적이 다르므로 둘 중 하나로 다른 하나를 대체할 수 없습니다.

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

## 15. 적용된 구성에서 한 단계 더 검토할 부분

운영 Node Label과 Hard Node Selector는 환경별 배치 경계를 만들고, 핵심 API의 Hostname Topology Spread는 Replica를 서로 다른 Worker Node에 분산합니다. Workload별 Request와 Limit도 역할에 맞게 구분돼 Scheduler의 용량 판단과 Resource 상한을 제공합니다.

이 구성이 보장하는 범위를 정확히 이해해야 합니다.

- Hostname 분산은 Node 장애를 줄이지만 Availability Zone 장애까지 자동으로 보호하지 않습니다.
- Replica 1개인 Gateway, BFF, Batch·Metrics Workload는 분산 규칙을 추가해도 고가용성이 생기지 않습니다.
- Node Label과 Selector만으로는 일반 Pod가 운영 Node에 들어오는 것을 차단하지 못합니다.
- Request와 Limit은 정적 초기값이므로 실제 사용량과 부하 테스트로 지속해서 교정해야 합니다.
- Blue-Green 중에는 Stable·Preview Replica가 함께 존재해 평시보다 큰 Capacity가 필요합니다.

SLO가 요구하는 Workload부터 최소 Replica를 2개 이상으로 조정하고 Zone과 Hostname 두 수준의 Topology Spread를 검토합니다. 운영 전용 Node에는 Taint·Toleration을 결합하고 Application PDB, Namespace별 ResourceQuota·LimitRange와 Default-deny NetworkPolicy로 경계를 보완합니다.

완료 여부는 Manifest 존재가 아니라 실험으로 판단합니다. Node Drain과 AZ 격리 중 최소 가용 Replica가 유지되고, 운영 Pod가 허용된 Node에만 배치되며, Peak와 Blue-Green 배포 중에도 Pod가 Resource 부족으로 Pending되지 않아야 합니다.

---

# Reference
- [Kubernetes Configure Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [Kubernetes Resource Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
- [Pod Disruptions](https://kubernetes.io/docs/concepts/workloads/pods/disruptions/)
- [[Argo Rollouts Blue-Green 배포]]
