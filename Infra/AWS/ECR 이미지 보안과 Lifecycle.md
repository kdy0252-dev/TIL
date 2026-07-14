---
id: ECR 이미지 보안과 Lifecycle
started: 2026-06-24
tags:
  - ✅DONE
  - AWS
  - ECR
  - Security
group:
  - "[[Infra AWS]]"
---
# ECR 이미지 보안과 Lifecycle

## 1. Registry는 배포 공급망의 경계다

ECR은 Image 보관소이면서 Build 결과가 운영에 들어가기 직전의 신뢰 경계다. `latest` Tag를 덮어쓸 수 있고 취약한 Image가 승인 없이 배포된다면 CI가 안전해도 운영 Artifact를 신뢰할 수 없다.

```text
Source -> Build -> Scan/SBOM/Sign -> ECR Digest
                                  -> 승인 -> 운영 배포
```

## 2. Tag와 Digest

Tag는 사람이 읽기 좋은 가변 포인터이고 Digest는 Content로 결정되는 불변 식별자다. 같은 `v1.2.0` Tag를 다시 Push하면 어떤 Binary가 실행됐는지 모호해진다.

- Repository의 Tag Immutability를 활성화한다.
- 배포 Manifest는 가능하면 Digest로 고정한다.
- 환경 승격은 Rebuild가 아니라 동일 Digest를 Promote한다.
- Git Commit, Image Digest, SBOM, 배포 Revision을 연결한다.

## 3. 취약점 Scan

Push 시 Scan은 알려진 Package 취약점을 조기에 발견하지만 안전성 전체를 증명하지 않는다. Base Image, OS Package와 Language Dependency를 모두 보며 심각도만으로 차단하지 않고 실행 가능성, 노출 경로와 수정 Version을 평가한다.

Enhanced Scanning을 사용할 때 Scan 범위, 재Scan 주기와 Finding 집계 위치를 정한다. 어제 안전했던 Image도 새 CVE 공개 후 위험해질 수 있다.

## 4. Lifecycle Policy

Lifecycle Policy는 비용 절감뿐 아니라 Rollback 가능 기간을 결정한다. 최근 Image만 남기는 규칙이 운영 Rollback에 필요한 Digest를 삭제하면 복구가 늦어진다.

```text
untagged: 짧게 보관 후 제거
개발 Tag: 개수 또는 기간 기준 정리
운영 Release Digest: Rollback·감사 기간 동안 보관
```

규칙 적용 전 Preview를 검토하고 Release와 Evidence Artifact의 보관 기간을 맞춘다.

## 5. Repository Policy와 Network

CI Role에는 Push, Runtime Node에는 Pull만 허용한다. Cross-account 배포는 특정 Account와 Role만 허용하고 Public Principal을 금지한다. ECR API와 Docker Endpoint, S3 Gateway Endpoint를 사용하면 Private Workload의 Image Pull이 NAT에 덜 의존한다.

## 6. 서명과 Admission

취약점 Scan은 “알려진 문제”를 찾고 Signature는 “승인된 Build가 만든 Artifact인가”를 검증한다. Cosign으로 Digest에 서명하고 Admission Policy가 서명, Issuer, Repository와 Attestation을 확인하도록 구성할 수 있다.

SBOM은 Image 안의 Component 목록이다. Signature와 SBOM을 같은 Digest에 연결해야 사고 시 영향받는 Image를 빠르게 찾을 수 있다.

## 7. 개발에서 운영까지 같은 Image를 써야 하는 이유

환경마다 Source를 다시 Build하면 개발에서 검증한 Artifact와 운영 Artifact가 다를 수 있다. Compiler, Base Image와 Dependency Repository가 바뀌기 때문이다. 한 번 Build한 Digest를 개발, 검증, 운영으로 승격하면 환경별 차이는 설정에만 남는다.

```text
Build once -> sha256:abc...
           -> dev 검증 -> stage 검증 -> prod 승인
```

운영 장애 때도 Source를 다시 Build하지 않고 이미 검증된 이전 Digest로 돌아갈 수 있다. Lifecycle Policy는 이 Rollback Window보다 오래 운영 Digest를 보존해야 한다.

## 8. Scan 결과를 어떻게 판단할까

Critical CVE가 있다는 사실만으로 모든 배포를 영구 차단하면 팀은 곧 예외를 남발한다. 반대로 Base Image 문제라는 이유로 무시하면 Internet에 노출된 취약 Library가 남을 수 있다. Package가 Runtime Image에 존재하는지, 취약 기능이 호출 가능한지, Network에서 도달 가능한지, 수정 Version이 있는지를 함께 본다.

예외에는 근거, 소유자와 만료일을 두고 새 CVE 공개 시 실행 중인 Digest도 다시 평가한다. Image Scan은 Source Scan, Secret Scan과 Runtime 탐지를 대체하지 않는다.

## 9. 실무에서 빠지기 쉬운 설계

Push Scan과 Lifecycle Policy가 이미 있어도 Tag를 덮어쓸 수 있고 배포가 Tag만 참조한다면 실행 Artifact의 정체가 바뀔 수 있다. Scan Finding이 Ticket으로만 남고 Admission과 연결되지 않으면 위험한 Image도 그대로 배포된다.

이 간극은 Tag 불변성, Digest 승격, SBOM·Signature 생성과 Admission 검증으로 연결한다. 보관 규칙은 단순한 “최근 N개”가 아니라 운영 Rollback과 감사 기간을 기준으로 정한다.

## 10. 기억할 점

Registry 보안의 목적은 Image를 많이 검사하는 것이 아니라 실행 중인 Binary가 어디서 왔고 무엇을 포함하며 누가 승인했는지 증명하는 것이다. Digest가 Source Commit, SBOM, Signature와 배포 Revision을 잇는 공통 열쇠다.

# Reference
- [Amazon ECR image scanning](https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html)
- [Amazon ECR lifecycle policies](https://docs.aws.amazon.com/AmazonECR/latest/userguide/LifecyclePolicies.html)
- [[SLSA SBOM Cosign 공급망 보안]]
