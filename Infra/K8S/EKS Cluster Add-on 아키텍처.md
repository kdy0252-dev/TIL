---
id: EKS Cluster Add-on 아키텍처
started: 2026-07-02
tags:
  - ✅DONE
  - K8S
  - EKS
  - AWS
group:
  - "[[Infra K8S]]"
---
# EKS Cluster Add-on 아키텍처

## 1. 개요 (Overview)
EKS Cluster는 애플리케이션 Pod만으로 운영되지 않습니다. Network, Storage, Ingress, DNS, Certificate, Metric과 Node 확장을 담당하는 **Cluster Add-on**이 Kubernetes Resource를 AWS Resource와 연결합니다.

---

## 2. 사례 Add-on 구성

| Add-on | 역할 |
|---|---|
| VPC CNI | Pod에 VPC Network 연결 |
| CoreDNS | Cluster DNS |
| kube-proxy | Service Network |
| AWS Load Balancer Controller | Ingress·Service를 ALB/NLB로 변환 |
| external-dns | Ingress·Service 기반 Route 53 Record 조정 |
| cert-manager | Kubernetes Certificate Lifecycle |
| EBS CSI Driver | EBS Persistent Volume Provisioning |
| Metrics Server | HPA와 `kubectl top` Resource Metric |
| Karpenter | 수요 기반 EC2 Node Provisioning |

---

## 3. IRSA
**IAM Roles for Service Accounts(IRSA)**는 Kubernetes Service Account와 IAM Role을 연결해 Pod에 최소 AWS 권한을 제공합니다.

```text
Pod
  -> ServiceAccount
  -> EKS OIDC Token
  -> AssumeRoleWithWebIdentity
  -> Temporary AWS Credential
```

Node IAM Role에 광범위한 권한을 주는 대신 EBS CSI, VPC CNI, external-dns, Kubecost 같은 Controller별 Role을 분리합니다.

### 신뢰 체인

IRSA가 동작하려면 EKS OIDC Provider, IAM Role의 Trust Policy, ServiceAccount Annotation 세 요소가 정확히 연결되어야 합니다. 권한 정책만 맞아도 Trust Policy의 `sub`가 다른 Namespace나 ServiceAccount를 가리키면 AssumeRole이 실패합니다.

```text
iss  = EKS OIDC issuer
sub  = system:serviceaccount:<namespace>:<service-account>
aud  = sts.amazonaws.com
```

Controller마다 별도 Role을 두면 침해 범위를 줄이고 CloudTrail에서 어떤 Controller가 AWS API를 호출했는지도 구분할 수 있습니다. Wildcard Resource는 AWS API 특성상 불가피한 경우에만 허용하고, Route 53 Hosted Zone이나 KMS Key처럼 범위를 좁힐 수 있는 Resource는 명시합니다.

---

## 4. AWS Load Balancer Controller
Ingress Annotation을 읽어 ALB, Listener, Target Group과 Health Check를 생성합니다.

```yaml
annotations:
  alb.ingress.kubernetes.io/scheme: internal
  alb.ingress.kubernetes.io/target-type: ip
  alb.ingress.kubernetes.io/healthcheck-path: /actuator/health/liveness
```

Public·Internal Scheme, Ingress Group, Certificate, Deregistration Delay와 Security Group을 환경 경계에 맞게 설계합니다.

### Reconciliation과 장애 진단

Controller는 Ingress를 한 번 변환하고 끝나는 것이 아니라 Kubernetes 상태와 AWS 상태를 계속 비교합니다. Annotation 오류, IAM 권한 부족, Subnet Tag 누락은 대개 Ingress Event와 Controller Log에 나타납니다.

```bash
kubectl describe ingress <name> -n <namespace>
kubectl logs -n kube-system deploy/aws-load-balancer-controller
```

ALB가 생성됐지만 Target이 Unhealthy라면 Controller보다 다음을 먼저 확인합니다.

- Health Check Path와 애플리케이션 Port가 일치하는가
- Target Type `ip`에서 Pod Security Group 경로가 열려 있는가
- Readiness Probe와 ALB Health Check가 서로 다른 준비 기준을 사용하지 않는가
- Rollout 전환 시 Deregistration Delay보다 Pod 종료 유예가 짧지 않은가

---

## 5. external-dns와 cert-manager
- external-dns는 Kubernetes Desired State에 맞춰 Route 53 Record를 생성·갱신합니다.
- cert-manager는 Issuer와 Certificate Resource를 기반으로 TLS Certificate를 발급·갱신합니다.
- AWS ACM Certificate를 ALB에서 직접 사용하는 방식과 cert-manager Secret 방식의 소유권을 혼합하지 않습니다.

