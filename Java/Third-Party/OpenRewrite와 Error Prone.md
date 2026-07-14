---
id: OpenRewrite와 Error Prone
started: 2026-05-14
tags:
  - ✅DONE
  - Java
  - Static-Analysis
  - Refactoring
group:
  - "[[Java Third-Party]]"
---
# OpenRewrite와 Error Prone: 자동 리팩터링과 컴파일 정적 분석

## 1. 개요 (Overview)
**OpenRewrite**와 **Error Prone**은 둘 다 코드 품질을 높이지만 동작 목적이 다릅니다.

| 도구 | 질문 | 동작 |
|---|---|---|
| OpenRewrite | 기존 코드를 어떤 형태로 바꿀 것인가? | Recipe 기반 소스 변환 |
| Error Prone | 이 코드에 결함 가능성이 있는가? | javac Plugin 기반 진단 |
| Checkstyle | 프로젝트 형식을 지켰는가? | Style·구조 규칙 검사 |

---

## 2. OpenRewrite
OpenRewrite는 Java Source를 Lossless Semantic Tree로 분석하고 Recipe에 따라 안전한 변경을 수행합니다.

```kotlin
rewrite {
    activeRecipe("org.openrewrite.java.RemoveUnusedImports")
    activeRecipe("org.openrewrite.java.migrate.UpgradeToJava21")
    activeRecipe("org.openrewrite.staticanalysis.CommonStaticAnalysis")
}
```

대표 용도는 다음과 같습니다.

- JDK·Spring Boot·Jakarta Migration
- Deprecated API 교체
- Test Framework와 Assertion 스타일 변환
- Import·Format·일반 정적 분석 정리
- 대규모 Repository의 반복 수정

Recipe 적용 전후에는 반드시 Diff Review와 Test가 필요합니다. 자동 변환은 비즈니스 의미를 알지 못합니다.

---

## 3. Error Prone
Error Prone은 javac의 Type 정보를 사용하여 일반 Compiler Warning보다 의미 있는 결함 패턴을 탐지합니다.

```kotlin
tasks.withType<JavaCompile>().configureEach {
    options.errorprone {
        disableWarningsInGeneratedCode.set(true)
        allErrorsAsWarnings.set(false)
    }
    options.compilerArgs.addAll(listOf("-Xlint:all", "-Werror"))
}
```

잘못된 `equals`, 무시된 반환값, 잘못된 Optional 사용, 동시성 API 오용 같은 문제를 빌드 시점에 발견할 수 있습니다.

---

## 4. 실무 사례 적용 관점
이 사례는 공통 Gradle Convention Plugin으로 두 도구를 여러 Module에 일관되게 적용합니다.

```text
Developer Change
  -> OpenRewrite Recipe로 기계적 개선
  -> javac + Error Prone으로 결함 검사
  -> Checkstyle로 형식 검사
  -> Test + Architecture Test
```

생성 코드에는 Error Prone 경고를 비활성화하고, 직접 작성한 코드에는 Warning을 Build Failure로 다루어 품질 기준을 통일합니다.

---

## 5. 운영 원칙
- OpenRewrite 결과를 한 번에 대규모 Feature 변경과 섞지 않습니다.
- Recipe Version과 활성 Recipe 목록을 Version Control에 둡니다.
- Error Prone 규칙 비활성화에는 구체적인 이유를 기록합니다.
- Suppression은 가장 작은 Scope에 적용합니다.
- 신규 규칙 도입 시 기존 위반을 Baseline으로 관리하거나 별도 정리 Commit을 만듭니다.

---

## 6. OpenRewrite Recipe 구성
Recipe는 작은 변환을 조합한 선언적 목록입니다.

```yaml
type: specs.openrewrite.org/v1beta/recipe
name: io.example.Modernize
recipeList:
  - org.openrewrite.java.RemoveUnusedImports
  - org.openrewrite.java.migrate.UpgradeToJava21
```

검색 조건과 변환을 분리할 수 있고, Data Table로 어떤 파일이 왜 변경됐는지 분석할 수 있습니다.

