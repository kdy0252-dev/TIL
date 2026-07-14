---
id: EKS 기반 GitOps 플랫폼 아키텍처 사례
started: 2026-06-01
tags:
  - ✅DONE
  - Case-Study
  - Architecture
  - GitOps
group:
  - "[[Architecture]]"
---
# EKS 기반 GitOps 플랫폼 아키텍처 사례

## 1. 개요 (Overview)
이 사례는 **Terraform이 기반 인프라와 공유 플랫폼을 생성하고, Argo CD가 Git에 선언된 애플리케이션 상태를 EKS에 지속적으로 동기화**하는 구조입니다. 이후의 저장소 이름은 특정 제품명이 아니라 역할을 나타내는 일반 명칭으로 사용합니다.

```text
Terraform
  -> VPC / EKS / RDS / Redis / ECR / IAM
  -> Cluster Add-ons / Argo CD / Observability / Service Mesh

Application CI
  -> Image Build / ECR Push
  -> 배포 구성 저장소 Image Tag 변경

Argo CD
  -> Helm Render
  -> Argo Rollout
  -> EKS Runtime
```

---

## 2. 저장소 책임

| 저장소 | 책임 |
|---|---|
| 애플리케이션 저장소 | 애플리케이션 코드, 테스트, Image 생성 |
| 배포 구성 저장소 | AWS·EKS Infrastructure, Helm Chart, 환경별 Runtime 설정, GitOps 선언 |

Build Artifact와 Runtime Configuration을 분리하면 같은 Image를 환경별로 승격할 수 있습니다.

---

## 3. Terraform과 GitOps의 소유권 경계

### Terraform 소유
- VPC, EKS, RDS, ElastiCache, ECR, Cognito
- IAM·IRSA, Storage Class, Cluster Add-on
- Argo CD, Observability, Istio 같은 공유 플랫폼
- Route 53, ACM, CloudFront, S3

### Argo CD 소유
- 핵심 업무 애플리케이션, Gateway, BFF, Metrics Application
- Deployment 대신 Argo Rollout
- Service, Ingress, ConfigMap, ServiceMonitor
- 환경별 Image Tag와 Resource 설정

같은 Kubernetes Resource를 Terraform과 Argo CD가 동시에 관리하면 지속적인 Drift와 덮어쓰기가 발생합니다.

---

## 4. 환경 구조
하나의 공유 EKS Cluster에서 Dev·QA·Prod를 Namespace와 Node Label로 분리합니다. 환경별 Helm Chart와 Argo CD Application이 각각의 Desired State를 가집니다.

공유 Cluster는 비용과 운영을 줄이지만 다음 격리가 필요합니다.

- Namespace와 RBAC
- Node Selector·Affinity·Taint
- ResourceQuota·LimitRange
- NetworkPolicy 또는 Service Mesh Authorization
- 환경별 IAM·Secret·Domain
- Production Priority와 PodDisruptionBudget

---

## 5. 배포 흐름

```text
Commit
  -> Jenkins 검증
  -> Jib Image
  -> ECR
  -> values.yaml Image Tag Commit
  -> Argo CD Reconciliation
  -> Argo Rollouts Blue-Green
  -> Health / Metric 확인
```

CI가 Cluster에 직접 `kubectl apply`하지 않고 Git의 선언 상태를 변경하면 배포 이력, 승인과 Rollback 기준이 명확해집니다.

---

## 6. 주요 품질 속성
- **재현성**: Terraform Module과 Helm Chart로 환경 선언
- **감사 가능성**: Git Commit이 인프라·배포 변경 이력
- **복구성**: Drift 자동 조정과 이전 Commit Rollback
- **배포 안전성**: Blue-Green, Preview Service, Probe
- **확장성**: Karpenter와 Resource Request
- **관측성**: ServiceMonitor, LGTM, Alertmanager

---

## 7. Control Plane과 Data Plane

```text
Control Plane
  -> Terraform, Argo CD, istiod, Operators

Data Plane
  -> core application, gateway, metrics, BFF, ztunnel
```

Control Plane 장애가 기존 Data Plane Traffic을 즉시 중단하지 않도록 설계합니다. Argo CD가 멈춰도 실행 중인 Pod는 계속 동작하지만 새 배포와 Drift 복구는 중단됩니다.

## 8. Shared Cluster 트레이드오프

### 장점
- EKS Control Plane과 Platform 운영 비용 공유
- Observability·GitOps·Mesh의 단일 운영
- 환경 간 동일 Add-on Version

### 위험
- Cluster 장애의 환경 공동 영향
- Dev 부하가 Production Resource에 영향
- RBAC·Network·Node 격리 복잡성
- Platform Upgrade의 Blast Radius

