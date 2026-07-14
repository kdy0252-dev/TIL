---
id: Jib와 Gradle 컨테이너 이미지 빌드
started: 2026-06-11
tags:
  - ✅DONE
  - Docker
  - Gradle
  - CI-CD
group:
  - "[[Docker]]"
---
# Jib와 Gradle을 이용한 Java 컨테이너 이미지 빌드

## 1. 개요 (Overview)
**Jib**는 Dockerfile 없이 Java 애플리케이션을 OCI Image로 빌드하는 Google의 Build Plugin입니다. Class, Dependency, Resource를 별도 Layer로 구성하여 애플리케이션 코드만 변경됐을 때 작은 Layer만 다시 Push할 수 있습니다.

---

## 2. 일반 Docker Build와 차이

| 항목 | Dockerfile | Jib |
|---|---|---|
| 빌드 정의 | 명령형 Layer 작성 | Java Application 구조 기반 |
| Docker Daemon | 일반적으로 필요 | Registry 직접 Push 시 불필요 |
| Layer 최적화 | 작성자가 설계 | Dependency·Resource·Class 자동 분리 |
| 재현성 | Dockerfile 내용에 좌우 | Timestamp·Layer 구성을 일관되게 관리 |

복잡한 OS Package 설치나 Multi-stage Native Build가 필요하다면 Dockerfile이 더 적합합니다.

---

## 3. Gradle 구성

```kotlin
jib {
    from.image = "eclipse-temurin:25-jre"
    to.image = providers.environmentVariable("APP_IMAGE").get()
    container {
        ports = listOf("8080")
        creationTime.set("USE_CURRENT_TIMESTAMP")
    }
}
```

Base Image는 Digest로 고정하면 공급망과 재현성을 강화할 수 있습니다. JVM Option과 Container Memory Limit의 관계도 함께 검증해야 합니다.

---

## 4. 실무 사례의 빌드 흐름

```text
Gradle Verification
  -> BootJar
  -> jibDockerBuild
  -> Local Docker Image
  -> Docker Compose Integration Test
  -> Tag
  -> AWS ECR Push
  -> Deployment Manifest Update
```

이 사례는 핵심 업무 애플리케이션, `gateway`, `metrics` 이미지를 동일 Pipeline에서 만들고, Commit Hash와 Build Number 기반 Runtime Tag를 사용합니다. Integration Test에서 검증한 동일 이미지를 Registry로 보내야 Build와 Deploy 사이의 차이를 막을 수 있습니다.

---

## 5. 주의사항
- `latest`만 사용하지 말고 불변 Tag나 Digest를 사용합니다.
- Image에 Secret이나 환경별 설정 파일을 포함하지 않습니다.
- Root가 아닌 사용자로 실행합니다.
- Base Image CVE Scan과 정기 Rebuild를 수행합니다.
- Multi-architecture Build 시 Target Platform을 명시합니다.
- Container의 Graceful Shutdown 시간과 Kubernetes 종료 유예 시간을 맞춥니다.

---

## 6. Jib Layer 구조
Jib는 Java Application을 변경 빈도에 따라 Layer로 나눕니다.

```text
Base Image
  -> Dependencies
  -> Snapshot Dependencies
  -> Resources
  -> Classes
  -> Extra Directories
```

Application Class만 바뀌면 Dependency Layer는 Registry Cache를 재사용합니다. 큰 Fat Jar를 단일 Layer로 복사하는 방식보다 Push와 Pull 비용이 작아집니다.

Layer 효율을 유지하려면 자주 바뀌는 파일을 Dependency Layer나 Extra Directory에 섞지 않습니다.

## 7. Reproducible Build
같은 Source와 설정으로 같은 Image를 만들려면 다음 입력을 고정합니다.

- Base Image Digest
- Dependency Lock과 Version
- Java Toolchain
- 파일 Timestamp 정책
- Target Platform
- Jib Plugin Version

Tag는 바뀔 수 있지만 Digest는 Content를 식별합니다. 배포와 감사에는 최종 Digest를 함께 남깁니다.

## 8. Base Image 선택

