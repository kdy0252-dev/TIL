---
id: Terraform Multi-Stack과 Remote State
started: 2026-06-27
tags:
  - ✅DONE
  - Terraform
  - AWS
  - Architecture
group:
  - "[[Infra AWS]]"
---
# Terraform Multi-Stack과 Remote State

## 1. 개요 (Overview)
Infrastructure 규모가 커지면 모든 Resource를 하나의 Terraform State에 두는 방식은 Plan 시간, 권한 범위와 장애 반경을 키웁니다. **Multi-stack**은 수명 주기와 소유권이 다른 Resource를 독립 State로 나누고 필요한 Output만 `terraform_remote_state`로 연결합니다.

---

## 2. Module과 Live Stack

```text
terraform/
  modules/
    networking/
    eks/
    elasticache/
  live/
    global/networking/
    platform/eks/
    platform/gitops/
    prod/redis/
```

- **Module**: 재사용 가능한 Resource 구성
- **Live Stack**: 실제 환경의 Provider, Backend, Variable과 Module 조합

Module은 환경 이름을 내부에 고정하지 않고 입력과 Output 계약을 가집니다.

---

## 3. Remote State

```hcl
data "terraform_remote_state" "eks" {
  backend = "s3"
  config = {
    bucket = "terraform-state"
    key    = "platform/eks/terraform.tfstate"
    region = "ap-northeast-2"
  }
}
```

Remote State는 Stack 간 결합을 명시하지만, Consumer가 Producer State 전체를 읽을 권한을 갖게 될 수 있습니다. 민감한 Output을 피하고 최소 권한을 적용합니다.

---

## 4. 사례 Stack 순서

```text
global/networking
  -> global/certs
  -> platform/eks
  -> platform/data / storage / addons
  -> platform/gitops / observability / service-mesh
  -> prod/ecr / auth / redis / routes
```

의존 Stack을 병렬 Apply하지 않고, 기반 Stack Output이 안정된 뒤 Consumer Stack을 적용합니다.

---

## 5. State 운영
- S3 Backend의 Versioning과 Encryption을 활성화합니다.
- Locking을 사용하여 동시 Apply를 막습니다.
- State Key 변경은 파일 이동이 아니라 명시적인 State Migration입니다.
- `.tfstate`, `.tfvars`, Certificate Private Key와 Secret을 Commit하지 않습니다.
- Apply 뒤 다시 Plan하여 Drift가 없는지 확인합니다.
- Stack별 IAM Role로 Blast Radius를 제한합니다.

---

## 6. 분리 기준
Network·Cluster처럼 변경 빈도가 낮고 영향이 큰 기반, Observability·GitOps 같은 공유 플랫폼, 환경별 Service Resource를 분리합니다. 너무 잘게 나누면 Remote State 연결과 실행 순서가 복잡해지므로 독립적인 수명 주기와 권한이 있는 단위로 나눕니다.

---

## 7. State는 무엇을 저장하는가
State에는 Resource ID, Attribute, Dependency와 일부 입력값이 저장됩니다. `sensitive = true`는 CLI 출력을 숨길 뿐 State에서 값을 제거하지 않습니다. State 접근 권한을 Production Credential 수준으로 보호합니다.

## 8. Locking과 동시성
같은 State에 두 Apply가 동시에 실행되면 서로의 변경을 덮어쓸 수 있습니다. Backend Locking을 사용하고 Lock 강제 해제는 실제 실행 중인 Process가 없는지 확인한 뒤 수행합니다.

서로 다른 Stack도 같은 AWS Resource를 소유하면 State가 달라도 충돌합니다. Resource Ownership Catalog가 필요합니다.

## 9. Remote State 결합
Consumer Stack이 Producer Output 이름에 의존하므로 Output은 API처럼 관리합니다.

- 내부 Resource 전체를 Output하지 않습니다.
- 안정적인 ID·ARN·Endpoint만 공개합니다.
- Output Rename은 Consumer를 먼저 호환시킨 뒤 제거합니다.
- 순환 Remote State 의존성을 만들지 않습니다.

## 10. Move와 Import
Code 위치만 바꾸면 Terraform은 기존 Resource 삭제와 새 Resource 생성을 계획할 수 있습니다.

```hcl
moved {
  from = aws_s3_bucket.old
  to   = module.storage.aws_s3_bucket.this
}
```

Stack 사이 이동은 `terraform state mv`와 Backend 간 State Migration 계획이 필요합니다. Plan의 Destroy가 의도치 않은지 반드시 검토합니다.

## 11. Provider와 Version
`required_version`, Provider Version Constraint와 Lock File을 관리합니다. 너무 넓은 `>=`만 사용하면 다음 Init에서 예기치 않은 Major 변경이 들어올 수 있습니다.

Upgrade는 Provider Changelog, State Schema, Deprecated Argument와 Plan을 별도 Branch에서 검증합니다.

## 12. Plan Review
Resource 수만 보지 않고 다음을 확인합니다.

- Replace가 발생하는 이유
- Security Group·IAM 권한 확대
- 공개 Endpoint·CIDR 변경
- Database·Volume 삭제
- Tag 변경으로 Add-on Discovery가 깨지는지
- `known after apply` 값이 하위 Stack에 주는 영향

## 13. Drift
Console이나 `kubectl`로 수동 변경하면 다음 Plan이 Drift를 보여줍니다. 긴급 조치는 허용할 수 있지만 안정화 뒤 Code에 반영하거나 원복합니다.

`ignore_changes`는 외부 Controller가 정당하게 소유한 필드에만 사용합니다.

## 14. Test와 검증
- `fmt`, `validate`, `tflint`, 보안 Scanner
- Module 단위 Test와 Plan Snapshot
- 개발 Account에서 Apply·Destroy
- Production Plan의 별도 승인
- Apply 뒤 No-op Plan

사례 Stack은 의존 순서대로 적용하고 여러 Stack을 한꺼번에 자동 Apply하지 않습니다.

---

## 15. 배포 사례 적용 진단과 개선 과제

기반·플랫폼·환경 Stack과 S3 Remote State가 분리되어 Blast Radius를 줄입니다. 그러나 Stack 간 Remote State Output이 많아지면 변경 순서와 암묵적 계약이 늘고, Sensitive Variable도 State에는 평문으로 저장될 수 있습니다.

State Bucket의 Versioning·KMS·접근 Log·Public 차단과 Lock을 검증하고, CI Role은 Stack별 최소 권한으로 분리합니다. Secret 값은 Terraform Resource가 반드시 생성해야 하는 경우 외에는 State를 통과시키지 않습니다. Output 계약은 이름·Type·소유자와 호환성 정책을 문서화합니다.

완료 기준은 Drift 탐지가 정기 실행되고 State 복구 훈련이 성공하며, `terraform show`에 재사용 가능한 Credential이 노출되지 않고, Stack 삭제·이동에 `moved/import` 계획과 승인 절차가 있는 상태입니다.

---

# Reference
- [Terraform S3 Backend](https://developer.hashicorp.com/terraform/language/backend/s3)
- [Terraform Remote State](https://developer.hashicorp.com/terraform/language/state/remote-state-data)
- [Terraform Module Development](https://developer.hashicorp.com/terraform/language/modules/develop)
- [[AWS Terraform]]