## 7. Semantic Tree의 장점
문자열 치환과 달리 Type Attribution을 사용해 같은 이름의 다른 Method를 구분합니다. Import, Generic Type과 Method Overload를 이해한 상태에서 변환합니다.

다만 Build가 정상적으로 Type을 해석할 수 있어야 하며 누락된 Dependency나 생성 코드가 있으면 일부 Recipe 정확도가 떨어질 수 있습니다.

## 8. 대규모 Migration 전략
1. Recipe만 추가하고 Dry Run 결과를 확인합니다.
2. Format·Import 같은 저위험 변경을 먼저 적용합니다.
3. API Migration을 작은 묶음으로 나눕니다.
4. Compile·Test·Architecture Test를 실행합니다.
5. 수동 의미 검토가 필요한 변경을 별도 처리합니다.

Feature 개발과 수천 파일의 자동 변경을 같은 Commit에 섞지 않습니다.

## 9. Error Prone Bug Pattern
Error Prone Check는 Error·Warning·Suggestion 심각도를 가집니다. 프로젝트 정책으로 Warning을 Error로 승격할 수 있습니다.

대표 범주는 Null·Equality, 반환값 무시, 동시성, Time API, Collection 오용과 Test 오류입니다.

## 10. Suppression

```java
@SuppressWarnings("FutureReturnValueIgnored")
void fireAndForget() {
    executor.submit(task);
}
```

Suppression은 Check 이름과 의도가 드러나게 최소 Scope에 둡니다. 전체 Package나 Build에서 비활성화하기 전에 API 설계를 바꿀 수 있는지 검토합니다.

## 11. Generated Code
MapStruct, QueryDSL 같은 생성 코드는 경고를 직접 수정할 수 없습니다. Generated Directory를 제외하되 생성기 설정이나 Source 선언의 문제는 숨기지 않습니다.

## 12. Checkstyle과 역할 분리
- Checkstyle: 형식, Import, Naming, 줄 길이
- Error Prone: Compiler Type 기반 결함
- ArchUnit: 구조적 의존성
- OpenRewrite: 자동 변환

같은 규칙을 여러 도구에 중복 정의하면 오류 메시지와 수정 방식이 혼란스러워집니다.

## 13. CI 운영
OpenRewrite 자동 적용 Task는 일반 Build에서 Source를 몰래 변경하지 않게 분리합니다. Error Prone은 Compile Gate로 항상 실행합니다.

Recipe Upgrade로 대규모 Diff가 생길 수 있으므로 Tool Version과 Recipe BOM을 고정합니다.

## 14. 검증 체크리스트
- Rewrite Dry Run 결과에 업무 로직 변경이 없는지 확인합니다.
- Compile과 전체 Test를 실행합니다.
- Suppression 증가를 Review합니다.
- 비활성화된 Check 목록과 이유를 관리합니다.
- JDK·Spring Upgrade마다 기존 Custom Recipe 호환성을 확인합니다.

---

## 15. 실무 사례 적용 진단과 개선 과제

도구 의존성은 있으나 Recipe 적용 범위, Suppression 정책, CI Gate가 불명확하면 설치만 된 기술이 됩니다. 대규모 자동 수정은 프로젝트 고유 Architecture 규칙을 훼손할 수도 있습니다.

먼저 Dry-run Report를 저장하고 안전한 Recipe를 Module별 작은 Commit으로 적용합니다. Error Prone 경고는 신규 위반 차단부터 시작해 Baseline을 줄이며 Generated Source와 Lombok 호환을 분리합니다. Rewrite 후 Compile·Architecture·Integration Test를 필수로 실행합니다.

완료 기준은 CI가 신규 Critical Warning을 차단하고 Recipe Version과 결과 Diff가 재현 가능하며, Suppression마다 이유와 범위가 명시된 상태입니다.

---

# Reference
- [OpenRewrite Documentation](https://docs.openrewrite.org/)
- [Error Prone](https://errorprone.info/)
- [Checkstyle](https://checkstyle.org/)