external-dns는 소유권을 TXT Record로 기록할 수 있습니다. 여러 Cluster가 같은 Hosted Zone을 관리하면 `txt-owner-id`를 환경별로 분리해 다른 Cluster의 Record를 삭제하지 못하게 해야 합니다. Domain Filter로 관리 범위를 제한하는 것도 중요합니다.

Certificate 자동 갱신은 발급 성공만 확인해서는 부족합니다. 만료 잔여 기간, 갱신 실패 Event, 실제 Load Balancer가 제공하는 인증서를 함께 감시해야 합니다. Kubernetes Secret을 갱신했어도 Ingress나 Gateway가 새 인증서를 읽지 못한 경우가 있기 때문입니다.

---

## 6. EBS CSI와 Storage Class
EBS CSI Driver는 PVC 요청에 따라 암호화된 gp3 Volume을 생성합니다. `WaitForFirstConsumer`를 사용하면 Pod가 배치될 Availability Zone을 결정한 뒤 Volume을 생성해 Zone 불일치를 피할 수 있습니다.

Stateful Component의 Reclaim Policy, Snapshot, Backup과 Node Drain 동작을 별도로 검증합니다.

### EBS의 Zone 제약

EBS Volume은 한 Availability Zone에 속합니다. Pod가 다른 Zone으로 이동하면 기존 Volume을 즉시 Attach할 수 없습니다. 따라서 StatefulSet에는 다음을 함께 검토합니다.

- `WaitForFirstConsumer` StorageClass
- Pod Topology Spread 또는 Affinity
- Volume Snapshot과 Restore 절차
- Multi-Attach Error 발생 시 기존 Node의 Detach 완료 시간
- 장애 시 RTO가 EBS 재연결 시간보다 짧은지 여부

여러 Zone에서 동시에 쓰기가 필요한 데이터는 EBS 복제만으로 해결되지 않습니다. 애플리케이션 수준 복제, 관리형 데이터베이스 또는 EFS 같은 다른 저장 계층을 선택해야 합니다.

---

## 7. VPC CNI의 IP 주소 관리

AWS VPC CNI는 Pod에 VPC IP를 할당합니다. 이 방식은 ALB의 IP Target과 자연스럽게 연결되지만, Node CPU보다 Subnet IP가 먼저 고갈될 수 있습니다.

확인해야 할 항목은 다음과 같습니다.

- 각 Subnet의 가용 IP 수
- Instance Type별 ENI와 Secondary IP 한도
- Prefix Delegation 사용 여부
- `WARM_IP_TARGET`, `MINIMUM_IP_TARGET` 설정
- DaemonSet와 급격한 Scale-out이 소비하는 IP 여유분

Pod가 `Pending`인데 Scheduler Event에 IP 할당 실패가 보이면 Node 수만 늘리기 전에 Subnet 용량과 CNI Metric을 확인합니다. 작은 Subnet에서 Karpenter만 공격적으로 확장하면 EC2는 생성돼도 Pod IP를 받을 수 없습니다.

---

## 8. CoreDNS와 kube-proxy

CoreDNS는 Service Discovery의 공통 의존성입니다. CPU Throttling이나 Upstream DNS 지연은 모든 서비스의 간헐적 Timeout처럼 보일 수 있습니다. Replica를 여러 Zone에 분산하고, Request·Limit와 Cache 설정을 실제 Query Rate에 맞춥니다.

kube-proxy는 Service의 Virtual IP를 실제 Endpoint로 전달합니다. EKS Version Upgrade 시 kube-proxy, VPC CNI, CoreDNS의 호환 버전을 함께 검토해야 합니다. Control Plane만 업그레이드하고 Add-on을 오래 방치하면 지원되지 않는 조합이 남습니다.

DNS 장애 진단은 Application Log만 보지 말고 다음 순서로 범위를 좁힙니다.

```text
Pod resolv.conf
  -> ClusterIP DNS
  -> CoreDNS Pod
  -> Kubernetes API Service/Endpoint 정보
  -> VPC Resolver 또는 외부 DNS
```

---

## 9. Metrics Server의 역할과 한계

Metrics Server는 Kubelet의 최근 CPU·Memory 사용량을 모아 HPA와 `kubectl top`에 제공합니다. 장기 보관, SLO 분석, 정교한 Alert 목적의 Monitoring System은 아닙니다.

HPA가 `unknown`을 표시하면 다음을 확인합니다.

- 대상 Container에 Resource Request가 있는가
- Metrics Server가 Kubelet에 접근할 수 있는가
- APIService가 Available 상태인가
- 새 Pod의 초기 Metric이 아직 수집되지 않은 것은 아닌가

