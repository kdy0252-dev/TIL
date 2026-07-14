---
id: Jenkins CI-CD Pipeline
started: 2026-06-13
tags:
  - ✅DONE
  - Infra
  - CI-CD
  - Jenkins
group:
  - "[[Infra]]"
---
# Jenkins CI/CD Pipeline 설계

## 1. 개요 (Overview)
**Jenkins Pipeline**은 Build, Test, Image 생성, 배포를 코드로 정의합니다. 좋은 Pipeline은 명령을 자동화하는 수준을 넘어 동일 Artifact 승격, 빠른 실패, 재현 가능한 환경과 배포 감사 기록을 제공합니다.

---

## 2. 사례 Pipeline 흐름

```text
Checkout
  -> Unit / Integration / Migration / Architecture Test
  -> Checkstyle
  -> BootJar
  -> Jib Image Build
  -> Docker Compose
  -> Newman E2E
  -> ECR Push
  -> 배포 구성 저장소 Manifest Tag 변경
  -> Argo CD Sync
```

검증이 끝난 Image를 다시 만들지 않고 동일 Digest를 환경에 승격하는 것이 핵심입니다.

---

## 3. Pipeline 단계 설계
- **Build**: Compiler, Error Prone, Checkstyle을 가장 먼저 실행해 빠르게 실패합니다.
- **Test**: 단위, 통합, Migration, Architecture, External API Test를 목적별로 분리합니다.
- **Package**: Commit Hash와 Build Number로 추적 가능한 Image Tag를 생성합니다.
- **Integration**: 실제 Image를 Compose로 기동하고 Newman으로 Gateway부터 DB까지 검증합니다.
- **Publish**: 성공한 Image만 ECR로 Push합니다.
- **Deploy**: GitOps Repository의 선언 상태를 변경하고 실제 배포는 Argo CD에 위임합니다.

---

## 4. Branch와 Release 정책

| Trigger | 대상 | Version 예 |
|---|---|---|
| Main Branch | Dev | Commit Hash |
| QA Tag | QA | `v1.2.3` |
| Production Tag | Prod | 승인된 Release Tag |

Tag 형식만으로 Production 배포를 허용하지 말고 승인·보호 규칙·배포 권한을 함께 적용합니다.

---

## 5. 보안
- AWS Credential과 Git Token은 Jenkins Credential Store에서 주입합니다.
- Shell 출력에 Secret이 노출되지 않게 Masking합니다.
- Build Agent는 최소 권한 IAM Role을 사용합니다.
- Pull Request의 신뢰할 수 없는 Script가 Production Credential에 접근하지 못하게 분리합니다.
- Artifact에 환경별 설정과 Secret을 포함하지 않습니다.

---

## 6. 실패 진단
항상 다음 Artifact를 남깁니다.

- JUnit XML과 Test Report
- Checkstyle·Architecture Test 결과
- Newman JSON Report
- Compose Service Log
- Image Tag와 Digest
- 변경된 Deployment Manifest Commit

Cleanup은 `post { always { ... } }`에서 수행하여 실패해도 Container와 임시 Image가 남지 않게 합니다.

---

## 7. Declarative Pipeline 구조

```groovy
pipeline {
    agent { label 'java-build' }
    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 60, unit: 'MINUTES')
    }
    stages {
        stage('Verify') { steps { sh './gradlew check' } }
        stage('Image')  { steps { sh './gradlew jibDockerBuild' } }
        stage('E2E')    { steps { sh './scripts/run-e2e.sh' } }
    }
}
```

전체 Timeout뿐 아니라 외부 API Test, Compose Health 대기와 배포 단계에 개별 Timeout을 둡니다.

## 8. Agent 격리
Build Agent는 작업마다 깨끗한 Workspace와 Docker Resource를 가져야 합니다. Shared Agent의 Gradle Cache는 성능을 높이지만 잘못된 권한·손상·교차 Job 오염을 관리해야 합니다.

