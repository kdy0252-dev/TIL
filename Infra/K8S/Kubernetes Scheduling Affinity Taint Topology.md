---
id: Kubernetes Scheduling Affinity Taint Topology
started: 2026-07-10
tags:
  - ✅DONE
  - K8S
  - Scheduling
  - Topology
group:
  - "[[Infra K8S]]"
---
# Kubernetes Scheduling Affinity Taint Topology

## 1. Scheduler는 빈 Node를 찾는 도구가 아니다

Scheduler는 Pod의 Request와 제약을 만족하는 Node를 Filter한 뒤 점수가 높은 Node를 선택한다. 배치 규칙은 성능, 비용, 가용성과 격리를 동시에 표현한다. 규칙이 너무 약하면 Replica가 한 장애 도메인에 몰리고, 너무 강하면 Capacity가 있어도 Pod가 Pending이 된다.

## 2. Node Selector와 Node Affinity

`nodeSelector`는 Label이 정확히 일치해야 하는 간단한 Hard Constraint다. Node Affinity는 `In`, `NotIn`, `Exists`와 여러 조건을 표현하고 Required와 Preferred를 나눈다.

```text
requiredDuringScheduling: 만족하지 않으면 배치 불가
preferredDuringScheduling: 가능하면 선호하지만 아니어도 배치
```

운영 Workload 전용 Node처럼 반드시 지킬 격리는 Required가 적합하다. 비용 최적화를 위해 Spot을 선호하는 정도라면 Preferred가 Capacity 부족 시 탈출구를 남긴다.

## 3. Taint와 Toleration

Taint는 Node가 Pod를 밀어내고, Toleration은 특정 Taint를 견딜 수 있다고 표시한다. Toleration만 있다고 그 Node에 반드시 배치되는 것은 아니다. 전용 Node를 만들려면 Taint로 일반 Pod를 막고 Affinity로 대상 Pod를 끌어오는 두 방향이 필요하다.

| Effect | 동작 |
|---|---|
| NoSchedule | 새 Pod 배치를 막음 |
| PreferNoSchedule | 가능하면 피함 |
| NoExecute | 기존 Pod도 조건에 따라 축출 |

`NoExecute`의 `tolerationSeconds`는 Node NotReady 상황에서 Pod가 얼마나 기다릴지 결정한다.

## 4. Pod Affinity와 Anti-affinity

Pod Affinity는 Cache와 Consumer처럼 가까이 둘 Workload를, Anti-affinity는 Replica를 서로 다른 Node나 Zone에 흩을 때 사용한다. Required Anti-affinity는 작은 Cluster나 장애 상황에서 교착을 만들 수 있고 큰 Cluster에서는 Scheduling 비용도 커질 수 있다.

단순한 Replica 분산에는 Topology Spread Constraints가 의도를 더 직접적으로 표현한다.

## 5. Topology Spread Constraints

```yaml
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: api
```

`maxSkew`는 Topology Domain 간 Pod 수 차이를 제한한다. Zone과 Hostname 두 수준을 함께 두면 AZ와 Node 양쪽 분산을 표현할 수 있다. Label Selector가 Rollout의 Stable·Preview Replica를 어떻게 묶는지 확인해야 한다.

## 6. Storage와 Zone

EBS Volume은 Availability Zone에 속한다. PVC가 특정 Zone Volume에 Binding되면 Pod도 그 Zone에 배치되어야 한다. `WaitForFirstConsumer` StorageClass는 Pod Scheduling을 고려한 뒤 Volume을 Provision해 초기 Zone 불일치를 줄인다.

Multi-AZ 분산 규칙과 Single-AZ PVC를 동시에 요구하면 Scheduler가 해결할 수 없는 제약이 될 수 있다.

## 7. Karpenter와의 상호작용

Pod가 기존 Node에 맞지 않으면 Karpenter는 Pod Requirement를 만족하는 새 Node 후보를 찾는다. Instance Type, Zone, Architecture와 Capacity Type 제약을 과도하게 좁히면 Cloud에 Capacity가 있어도 Provisioning이 실패한다.

Spot 중단과 Consolidation 때도 PDB, Topology Spread와 Taint가 재배치 가능성을 결정한다. Scheduler 규칙은 평시 배치뿐 아니라 Node 교체 가능성까지 포함한다.

## 8. Pending Pod를 진단하는 순서

Scheduler Event의 `FailedScheduling` 이유에서 시작한다. CPU·Memory 부족, 일치하지 않는 Affinity, 처리되지 않은 Taint, Volume Zone Conflict와 Topology Constraint를 각각 분리한다. 여러 이유가 동시에 있을 수 있다.

규칙을 하나 제거해 “일단 뜨게” 만들기 전에 그 규칙이 보호하던 가용성 또는 격리 목적을 확인한다.

## 9. 실무에서 빠지기 쉬운 설계

Node Selector와 Affinity가 Values에 있어도 Replica의 AZ 분산과 PVC Zone, Karpenter가 만들 수 있는 Node 조건을 하나의 제약 Graph로 보지 않으면 배포 중 Pending이 발생한다. Blue-Green은 두 ReplicaSet이 동시에 이 Graph를 만족해야 한다.

Hard Constraint는 반드시 필요한 규칙에만 사용하고 가용성 선호는 Preferred나 `ScheduleAnyway`로 표현한다. Node Drain과 AZ Capacity 부족을 재현해 제약이 장애 중에도 해를 갖는지 확인한다.

## 10. 기억할 점

Scheduling 설계는 Pod가 “어디에 있어야 하는가”뿐 아니라 장애 후 “어디로 이동할 수 있는가”를 정의한다. 좋은 규칙은 평시 균형과 장애 시 탈출구를 함께 가진다.

# Reference
- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
