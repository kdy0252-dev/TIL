---
id: Karpenter Node 자동 확장
started: 2026-07-05
tags:
  - ✅DONE
  - K8S
  - EKS
  - Autoscaling
group:
  - "[[Infra K8S]]"
---
# Karpenter를 이용한 EKS Node 자동 확장

## 1. 개요 (Overview)
**Karpenter**는 Pending Pod의 실제 Resource·Scheduling 요구를 보고 적합한 EC2 Instance를 직접 생성하는 Kubernetes Node Lifecycle Controller입니다. 고정 Auto Scaling Group 중심의 Cluster Autoscaler보다 Instance Type 선택과 Provisioning이 유연합니다.

---

## 2. 핵심 Resource

| Resource | 역할 |
|---|---|
| NodePool | Scheduling 요구, 용량 유형, 한도와 Disruption 정책 |
| EC2NodeClass | AMI, Subnet, Security Group, IAM, Storage 설정 |
| NodeClaim | 실제 생성되는 개별 Node 요청 |

```yaml
spec:
  template:
    spec:
      requirements:
        - key: karpenter.sh/capacity-type
          operator: In
          values: ["on-demand"]
  limits:
    cpu: 1000
```

---

## 3. Provisioning 흐름

```text
Pending Pod
  -> Scheduler가 배치 실패
  -> Karpenter가 요구사항 분석
  -> Instance Type·AZ 선택
  -> EC2 Node 생성
  -> Pod Scheduling
```

Pod의 Resource Request가 부정확하면 Karpenter의 선택도 부정확해집니다.

---

## 4. Consolidation과 Disruption
사용률이 낮은 Node를 더 작은 Node로 교체하거나 제거하여 비용을 줄일 수 있습니다. 하지만 Stateful Pod, 긴 작업, PDB가 없는 서비스는 중단될 수 있습니다.

- PodDisruptionBudget
- `terminationGracePeriodSeconds`
- `do-not-disrupt` 정책이 필요한 작업
- Spot Interruption 처리
- Node 만료와 AMI 교체

를 함께 설계합니다.

---

## 5. 실무 사례 적용 관점
이 사례는 Platform 공유 Node와 환경별 업무 Node를 Label·Node Selector로 구분합니다. Karpenter NodePool은 Architecture, OS, Capacity Type, Instance Category와 Generation을 제한합니다.

Production과 Dev가 하나의 Cluster를 공유한다면 환경별 NodePool·Limit·Priority를 분리하여 개발 부하가 Production Capacity를 잠식하지 않게 해야 합니다.

---

## 6. Scheduling 요구 분석
Karpenter는 단순 CPU 합계뿐 아니라 다음 제약의 교집합을 계산합니다.

- CPU·Memory·Ephemeral Storage Request
- Node Selector와 Node Affinity
- Architecture와 OS
- Availability Zone과 Volume Topology
- Taint·Toleration
- Pod Topology Spread
- Instance Type·Generation·Capacity Type 제한

서로 모순되는 조건은 어떤 EC2 Instance로도 해결할 수 없습니다. Pending Pod Event에서 `incompatible requirements` 원인을 확인합니다.

## 7. EC2NodeClass

```yaml
apiVersion: karpenter.k8s.aws/v1
kind: EC2NodeClass
spec:
  amiSelectorTerms:
    - alias: al2023@latest
  subnetSelectorTerms:
    - tags:
        karpenter.sh/discovery: production-cluster
  securityGroupSelectorTerms:
    - tags:
        karpenter.sh/discovery: production-cluster
```

AMI를 `latest`로 두면 Node 교체 시점에 예기치 않은 Version이 들어올 수 있습니다. 운영 환경은 검증된 Alias·ID를 고정하고 정기 Upgrade 절차를 두는 것이 안전합니다.

## 8. On-demand와 Spot

| 용량 | 장점 | 위험 |
|---|---|---|
| On-demand | 안정적인 공급과 중단 없음 | 비용 높음 |
| Spot | 큰 비용 절감 | 2분 전 중단, 용량 부족 |

