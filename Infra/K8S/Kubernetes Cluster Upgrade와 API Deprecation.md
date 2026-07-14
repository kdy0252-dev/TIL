---
id: Kubernetes Cluster Upgrade와 API Deprecation
started: 2026-07-06
tags:
  - ✅DONE
  - K8S
  - Upgrade
  - API-Deprecation
group:
  - "[[Infra K8S]]"
---
# Kubernetes Cluster Upgrade와 API Deprecation

## 1. Cluster Upgrade는 Control Plane Version 변경이 아니다

Kubernetes는 API Server, etcd, Node의 kubelet, CNI, CSI, DNS, Ingress·Gateway Controller와 여러 CRD Controller가 협력하는 플랫폼이다. EKS Control Plane Version만 올리고 끝내면 Add-on과 Client의 호환성 문제가 나중에 드러난다.

```text
Manifest/API 조사
 -> Controller·Add-on 호환성 확인
 -> Control Plane
 -> Managed Add-on
 -> Node Group
 -> Workload 검증
```

## 2. Version Skew

Control Plane과 kubelet, kube-proxy, kubectl은 허용되는 Version 차이가 정해져 있다. “대충 한두 Version”으로 기억하지 말고 대상 Version의 공식 Version Skew Policy를 확인한다.

Node가 오래된 상태로 남으면 새 API 기능을 기대하는 Workload와 충돌할 수 있다. 반대로 Node부터 Control Plane보다 앞서 올리는 순서도 지원되지 않을 수 있다. Upgrade 순서는 호환성 계약의 일부다.

## 3. API Deprecation과 제거

Deprecated API는 당장 동작할 수 있지만 미래 Version에서 제거된다. 저장된 Manifest뿐 아니라 Helm Template, CRD, Operator가 생성하는 Resource와 실행 중 Controller의 API 호출도 조사해야 한다.

```text
apiVersion: extensions/v1beta1  # 과거에는 허용
apiVersion: networking.k8s.io/v1 # 현재 대체 API
```

단순히 `apiVersion` 문자열만 바꾸면 Schema 필드와 기본값 차이를 놓칠 수 있다. Server-side Dry-run과 실제 Reconciliation을 검증한다.

## 4. CRD와 Webhook의 함정

Admission Webhook이 새 API 요청을 처리하지 못하거나 인증서가 만료되면 Resource 생성 전체가 막힐 수 있다. CRD의 Stored Version과 Served Version도 확인한다. Conversion Webhook이 있는 CRD는 기존 Object를 새 Schema로 읽고 쓸 수 있어야 한다.

Operator, Service Mesh, Observability Stack은 지원 Kubernetes Version 범위를 가진다. Cluster보다 먼저 호환 Version으로 올려야 하는 Component가 있을 수 있다.

## 5. Managed Add-on

EKS의 VPC CNI, CoreDNS, kube-proxy, EBS CSI Driver는 Cluster Networking과 Storage에 직접 영향을 준다. Add-on Version의 권장 조합과 Configuration Conflict를 확인한다.

VPC CNI Upgrade는 IP 할당과 NetworkPolicy 동작에, CoreDNS는 Service Discovery에, CSI Driver는 Volume Attach와 Mount에 영향을 준다. 하나씩 변경하고 핵심 신호를 관찰한다.

## 6. Node 교체와 Eviction

Managed Node Group이나 Karpenter Node를 교체할 때 Pod는 Drain된다. PDB, Termination Grace Period, Local Storage와 StatefulSet 제약이 교체 속도를 결정한다.

Replica 1개에 `minAvailable: 1`인 PDB는 안전장치가 아니라 Drain 교착을 만들 수 있다. 새 Node가 Ready하기 전에 기존 Node를 과도하게 줄이지 않도록 Surge Capacity와 AZ 분산을 확보한다.

## 7. Rollback의 현실

Kubernetes Control Plane은 일반 Application처럼 쉽게 이전 Minor Version으로 되돌릴 수 없다. 그래서 Rollback보다 사전 탐지, Staging 승격과 Workload 우회가 중요하다. Node Image와 Add-on은 되돌릴 수 있어도 새 API로 저장된 Object나 CRD Data 변환은 별도 복구가 필요할 수 있다.

## 8. 업그레이드 리허설

운영과 같은 Add-on·CRD를 가진 비운영 Cluster에서 먼저 실행한다. Deployment 성공만 보지 않고 DNS, Service Routing, PVC Attach, HPA Metric, Admission, GitOps Sync, Log·Trace 수집과 Node Drain을 검증한다.

Deprecated API Scanner의 결과가 0이어도 Runtime 호출을 놓칠 수 있으므로 API Server Audit나 EKS Upgrade Insight를 함께 본다.

## 9. 실무에서 빠지기 쉬운 설계

Add-on과 GitOps 구성이 잘 문서화되어도 Version 호환표, Deprecated API 검사와 Node Drain 리허설이 없다면 Upgrade는 담당자의 경험에 의존한다. Cluster 수명 주기가 길어질수록 한 번에 여러 Minor Version을 건너야 하는 압력이 커진다.

정기적인 작은 Upgrade를 Release Engineering 작업으로 취급하고, 호환성 표와 검증 시나리오를 코드로 남긴다. Upgrade 완료는 Version 숫자가 아니라 핵심 사용자 흐름과 Platform Controller가 다시 안정 상태에 도달한 시점이다.

## 10. 기억할 점

Kubernetes Upgrade의 본질은 API 계약과 여러 Control Loop의 호환성을 순서대로 옮기는 일이다. Control Plane, Add-on, Node와 Workload를 하나의 변경 단위로 보되 실제 변경은 작게 나눠야 한다.

# Reference
- [Upgrading Kubernetes clusters](https://kubernetes.io/docs/tasks/administer-cluster/cluster-upgrade/)
- [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
- [Version Skew Policy](https://kubernetes.io/releases/version-skew-policy/)