Namespace만으로 완전한 보안·자원 격리가 되지 않습니다. NodePool, Quota, Priority, NetworkPolicy와 IAM을 결합합니다.

## 9. Bootstrap 순서

```text
AWS Foundation
  -> EKS
  -> Storage / Add-ons
  -> Argo CD
  -> Observability / Service Mesh
  -> Application Namespace
  -> Application
```

Argo CD 자체를 Argo CD가 처음부터 관리할 수 없으므로 Terraform이 Bootstrap하고 이후 소유권을 명확히 유지합니다.

## 10. 구성 계층
- Image: 환경 중립 실행 코드
- Helm Values: 환경별 Resource·Endpoint·Profile
- ConfigMap: 비민감 Spring 설정
- Secret: Credential·Key
- Terraform Variable: 인프라 입력

같은 설정을 여러 계층에 중복 정의하면 어느 값이 우선인지 불명확해집니다.

## 11. 네트워크 경계

```text
Internet
  -> Public ALB / CloudFront
  -> Gateway / Static Frontend

Internal
  -> Internal ALB
  -> Application Service

Data
  -> RDS / ElastiCache Security Group
```

Istio Routing과 AWS Security Group은 서로 다른 계층입니다. 둘 중 하나가 허용해도 다른 계층이 차단할 수 있습니다.

## 12. 데이터 계층
RDS PostgreSQL과 ElastiCache는 EKS와 독립적인 관리형 Data Plane입니다. Application Rollback과 DB Schema Rollback은 분리되므로 Expand-and-Contract Migration을 사용합니다.

Backup, PITR, Multi-AZ, Connection Capacity와 Maintenance Window를 Application SLO와 연결합니다.

## 13. 배포 Artifact 추적
Source Commit, Jib Image Digest, ECR Tag, 배포 구성 저장소 Commit과 Argo Rollout Revision을 연결합니다.

```text
source sha
  -> image digest
  -> deploy commit
  -> rollout revision
```

장애 시 어떤 코드와 설정이 실행 중인지 한 번에 찾을 수 있어야 합니다.

## 14. Disaster Recovery
- Terraform State와 Git Repository 복구
- EKS 재생성 후 Add-on Bootstrap
- RDS·Redis 복구
- Argo CD Application 재동기화
- DNS·Certificate 복구

Infrastructure as Code가 있어도 Data와 Secret Backup이 없으면 복구되지 않습니다. 실제 순서와 RTO를 Runbook으로 시험합니다.

## 15. 변경 소유권 표

| 변경 | 소유 도구 |
|---|---|
| VPC·EKS·RDS | Terraform |
| Cluster Add-on | Terraform Helm Provider |
| Application Rollout·Service | Argo CD + Helm |
| Image | Jenkins + Jib |
| Runtime Secret | Secret 관리 체계 |
| DB Schema | Liquibase |

## 16. 아키텍처 검증
- Terraform No-op Plan
- Helm Render·Schema Test
- Argo CD Sync·Drift Test
- Rollout Preview·Rollback Test
- Node Drain·AZ 장애 Test
- Backup Restore Drill
- 환경 간 Network·IAM 격리 Test

---

## 17. 현재 플랫폼의 부족한 점과 우선순위

현재 구조는 Terraform·GitOps 소유권과 Blue-Green 배포 기반이 좋지만, 선언만으로 격리가 완성되지는 않았습니다. 저장소 조사 기준으로 NetworkPolicy, ResourceQuota, LimitRange, Application PDB 선언이 보이지 않으며 공유 Cluster의 환경 간 Blast Radius가 큽니다. 설정 파일과 Terraform Variable에 비밀값이 직접 들어갈 수 있는 흔적도 있습니다.

P0는 비밀값을 즉시 회전하고 Secret Manager/External Secrets 계열 Runtime 주입으로 바꾸는 것입니다. P1은 Prod RDS Multi-AZ, NetworkPolicy·PDB·Quota, 복구 훈련입니다. P2는 단일 NAT와 공유 Cluster의 비용·가용성 Trade-off를 SLO로 재결정하는 것입니다.

완료 기준은 Git·Terraform State·Rendered Manifest에 평문 Secret이 없고, 환경 간 Network/Resource 침범 Test가 실패하며, AZ·Node·Controller 장애 Game Day에서 정의된 RTO 안에 복구하는 상태입니다.

---

# Reference
- [[Terraform Multi-Stack과 Remote State]]
- [[Helm Application Chart 설계]]
- [[Argo CD와 GitOps]]
- [[Argo Rollouts Blue-Green 배포]]
- [[EKS Cluster Add-on 아키텍처]]
- [[Istio Ambient Mesh와 Kiali]]