Kubernetes 기반 Ephemeral Agent는 격리에 유리하지만 Docker Build 방식, Cache Volume, Network와 Pod Startup 비용을 설계해야 합니다.

## 9. Cache 전략
- Gradle User Home Cache
- Dependency Download Cache
- Jib Base·Dependency Layer Cache
- Docker Registry Cache

Build Output 자체를 무조건 재사용하지 않고 Cache Key에 Toolchain·Lockfile·Build Script 변경을 반영합니다.

## 10. Quality Gate 순서
빠르고 결정적인 검사를 먼저 실행합니다.

```text
Compile / Static Analysis
  -> Unit Test
  -> Architecture Test
  -> Integration / Migration Test
  -> External API
  -> E2E
```

병렬화 가능한 Module Test는 병렬 실행하되 DB·CPU·Memory가 포화되어 오히려 느려지지 않게 Agent 자원에 맞춥니다.

## 11. Artifact Promotion
환경마다 Source를 다시 Build하지 않습니다.

```text
Commit A -> Digest X
Dev:  X
QA:   X
Prod: X
```

환경 차이는 Runtime Config로 주입합니다. QA 검증을 통과한 Digest가 Production에 그대로 배포되어야 합니다.

## 12. GitOps Commit
Pipeline이 `values.yaml`을 수정할 때 대상 환경과 서비스만 Surgical하게 변경합니다. Bot Commit에는 Source Commit, Image Digest와 Build URL을 기록합니다.

동시 Pipeline이 같은 Manifest를 수정할 수 있으므로 Pull/Rebase·Conflict 처리와 Environment별 직렬화를 설계합니다.

## 13. 배포 승인과 권한
- Dev는 Main 성공 시 자동
- QA는 Release Candidate Tag와 Test 결과
- Prod는 보호 Tag, 승인, 변경 기록

Jenkins Controller와 Build Agent의 Credential을 분리하고, Production ECR·Deploy Repository 권한은 승인 단계에서만 제공합니다.

## 14. Pipeline 장애
- Agent 소실: 재실행 가능한 Stage와 외부 Side Effect 확인
- ECR Push 중단: Digest 존재 여부 확인 후 재개
- Manifest Commit 성공·알림 실패: Git을 Source of Truth로 확인
- E2E 실패: Compose를 정리하기 전 Log 수집
- Jenkins 재시작: Durable Task와 중복 배포 방지

## 15. 운영 지표
- Queue 대기와 Build Duration
- Stage별 실패율
- Flaky Test 재실행 비율
- Commit-to-Deploy Lead Time
- Deployment Frequency와 Change Failure Rate
- Rollback·Recovery 시간

---

## 16. 배포 사례 적용 진단과 개선 과제

Jenkins Controller는 EKS Helm Release와 암호화 PVC를 사용하고 외부 Webhook용 별도 Ingress가 있습니다. Stateful 단일 Controller와 PVC는 Node·Volume 장애 시 Pipeline 전체의 단일 실패 지점이며, Public Webhook 경로가 UI 접근으로 확장되지 않게 검증해야 합니다.

Controller Configuration과 Job은 JCasC·Pipeline-as-Code로 복원 가능하게 하고 PVC Snapshot/Restore를 정기 시험합니다. Build는 Ephemeral Agent로 격리하고 Controller에는 Build Tool을 두지 않습니다. Webhook Ingress는 정확한 Path, Rate Limit, Provider Signature만 허용하고 Admin UI는 내부 CIDR·SSO로 제한합니다.

완료 기준은 새 Cluster에서 Code와 Backup만으로 Jenkins를 복원하고, Controller 재시작 중 중복 배포가 없으며, 외부에서 Webhook 이외 경로와 Credential에 접근할 수 없는 상태입니다.

---

# Reference
- [Jenkins Pipeline](https://www.jenkins.io/doc/book/pipeline/)
- [[Jib와 Gradle 컨테이너 이미지 빌드]]
- [[Postman Newman WireMock 테스트 전략]]
- [[Argo CD와 GitOps]]
