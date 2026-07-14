---
id: EKS Access Entry와 Pod Identity
started: 2026-06-25
tags:
  - ✅DONE
  - AWS
  - EKS
  - IAM
group:
  - "[[Infra AWS]]"
---
# EKS Access Entry와 Pod Identity

## 1. 두 종류의 신원을 분리한다

EKS에는 사람과 Workload라는 서로 다른 주체가 접근한다. 운영자는 Kubernetes API를 호출하고, Pod는 S3·SQS·Secrets Manager 같은 AWS API를 호출한다. 둘을 같은 IAM User나 Node Role로 처리하면 권한 범위와 감사 주체가 흐려진다.

```text
운영자 -> IAM Role -> EKS Access Entry -> Kubernetes RBAC
Pod    -> ServiceAccount -> Pod Identity Association -> IAM Role -> AWS API
```

Access Entry는 사람이 Cluster 안에서 무엇을 할 수 있는지를, Pod Identity는 Workload가 AWS에서 무엇을 할 수 있는지를 다룬다.

## 2. EKS Access Entry

Access Entry는 IAM Principal을 EKS Cluster에 등록하는 API다. 인증과 인가를 구분해야 한다.

- IAM과 STS는 요청자의 신원을 인증한다.
- Access Entry는 그 Principal을 Cluster에 연결한다.
- EKS Access Policy 또는 Kubernetes RBAC가 허용 동작을 결정한다.

Cluster 관리자 권한을 개인 User에 직접 주기보다 Identity Center를 통해 받은 단기 Role을 등록한다. 읽기, 배포, 운영, 비상 관리자 역할을 분리하고 운영 환경은 Namespace 범위 Access Scope부터 검토한다.

## 3. EKS Access Policy와 RBAC

EKS Access Policy는 관리가 단순하지만 세밀한 Kubernetes Resource 규칙에는 RBAC가 더 적합하다. 한 Principal에 둘을 무분별하게 섞으면 최종 권한을 이해하기 어렵다.

```text
플랫폼 운영자: Cluster 범위 관리 정책
애플리케이션 배포자: 대상 Namespace의 Deployment/Rollout 조작
감사 사용자: 조회 전용
비상 관리자: 승인 후 짧게 활성화
```

권한 변경은 Terraform 같은 선언으로 리뷰하고 CloudTrail에서 Access Entry 변경 이력을 추적한다.

## 4. Pod Identity

Pod Identity Agent는 ServiceAccount와 IAM Role의 Association을 바탕으로 Pod에 임시 Credential을 제공한다. 애플리케이션은 AWS SDK의 기본 Credential Provider Chain을 사용하므로 장기 Access Key를 Secret에 저장할 필요가 없다.

```hcl
resource "aws_eks_pod_identity_association" "object_reader" {
  cluster_name    = var.cluster_name
  namespace       = "application"
  service_account = "object-reader"
  role_arn        = aws_iam_role.object_reader.arn
}
```

IAM Policy는 실제 API Action과 Resource ARN만 허용한다. 같은 ServiceAccount를 여러 성격의 Deployment가 공유하지 않으며 환경별 Role을 분리한다.

## 5. IRSA와의 관계

IRSA도 ServiceAccount와 IAM Role을 연결하는 검증된 방식이다. Pod Identity가 항상 상위 호환이라는 뜻은 아니다.

| 기준 | IRSA | Pod Identity |
|---|---|---|
| 신뢰 기반 | Cluster OIDC Provider | EKS Pod Identity Service |
| 연결 선언 | ServiceAccount Annotation | EKS Association |
| Role 재사용 | OIDC Trust 조건 필요 | Association 중심 |
| 적용 범위 | EKS와 OIDC 연동 | EKS 전용 |

기존 IRSA를 무조건 교체하기보다 신규 Workload의 표준을 정하고 SDK, Add-on, Cross-account 요구를 검증한 뒤 점진적으로 통일한다.

