---
id: SLSA SBOM Cosign 공급망 보안
started: 2026-06-12
tags:
  - ✅DONE
  - Security
  - SLSA
  - SBOM
group:
  - "[[Docker]]"
---
# SLSA·SBOM·Cosign 공급망 보안

## 1. 개요

Software Supply Chain Security는 Source Commit부터 Dependency, Builder, Container Registry와 운영 Cluster까지 Artifact의 신뢰를 검증합니다.

```text
Source
  -> Dependency Resolution
  -> Build
  -> Image + SBOM + Provenance
  -> Signature
  -> Registry
  -> Admission Verification
  -> Runtime
```

취약점 Scan 하나로는 Build 변조, 다른 Source로 만든 Image, Registry Tag 교체를 막을 수 없습니다.

---

## 2. 위협 모델

- 악성 Dependency 또는 Dependency Confusion
- Build Agent 침해
- CI Script 변조
- Registry의 Tag 덮어쓰기
- 서명 Key 탈취
- 검증하지 않은 Base Image
- SBOM에 없는 파일의 포함
- 개발자가 Local에서 만든 Image의 운영 배포

어떤 위협을 막으려는지 먼저 정해야 도구 도입이 Checklist로 끝나지 않습니다.

---

## 3. Digest와 Tag

Tag는 변경 가능한 이름이고 Digest는 Content Address입니다.

```text
image:1.2.3                  -> 같은 Tag가 다른 내용일 수 있음
image@sha256:abcdef...       -> 특정 Image Content
```

Build·검증·승격·배포를 Digest로 연결합니다. 사람이 읽는 Tag는 Metadata로 유지할 수 있지만 보안 판단은 Digest를 사용합니다.

---

## 4. SBOM

Software Bill of Materials는 Artifact에 포함된 Component와 Version을 목록화합니다. 대표 형식은 SPDX와 CycloneDX입니다.

SBOM의 용도:

- 새 CVE 발생 시 영향 Image 검색
- License와 Dependency Inventory
- Base Image·OS Package 추적
- Release 간 Component Diff

SBOM은 취약점이 없다는 증명이 아닙니다. 내용의 Inventory이며 생성 시점과 실제 Image의 일치가 중요합니다.

---

## 5. 취약점 Scan

Source Dependency Scan과 최종 Image Scan을 모두 수행합니다. Image에는 OS Package, JRE와 Build 중 복사된 파일이 포함될 수 있습니다.

Gate 기준은 Severity 하나만 사용하지 않고 다음을 봅니다.

- 실제 Runtime에 도달 가능한가
- Exploit 가능성과 공개 여부
- Fix Version 존재 여부
- Internet 노출과 권한
- 보상 통제와 예외 만료일

DB Update가 오래되면 Scan 성공이 안전을 의미하지 않습니다.

---

## 6. Signature와 Cosign

Signature는 특정 Identity가 Image Digest를 승인했다는 증거입니다. Cosign은 OCI Artifact 서명과 검증에 사용됩니다.

Key Pair를 직접 관리하거나 OIDC Identity 기반 Keyless Signing을 사용할 수 있습니다. Keyless는 장기 Private Key 대신 CI Workload Identity와 투명성 Log를 활용합니다.

검증 정책은 단순히 “서명이 하나 있다”가 아니라 허용된 Issuer, Subject, Repository, Workflow와 Digest를 확인해야 합니다.

---

## 7. Provenance

Provenance는 Artifact가 어디서, 언제, 어떤 Source와 Builder로 만들어졌는지 설명하는 검증 가능한 Metadata입니다.

```text
Subject: Image Digest
Source: Repository + Commit
Builder: CI Identity
Build Type: Jib/Gradle Pipeline
Parameters: 허용된 비민감 Build 입력
Materials: Base Image와 Dependency
```

서명은 승인자를, Provenance는 생성 과정을 설명합니다. 둘은 대체 관계가 아닙니다.

---

## 8. SLSA

SLSA는 Supply Chain 보안을 단계적으로 높이는 Framework입니다. 최신 Specification은 Source와 Build Track에서 Provenance, 격리된 Build, 변조 방지 같은 보증을 정의합니다.

학습 시 Level 숫자만 목표로 삼지 말고 다음 질문을 봅니다.

- Build가 Source와 분리된 신뢰 환경에서 실행되는가
- Provenance를 Builder가 자동 생성하는가
- 사용자가 Provenance를 임의로 위조할 수 없는가
- Artifact Consumer가 정책으로 검증하는가

---

