---
id: ResourceQuota LimitRange PriorityClass
started: 2026-07-12
tags:
  - ✅DONE
  - K8S
  - Resource
  - Scheduling
group:
  - "[[Infra K8S]]"
---
# ResourceQuota LimitRange PriorityClass

## 1. 공유 Cluster의 자원은 공공재다

한 Namespace의 잘못된 Deployment가 Replica 수를 수백 개로 늘리거나 Request 없는 Pod를 대량 배치하면 다른 Workload가 Pending 또는 OOM 상태가 될 수 있다. ResourceQuota, LimitRange와 PriorityClass는 각각 총량, 개별 기본값, 부족할 때의 우선순위를 다룬다.

```text
LimitRange   : Pod/Container 하나의 최소·최대·기본값
ResourceQuota: Namespace 전체 소비 한도
PriorityClass: 경합 시 어떤 Pod를 먼저 배치·유지할지
```

## 2. Resource Request가 중요한 이유

Scheduler는 실제 사용량이 아니라 Request를 기준으로 Node를 선택한다. Request가 너무 낮으면 Node에 많은 Pod가 몰리고 실제 부하 때 Memory Pressure와 CPU 경합이 발생한다. 너무 높으면 사용하지 않는 Capacity가 예약되어 Pending과 비용 증가로 이어진다.

Limit은 안전망이지만 CPU Limit 초과는 Throttling, Memory Limit 초과는 OOMKill이라는 서로 다른 결과를 만든다. 같은 비율을 기계적으로 적용하지 않는다.

## 3. LimitRange

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: container-defaults
spec:
  limits:
    - type: Container
      defaultRequest:
        cpu: 100m
        memory: 256Mi
      default:
        memory: 512Mi
```

기본값은 Request를 빼먹은 Workload가 무제한이 되는 것을 막지만, 모든 서비스에 적합한 성능값은 아니다. 작은 기본값이 조용히 주입되면 개발자는 설정 사실을 모르고 Throttling이나 OOM을 겪을 수 있다. Admission 결과와 문서에서 기본값을 드러낸다.

## 4. ResourceQuota

Quota는 CPU·Memory뿐 아니라 Pod, Service, LoadBalancer, PVC와 특정 PriorityClass의 총량도 제한할 수 있다. 환경별 예산과 최대 Burst를 반영하되 Blue-Green 배포 중 Stable과 Preview가 동시에 존재하는 용량을 포함해야 한다.

Quota가 정확히 평시 사용량이면 새 Version을 띄울 여유가 없어 배포가 멈춘다. 장애 대응용 임시 Pod와 Job의 여유도 고려한다.

## 5. PriorityClass와 Preemption

Priority가 높은 Pending Pod를 배치하기 위해 Scheduler가 낮은 Priority Pod를 축출할 수 있다. 이는 CPU 시간을 더 주는 기능이 아니라 Scheduling 순서를 바꾸는 기능이다.

모든 팀이 자기 서비스를 최고 Priority로 선언하면 의미가 사라진다. PriorityClass는 Cluster 범위 Resource이므로 플랫폼이 생성하고 사용 권한을 통제한다.

```text
system-critical > customer-serving > asynchronous-job > best-effort
```

Preemption은 즉시 자리를 만들지 못할 수 있다. 낮은 Priority Pod의 종료 유예와 PDB, 새 Pod의 Scheduling 조건이 함께 작용한다.

## 6. Quota와 Autoscaler의 상호작용

HPA가 Replica를 늘리려 해도 Namespace Pod 또는 CPU Quota를 넘으면 새 Pod가 생성되지 않는다. Karpenter가 Node를 늘릴 수 있어도 Quota는 Namespace 정책이므로 해결되지 않는다. 반대로 Quota가 넓고 Request가 부정확하면 Autoscaler는 잘못된 Capacity 신호를 받는다.

Metric에는 HPA Desired Replica, Quota 사용률, Unschedulable Pod와 Node Provisioning을 함께 본다.

## 7. 실무에서 빠지기 쉬운 설계

여러 환경이 한 Cluster를 공유하면서 Quota와 LimitRange가 없다면 부하 테스트나 Batch가 운영 Workload의 Scheduling을 방해할 수 있다. PriorityClass만 추가해도 Resource 총량이 통제되지 않으면 낮은 Priority Workload가 반복 축출되는 기아 상태가 생긴다.

Namespace의 업무 중요도와 비용 예산으로 Quota를 잡고, 관측 데이터로 Container 기본 Request를 정한다. Priority는 소수 계층으로 제한하며 Blue-Green과 장애 Burst를 실제 배포 Test에 포함한다.

## 8. 기억할 점

Resource Governance는 “많이 못 쓰게 막기”가 아니다. 공유 Capacity가 부족할 때 예측 가능한 방식으로 배분하고, 한 팀의 실수가 다른 팀의 장애가 되지 않게 만드는 계약이다.

# Reference
- [Resource Quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [Limit Ranges](https://kubernetes.io/docs/concepts/policy/limit-range/)
- [Pod Priority and Preemption](https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/)