## 6. Node Role Credential 노출

Pod가 EC2 Instance Metadata Service에 접근할 수 있으면 Node Role Credential을 얻을 가능성이 있다. ServiceAccount Role을 잘 나눠도 Node Role이 광범위하면 경계가 무너진다.

- Node Role은 Image Pull과 Node 운영에 필요한 최소 권한만 가진다.
- IMDSv2를 강제하고 Hop Limit과 Network 접근을 검토한다.
- HostNetwork Pod와 특권 DaemonSet은 별도 위험으로 취급한다.
- AWS SDK가 기대한 Pod Role을 사용하는지 호출자 ARN으로 검증한다.

## 7. 하나의 요청은 어떻게 권한을 얻는가

운영자가 `kubectl get pods`를 실행하면 먼저 AWS Credential로 EKS 인증 Token을 만든다. API Server는 Token에서 IAM Principal을 확인하고 Access Entry를 통해 Kubernetes 사용자나 Group에 대응시킨 뒤 RBAC 규칙을 평가한다. Network가 열려 있다는 사실은 이 인가 과정을 생략하지 않는다.

Pod가 S3 Object를 읽을 때는 흐름이 다르다. AWS SDK가 Container Credential Provider에서 임시 Credential을 얻고 STS가 ServiceAccount와 연결된 IAM Role의 Session을 발급한다. S3는 IAM Policy, Bucket Policy, KMS Key Policy를 종합해 요청을 허용한다. 따라서 `AccessDenied`는 Pod Identity 하나만 확인해서 해결할 수 없다.

```text
kubectl: IAM Principal -> EKS 인증 -> Access Entry -> RBAC
SDK    : ServiceAccount -> 임시 Role Session -> IAM/Resource/Key Policy
```

## 8. 흔히 발생하는 실패

Access Entry를 만들었는데도 접근이 안 된다면 Cluster의 Authentication Mode와 Access Scope, RBAC Binding을 확인한다. 반대로 조회만 허용했다고 생각했는데 Resource를 수정할 수 있다면 다른 Group Binding이나 중첩된 Access Policy가 권한을 더하고 있을 수 있다.

Pod Identity Association을 만들었는데 SDK가 Node Role을 사용한다면 SDK Version과 Credential Provider Chain, Agent 상태, IMDS 접근을 확인한다. 권한 문제를 해결하려고 Node Role에 `*`를 추가하면 한 Pod의 문제가 Cluster 전체 Workload의 권한 확대로 바뀐다.

## 9. 실무에서 빠지기 쉬운 설계

EKS 구성에서 Access Entry와 ServiceAccount IAM 연동이 이미 사용되더라도 다음 경계가 설명되지 않으면 운영자는 실제 권한 모델을 이해하기 어렵다.

- 사람, CI/CD, Pod와 Node가 어떤 Principal을 사용하는가
- IRSA와 Pod Identity 중 무엇을 표준으로 선택했는가
- Node Role Credential로 우회할 수 있는가
- 비상 관리자 권한은 어떻게 승인되고 만료되는가

이를 보완하려면 Principal별 신뢰 관계를 한 장의 흐름으로 기록하고, 사람은 연합 신원의 단기 Session, Pod는 전용 ServiceAccount, Node는 Node 운영 권한만 사용하게 한다. 마지막 검증은 정책 파일을 읽는 데서 끝내지 않고 각 신원으로 허용·거부 API를 실제 호출하는 방식이 좋다.

## 10. 기억할 점

EKS의 권한 문제는 “IAM인가 RBAC인가”의 선택 문제가 아니다. AWS 인증, EKS 연결, Kubernetes 인가와 Workload Credential 전달이 직렬로 이어진다. 각 단계의 주체와 책임을 분리할수록 최소 권한과 사고 조사가 쉬워진다.

# Reference
- [EKS Access Entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
- [EKS Pod Identities](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IAM roles for service accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