## 9. Reproducible과 Hermetic Build

Reproducible Build는 같은 입력이 같은 출력을 만드는 성질입니다. Hermetic Build는 선언된 입력 외 Network·Host 상태에 의존하지 않습니다.

Jib Layer Timestamp, Base Image Digest, Dependency Lock, JDK·Gradle Version을 고정합니다. 외부 Repository에서 `latest` Metadata를 읽거나 현재 시간을 Artifact에 넣으면 재현성이 깨집니다.

완전한 재현이 어렵더라도 변동 원인을 Inventory화하고 핵심 Layer Digest를 비교할 수 있습니다.

---

## 10. CI/CD 흐름

```text
Protected Source Commit
  -> Ephemeral Builder
  -> Test / Static Analysis
  -> Jib Image by Digest
  -> SBOM + Vulnerability Scan
  -> Provenance Attestation
  -> Keyless Signature
  -> ECR Push
  -> GitOps Digest Update
  -> Admission Verification
```

QA에서 검증한 Digest를 Production에 그대로 승격합니다. 환경별 재Build는 검증한 Artifact와 배포 Artifact를 다르게 만듭니다.

---

## 11. Admission Verification

서명과 Provenance를 생성해도 Cluster가 검증하지 않으면 우회 배포를 막지 못합니다. Kyverno, Sigstore Policy Controller 또는 다른 Admission Policy로 다음을 확인합니다.

- 허용 Registry
- Digest Pinning
- 허용 CI Identity의 Signature
- Source Repository와 Branch
- 필요한 Attestation과 SBOM

Emergency Image 정책도 사전 정의하고 Break-glass 사용을 감사합니다.

---

## 12. Secret과 Build Isolation

Build Secret은 Image Layer, Log, Provenance Parameter에 들어가면 안 됩니다. Builder는 작업마다 폐기하고 다른 Job의 Workspace·Credential·Docker Socket을 공유하지 않습니다.

Production Push 권한은 Test가 통과한 서명 단계에만 제공하고 Pull Request Build에는 부여하지 않습니다. OIDC Short-lived Credential로 장기 Access Key를 줄입니다.

---

## 13. 사례의 부족한 점과 해결

Jib와 ECR, GitOps Artifact Promotion 기반은 있지만 SBOM, Signature, Provenance와 Admission Verification이 하나의 신뢰 체인으로 완성됐다는 근거는 부족합니다.

1. Base Image와 Deployment를 Digest로 고정합니다.
2. Dependency Lock과 SBOM을 생성·보관합니다.
3. Source·Image 취약점 Scan에 예외 만료 정책을 둡니다.
4. CI OIDC Identity로 Image와 Attestation을 서명합니다.
5. GitOps에는 Tag보다 Digest를 기록합니다.
6. Stage에서 Audit 후 Production Admission Deny를 적용합니다.

---

## 14. Anti-pattern

- Tag를 서명하고 Digest를 검증하지 않습니다.
- SBOM 파일을 Image와 별개 위치에 이름만 맞춰 둡니다.
- 장기 Private Key를 Jenkins Home에 저장합니다.
- Scan 결과의 모든 Medium 취약점을 영구 예외 처리합니다.
- 서명은 생성하지만 Cluster에서 검증하지 않습니다.
- Production을 환경별로 다시 Build합니다.

---

## 15. 완료 기준

- [ ] Base Image와 배포 Image가 Digest로 고정됩니다.
- [ ] 모든 Release에 실제 Image와 연결된 SBOM이 있습니다.
- [ ] Source Commit, Builder와 Image Digest가 Provenance로 연결됩니다.
- [ ] 장기 서명 Key 없이 CI Identity로 서명할 수 있습니다.
- [ ] 취약점 예외에는 위험 근거와 만료일이 있습니다.
- [ ] 운영 Cluster는 허용된 Builder의 서명 Image만 실행합니다.
- [ ] QA에서 검증한 같은 Digest가 Production으로 승격됩니다.
- [ ] Break-glass 배포가 감사되고 자동 만료됩니다.

---

# Reference

- [SLSA Specification 1.2](https://slsa.dev/spec/v1.2/)
- [SLSA Provenance](https://slsa.dev/spec/v1.2/provenance)
- [Sigstore Cosign](https://docs.sigstore.dev/cosign/)
- [CycloneDX](https://cyclonedx.org/docs/)
- [SPDX](https://spdx.dev/)
- [[Jib와 Gradle 컨테이너 이미지 빌드]]
- [[Kubernetes Policy as Code]]
