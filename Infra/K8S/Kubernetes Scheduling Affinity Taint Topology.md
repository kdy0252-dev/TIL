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

### Label로 Worker Node Pool을 분리하는 패턴

하나의 Cluster에서 Platform Component와 환경별 Application을 함께 운영한다면 Node에 역할 Label을 부여해 배치 경계를 만들 수 있다.

```text
workload.example.com/node-role=platform
workload.example.com/node-role=dev
workload.example.com/node-role=qa
workload.example.com/node-role=prod
```

운영 Workload에는 다음과 같은 Hard Constraint를 둔다.

```yaml
spec:
  template:
    spec:
      nodeSelector:
        workload.example.com/node-role: prod
```

이 규칙을 사용하면 개발 환경의 부하나 Platform Component의 Resource 사용이 운영 Application과 같은 Node를 직접 경쟁하는 상황을 줄일 수 있다. 장애 분석과 비용 배분도 Node 역할 단위로 나누기 쉬워진다.

다만 Label은 Scheduler의 선택 조건이지 보안 격리 장치가 아니다. 권한이 있는 사용자가 다른 `nodeSelector`를 선언할 수 있고 일반 Pod도 Label Node에 배치될 수 있다. 전용 Node를 강제하려면 다음 요소를 함께 사용한다.

- Node에는 `dedicated=prod:NoSchedule` 같은 Taint를 설정한다.
- 운영 Workload에만 대응하는 Toleration과 Node Affinity를 부여한다.
- Admission Policy로 허용되지 않은 Node Selector와 Toleration을 차단한다.
- Namespace의 ResourceQuota와 NetworkPolicy로 자원 및 통신 경계를 보완한다.

Node 이름에 직접 Label을 붙이는 방식은 기존 Node를 옮길 때 유용하지만 Node가 교체되면 설정이 사라질 수 있다. Managed Node Group, Karpenter NodePool 또는 Launch Template에서 새 Node가 생성될 때부터 Label과 Taint를 갖도록 선언하는 편이 장기적으로 안전하다.

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

### 운영 Replica를 서로 다른 Worker Node에 강제 분산하기

Replica 2개인 핵심 API를 동일 Node 장애에서 보호하려면 `kubernetes.io/hostname`을 Topology Key로 사용할 수 있다.

```yaml
replicas: 2

template:
  metadata:
    labels:
      app.kubernetes.io/name: core-api
  spec:
    nodeSelector:
      workload.example.com/node-role: prod
    topologySpreadConstraints:
      - maxSkew: 1
        topologyKey: kubernetes.io/hostname
        whenUnsatisfiable: DoNotSchedule
        labelSelector:
          matchLabels:
            app.kubernetes.io/name: core-api
```

Scheduler는 먼저 운영 Label을 가진 Node만 후보로 남긴 뒤 두 Replica의 Node별 개수 차이가 1을 넘지 않도록 배치한다. 운영 Node가 두 개 이상 준비돼 있다면 Replica가 서로 다른 Worker Node에 놓인다.

`DoNotSchedule`은 분산을 지키지 못하면 두 번째 Pod를 Pending으로 남기는 강한 정책이다. 한 Node에 두 Replica를 올려 가용성 착시를 만드는 것보다 낫지만, 운영 Node가 하나만 남은 장애 상황에서는 복구보다 규칙 준수가 우선된다. 장애 중에도 축소된 서비스를 제공해야 한다면 `ScheduleAnyway`와 Preferred Anti-affinity를 검토한다.

Hostname 분산은 Node 장애만 다룬다. 두 Node가 같은 Availability Zone에 있을 수 있으므로 Zone 장애까지 견디려면 `topology.kubernetes.io/zone` Constraint를 추가한다. 이때 최소 Replica 수와 실제 Zone별 Capacity가 규칙을 만족하는지 먼저 계산해야 한다.

Argo Rollouts의 Blue-Green 배포에서는 Stable과 Preview Replica가 동시에 존재한다. Selector가 양쪽 ReplicaSet을 모두 선택하면 전체 Pod 수를 기준으로 분산하고, Version Label까지 선택하면 Version별로 분산한다. 의도와 Selector가 다르면 새 Version이 특정 Node에 몰릴 수 있으므로 Rendered Manifest와 실제 Pod 배치를 함께 검증한다.

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

운영 검증에서는 다음 결과를 확인한다.

```bash
kubectl get nodes --show-labels
kubectl get pods -n <namespace> -o wide
kubectl describe pod -n <namespace> <pod-name>
```

Node Label이 선언과 일치하는지, 운영 Pod가 지정 Node에만 배치됐는지, Replica의 `NODE`와 `ZONE`이 실제로 분산됐는지를 확인한다. 이후 Node 하나를 Drain해 남은 Capacity와 Scheduling 정책이 함께 복구 가능한지도 시험한다.

# Reference
- [Assigning Pods to Nodes](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/)
- [Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)
- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