| 방식 | 장점 | 주의점 |
|---|---|---|
| Full JRE | 진단 도구와 호환성 | Image가 큼 |
| Slim JRE | 균형 잡힌 크기 | OS Package가 제한됨 |
| Distroless | 작은 공격 표면 | Shell이 없어 현장 진단 방식 변경 |
| Custom jlink | 최소 Runtime | Module 구성·유지 비용 |

작은 Image가 항상 운영하기 좋은 Image는 아닙니다. JFR, Heap Dump, TLS Root CA, Font·Timezone 같은 Runtime 요구를 확인합니다.

## 9. JVM Container 설정
현대 JVM은 Container Memory와 CPU Limit을 인식하지만 Heap 외 Memory를 고려해야 합니다.

```text
Container Limit
  > Heap Max
  + Metaspace
  + Code Cache
  + Thread Stack
  + Direct Buffer
  + Native Memory
```

`MaxRAMPercentage`를 과도하게 높이면 OOMKill이 발생할 수 있습니다. Resource Limit과 실제 Peak를 기준으로 여유를 둡니다.

## 10. Supply Chain 보안
- 신뢰하는 Registry의 Base Image를 Digest로 고정합니다.
- SBOM을 생성하고 Image와 함께 보관합니다.
- CVE Scan은 Build 시점과 정기 재검사 모두 수행합니다.
- Image Signing과 Admission Policy를 검토합니다.
- Root Filesystem Read-only, Non-root User와 Capability Drop을 적용합니다.

Jib가 Dockerfile을 없애도 Base Image와 Dependency 공급망 책임은 사라지지 않습니다.

## 11. 사례 Pipeline 상세
이 사례는 먼저 모든 Module의 Test와 Architecture Check를 통과시킨 뒤 Jib Image를 Local Docker Daemon에 생성합니다. Compose E2E가 이 Image를 검증하고, 성공한 동일 Image에 Registry Tag를 붙여 ECR로 Push합니다.

```text
Source Commit A
  -> Image Digest X
  -> Compose에서 Digest X 검증
  -> ECR에 Digest X Push
  -> 배포 구성 저장소가 Digest X의 Tag 참조
```

검증 후 다시 Build하면 "테스트한 것"과 "배포한 것"이 달라질 수 있으므로 피합니다.

## 12. 실패 진단
- Base Image Pull 실패: Registry 인증, Rate Limit, Architecture 확인
- Main Class 오류: Jib Container Entry Point와 Spring Boot Main Class 확인
- Runtime ClassNotFound: Layer·Classpath와 Dependency Scope 확인
- ECR Push 실패: Repository, IAM, Token 만료 확인
- Local은 성공·EKS 실패: Platform Architecture, Runtime User, CA, Resource Limit 확인

## 13. 검증 체크리스트
- Image를 Non-root로 실행합니다.
- `/actuator/health`와 Graceful Shutdown을 실제 Container에서 검증합니다.
- Image Architecture가 EKS Node와 일치하는지 확인합니다.
- SBOM·Digest·Source Commit을 연결합니다.
- Base Image만 변경한 Rebuild도 E2E를 통과시키고 배포합니다.

---

## 14. 실무 사례 적용 진단과 개선 과제

Jib로 Docker Daemon 없이 Image를 만들 수 있지만 Base Image가 Tag에만 고정되거나 환경마다 재Build되면 재현성과 공급망 추적이 약해집니다.

Base Image를 Digest로 Pin하고 Commit SHA·Build URL·SBOM을 OCI Label/Artifact로 남깁니다. 취약점 Scan과 서명을 CI Gate에 넣고 QA에서 검증한 동일 Digest를 Prod로 승격합니다. JVM Memory 설정은 Pod Limit을 기준으로 Load Test합니다.

완료 기준은 같은 Source·Toolchain에서 동일 Layer Digest가 생성되고 Critical 취약점과 미서명 Image가 차단되며, 실행 중 Pod에서 Source Commit까지 역추적 가능한 상태입니다.

---

# Reference
- [Jib](https://github.com/GoogleContainerTools/jib)
- [Jib Gradle Plugin](https://github.com/GoogleContainerTools/jib/tree/master/jib-gradle-plugin)
- [[Docker 명령어]]