Queue Length나 Request Latency처럼 업무 Metric으로 확장하려면 Prometheus Adapter 또는 KEDA 같은 별도 경로가 필요합니다. CPU HPA만으로 I/O 중심 서비스의 포화를 정확히 판단하기 어렵습니다.

---

## 10. Add-on 설치 순서와 소유권

의존 관계가 있는 Add-on은 순서가 중요합니다.

```text
EKS / OIDC Provider
  -> VPC CNI, CoreDNS, kube-proxy
  -> EBS CSI, Load Balancer Controller, Karpenter
  -> cert-manager CRD
  -> Ingress, Certificate, Application Workload
```

Terraform이 Helm Release를 설치하는 동안 Argo CD도 같은 Release를 관리하면 Field Manager 충돌과 반복 Drift가 발생합니다. 부트스트랩 계층은 Terraform, 지속적으로 변하는 애플리케이션 계층은 Argo CD처럼 책임을 명시하고 예외를 최소화합니다.

CRD를 삭제하면 Custom Resource뿐 아니라 운영 상태가 대량으로 사라질 수 있습니다. Helm Uninstall이나 Terraform Destroy가 CRD까지 제거하는지 사전에 확인합니다.

---

## 11. Upgrade 전략

Add-on Upgrade는 다음 순서로 수행합니다.

1. EKS와 Add-on의 지원 Version Matrix를 확인합니다.
2. CRD와 API Deprecation을 검사합니다.
3. 비운영 환경에서 Controller 교체 중 데이터 경로가 유지되는지 확인합니다.
4. Controller Log와 Reconciliation Error가 안정화된 뒤 다음 Add-on으로 이동합니다.
5. Application 배포와 Cluster Add-on Upgrade를 같은 변경 창에 섞지 않습니다.

DaemonSet Add-on은 모든 Node를 순차 교체하므로 PDB만으로 안전성이 보장되지 않습니다. CNI와 CSI처럼 데이터 경로에 있는 구성요소는 새 Pod Ready뿐 아니라 실제 Network·Volume 기능을 Smoke Test해야 합니다.

---

## 12. Add-on 운영 원칙
- Kubernetes Version과 Add-on 호환표를 확인합니다.
- CRD가 필요한 Chart는 Upgrade 순서를 관리합니다.
- Controller를 Platform Node에 배치하여 업무 Node 변동과 격리합니다.
- Resource Request·Limit와 PodDisruptionBudget을 설정합니다.
- Terraform과 Helm·Argo CD 중 하나만 Resource 소유자가 되게 합니다.

### 점검표

- [ ] Controller별 ServiceAccount와 IRSA 권한이 분리되어 있는가
- [ ] System Add-on이 둘 이상의 Zone과 Node에 분산되는가
- [ ] Subnet IP와 Controller API Rate Limit에 여유가 있는가
- [ ] CRD Backup과 Upgrade·Rollback 절차가 있는가
- [ ] Controller Reconcile Error와 인증서 만료를 경보하는가
- [ ] EKS Upgrade 전에 Add-on 호환성을 자동 검사하는가
- [ ] Terraform과 GitOps의 Resource 소유자가 겹치지 않는가
- [ ] Node Drain 상황에서 CNI·CSI·DNS 기능을 검증했는가

---

## 13. 배포 사례 적용 진단과 개선 과제

주요 Add-on과 IRSA가 구성되어 있지만 Cluster 핵심 Controller의 PDB·Topology·Resource가 모두 동일한 수준으로 검증됐다고 보기 어렵고, Add-on Version 호환과 CRD Upgrade가 Terraform Apply에 결합됩니다.

EKS Version별 Add-on Compatibility Matrix를 저장소에 두고 Renovation PR마다 비운영 Smoke Test를 실행합니다. CoreDNS, CNI, CSI, Load Balancer Controller를 Platform Node와 여러 AZ에 분산하고 Controller별 Reconcile Error·IRSA 실패를 경보합니다.

완료 기준은 Node Drain 중 DNS·IP 할당·Volume Attach·Ingress Reconcile이 유지되고, Control Plane Upgrade 전후 Add-on E2E Test가 자동 통과하며, Terraform과 Argo CD가 같은 Add-on Resource를 동시에 소유하지 않는 상태입니다.

---

# Reference
- [EKS Add-ons](https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [ExternalDNS](https://kubernetes-sigs.github.io/external-dns/)
- [cert-manager](https://cert-manager.io/docs/)
- [EBS CSI Driver](https://docs.aws.amazon.com/eks/latest/userguide/ebs-csi.html)
- [[Karpenter Node 자동 확장]]
