---
id: Argo CD와 GitOps
started: 2026-06-29
tags:
  - ✅DONE
  - K8S
  - Argo-CD
  - GitOps
group:
  - "[[Infra K8S]]"
---
# Argo CD와 GitOps

## 1. 개요 (Overview)
**GitOps**는 Git Repository의 선언 상태를 배포 환경의 Source of Truth로 사용합니다. **Argo CD**는 Git의 Manifest·Helm Chart와 Kubernetes 실제 상태를 비교하고 차이를 동기화하는 Continuous Delivery Controller입니다.

---

## 2. Reconciliation Loop

```text
Git Desired State
  -> Argo CD Render
  -> Diff
  -> Sync
  -> Health Assessment
  -> Drift 발생 시 다시 Diff
```

CI가 Cluster에 직접 배포하는 Push 방식과 달리 Argo CD는 Cluster 내부에서 Git 상태를 Pull합니다.

---

## 3. Application 선언

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
spec:
  source:
    repoURL: https://example.com/deployment-config.git
    path: apps/development/core
  destination:
    namespace: development
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

- **Prune**: Git에서 삭제된 Resource를 Cluster에서도 삭제
- **Self Heal**: 수동 변경으로 생긴 Drift 복구
- **Sync Wave**: Resource 적용 순서 제어

자동 Prune은 편리하지만 Namespace, CRD, Stateful Resource에는 보호 정책이 필요합니다.

---

## 4. 실무 사례 적용 관점
이 사례는 환경·서비스별 Argo CD Application을 선언하고 Helm Chart를 Source로 사용합니다. Jenkins는 ECR Push 후 Chart의 Image Tag를 변경하며, Argo CD가 이를 EKS에 반영합니다.

`kustomization.yaml`은 여러 Argo CD Application Manifest를 묶는 용도로 사용합니다. 애플리케이션 Runtime Resource의 주 렌더링 도구는 Helm입니다.

---

## 5. Rollback
Git에서 이전 Image Tag Commit으로 되돌리는 것이 선언 상태의 Rollback입니다. Kubernetes에서만 수동으로 Rollback하면 Argo CD가 다시 Git 상태로 복구하므로 긴급 조치 후 반드시 Git을 일치시켜야 합니다.

---

## 6. 보안
- Argo CD Repository Credential과 Cluster Credential을 Secret으로 관리합니다.
- Project로 허용 Repository, Namespace, Resource Kind를 제한합니다.
- 기본 RBAC를 Read-only로 두고 Sync 권한을 최소화합니다.
- Manifest에 평문 Secret을 저장하지 않습니다.
- Admin 계정 대신 SSO와 감사 Log를 사용합니다.

---

## 7. Desired State와 Drift
Argo CD는 Live Resource를 Git의 Render 결과와 비교합니다. Kubernetes Controller가 자동으로 추가하는 필드나 Mutating Webhook 변경은 정상적인 차이일 수 있으므로 `ignoreDifferences`를 제한적으로 사용합니다.

무분별하게 전체 필드를 무시하면 실제 Drift도 보이지 않습니다. 어떤 Controller가 왜 필드를 소유하는지 기록합니다.

## 8. Sync 단계와 Hook

```text
PreSync: Migration 사전 검증
Sync:    ConfigMap, Service, Rollout 적용
PostSync: Smoke Test
SyncFail: 실패 알림·정리
```

Hook Job은 재실행 가능해야 하고 완료된 Resource의 삭제 정책을 정해야 합니다. DB Migration을 Hook으로 실행할 경우 여러 Application의 동시 Sync와 Version 호환성을 고려합니다.

## 9. Sync Wave
CRD, Controller, Custom Resource처럼 순서 의존성이 있는 Resource는 Wave를 사용합니다.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"
```

Wave는 Resource가 생성된 순서만이 아니라 Health가 완료되는 시점에도 영향을 받습니다. 지나치게 많은 Wave는 배포 흐름을 이해하기 어렵게 합니다.

## 10. ApplicationSet
환경·서비스 조합이 늘어나면 동일한 Application Manifest가 반복됩니다. ApplicationSet의 Git·List·Matrix Generator로 선언을 생성할 수 있습니다.

```text
environments [dev, qa, prod]
  × services [app, gateway, metrics, bff]
  -> Argo CD Applications
```

환경별 예외가 많다면 생성 Template이 복잡해질 수 있으므로 공통 규칙이 안정된 뒤 도입합니다.

## 11. Secret GitOps
Plain Secret을 Git에 저장하지 않습니다. 선택지는 다음과 같습니다.

- External Secrets Operator + AWS Secrets Manager
- Sealed Secrets
- SOPS 암호화
- 배포 전에 별도 Secret Provisioning

어떤 방식을 선택하든 Secret 소유권, Rotation, Argo CD 접근 권한과 장애 시 Bootstrap 절차가 필요합니다.

## 12. Multi-tenant Argo CD 보안
Argo CD Project로 다음을 제한합니다.

- 허용 Git Repository
- 배포 가능 Cluster·Namespace
- 허용·금지 Resource Kind
- Sync·Override 권한

Application Team이 Cluster-scoped CRD나 RBAC을 임의 생성하지 못하게 Platform과 Application 권한을 분리합니다.

## 13. 장애와 복구
- **OutOfSync 반복**: Field 소유권과 Mutating Controller 확인
- **Sync 실패**: Render 결과, Admission Webhook, CRD Version 확인
- **Unknown Health**: Custom Resource Health Check 정의 확인
- **Repository 연결 실패**: Credential, DNS, TLS, Rate Limit 확인
- **잘못된 자동 Prune**: Git Revert와 Resource 복구, Prune 보호 정책 검토

## 14. 검증 체크리스트
- Pull Request에서 Helm Render와 Schema를 검사합니다.
- Dev에서 Auto Sync·Prune·Self Heal 동작을 검증합니다.
- 수동 `kubectl edit` 후 Drift가 복구되는지 확인합니다.
- Git Revert로 실제 Rollback 시간을 측정합니다.
- Argo CD 자체 장애 시 기존 Workload가 계속 동작하는지 확인합니다.

---

## 15. 배포 사례 적용 진단과 개선 과제

Argo CD Application과 환경별 Chart가 Desired State를 제공하지만 Secret까지 Git에 들어가면 GitOps Audit 장점이 보안 위험으로 바뀝니다. Sync Wave·Hook 실패와 Terraform 소유 Resource의 경계도 자동 검증이 필요합니다.

External Secret Reference만 Git에 두고 실제 값은 Secret Manager에서 주입합니다. Argo Project로 Namespace·Cluster·Resource Kind를 제한하고 Prod Sync 권한과 Break-glass를 분리합니다. Orphan·Drift·Sync Failure를 Alert하고 Resource Ownership Label을 표준화합니다.

완료 기준은 Git에서 Cluster 상태를 재구성하되 Secret 값은 복원할 수 없고, 무단 Cluster 변경이 탐지·복구되며, Prod Application이 허용 Namespace 밖 Resource를 만들 수 없는 상태입니다.

---

# Reference
- [Argo CD Documentation](https://argo-cd.readthedocs.io/)
- [OpenGitOps Principles](https://opengitops.dev/)
- [[Jenkins CI-CD Pipeline]]
- [[Helm Application Chart 설계]]