Stateless Replica, 재시도 가능한 Worker는 Spot 후보입니다. 단일 Replica, 긴 Migration, Stateful Platform은 On-demand를 우선합니다. 여러 Instance Family와 AZ를 허용해야 Spot 가용성이 높아집니다.

## 9. Consolidation 동작
Karpenter는 비어 있거나 비효율적인 Node를 삭제·교체할 수 있습니다.

```text
Node A + Node B의 Pod
  -> 더 작은 Node C에 배치 가능
  -> C 생성 및 Ready
  -> Pod Eviction
  -> A, B 종료
```

PDB, `do-not-disrupt`, DaemonSet Overhead와 Local Storage가 Consolidation 가능 여부에 영향을 줍니다.

## 10. NodePool 분리 전략
사례의 Shared Cluster에서는 다음처럼 목적별 NodePool을 고려할 수 있습니다.

- Platform: Argo CD, Observability, Istio Control Plane
- Production Online: 높은 가용성, On-demand
- Batch·Migration: 별도 Limit과 Taint
- Dev·QA: 비용 최적화, 낮은 Priority

Node Label만으로는 Resource 상한이 생기지 않습니다. NodePool `limits`, ResourceQuota, PriorityClass를 함께 사용합니다.

## 11. Scale-up 지연
Pending Pod가 생긴 뒤 Node Ready까지 다음 시간이 필요합니다.

```text
Provision 판단
  + EC2 Launch
  + Bootstrap
  + CNI Ready
  + Image Pull
  + Application Startup
```

급격한 Traffic Spike는 Node 확장보다 빠를 수 있습니다. HPA, 여유 Capacity, 작은 Base Image와 Overprovisioning을 필요에 따라 조합합니다.

## 12. 장애와 진단
- NodeClaim 생성 안 됨: Controller 권한과 Pending Pod 제약 확인
- EC2 생성 실패: Quota, Subnet IP, Instance Capacity, IAM 확인
- Node는 생성됐지만 NotReady: AMI, User Data, CNI, Security Group 확인
- Consolidation 안 됨: PDB, Annotation, Local Storage, Pod Affinity 확인
- 비용 급증: Request 과대 설정, NodePool 제한, Consolidation 정책 확인

## 13. 관측 지표와 검증
- Pending Pod 시간
- Node Provisioning 시간
- Node Utilization과 낭비 Resource
- NodeClaim 실패 사유
- Consolidation·Interruption 횟수
- Spot 중단 후 서비스 오류율

부하 테스트에서 Pod 증가부터 Node Ready, Application Ready까지의 전체 시간을 측정합니다.

---

## 14. 배포 사례 적용 진단과 개선 과제

Karpenter가 수요 기반 Node Provisioning을 담당하지만 PDB와 Topology 규칙이 부족하면 Consolidation이 가용성을 해칠 수 있습니다. 공유 Cluster에서 환경별 우선순위와 Platform Node 격리도 비용 최적화보다 먼저 보장돼야 합니다.

Prod, Non-prod, Platform NodePool을 Taint·Requirement로 분리하고 Spot은 중단 허용 Workload부터 적용합니다. Provisioning Latency, Pending Pod, Interruption, Consolidation Disruption과 Subnet IP를 함께 감시하며 최소 Headroom을 둡니다.

완료 기준은 Spot 중단·Node 교체 Test에서 PDB와 SLO가 유지되고, Platform Component가 업무 Burst에 축출되지 않으며, 비용 절감 전후의 가용성·대기 시간 변화가 수치로 비교되는 상태입니다.

---

# Reference
- [Karpenter Documentation](https://karpenter.sh/docs/)
- [Karpenter Concepts](https://karpenter.sh/docs/concepts/)
- [[EKS Cluster Add-on 아키텍처]]
- [[Kubernetes Workload 신뢰성]]
