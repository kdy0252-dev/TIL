---
id: Gradle Convention Plugin
started: 2026-05-12
tags:
  - ✅DONE
  - Gradle
  - Build
group:
  - "[[Java Third-Party]]"
---
# Gradle Convention Plugin과 Version Catalog

## 1. 개요 (Overview)
Multi-module Project에서 각 `build.gradle.kts`가 Java Version, Test, Checkstyle, Spring Starter와 Compiler Option을 반복하면 Module마다 설정이 달라집니다. **Convention Plugin**은 조직의 Build 규칙을 Plugin으로 캡슐화하고 각 Module은 필요한 역할만 선언하게 합니다.

```kotlin
plugins {
    id("io.example.spring-web")
    id("io.example.checkstyle")
    id("io.example.architecture")
}
```

---

## 2. 구성 요소

| 구성 | 역할 |
|---|---|
| `build-logic` Included Build | Convention Plugin을 독립 Build로 관리 |
| Version Catalog | Version과 Library Alias 중앙 관리 |
| Kotlin DSL | Type-safe Build Script |
| Toolchain | Module 전체의 Java Version 통일 |
| Convention Plugin | 공통 Dependency와 Task 설정 캡슐화 |

---

## 3. Composite Build

```kotlin
// settings.gradle.kts
includeBuild("build-logic")
```

`buildSrc`와 달리 Included Build는 명시적인 경계를 가지며 독립적인 Build Cache와 Dependency 관리가 가능합니다.

---

## 4. Version Catalog

```toml
[versions]
springBoot = "4.0.6"

[libraries]
spring-boot-dependencies-bom = {
  module = "org.springframework.boot:spring-boot-dependencies",
  version.ref = "springBoot"
}
```

Version Catalog는 Dependency를 선언하기 쉽게 만들지만 Version 정합성을 자동 보장하는 BOM의 대체품은 아닙니다. Spring과 AWS SDK처럼 연관 Library는 BOM과 함께 사용합니다.

---

## 5. 실무 사례 적용 관점
이 사례의 Module은 Web, Data, Redis, Quartz, Modulith, Testcontainers, Error Prone, OpenRewrite 같은 역할 Plugin을 조합합니다.

```text
com.example.platform.java
  ├─ Java 25 Toolchain
  ├─ JUnit Platform
  └─ AssertJ

com.example.platform.spring-data
  ├─ JPA / JDBC
  ├─ Liquibase
  └─ PostgreSQL
```

Module Build Script는 업무 Module의 차이만 표현하고, 전사 규칙은 `build-logic`에서 관리합니다.

---

## 6. 설계 원칙
- 거대한 하나의 Plugin보다 기능별 작은 Plugin을 조합합니다.
- 모든 Module에 불필요한 Dependency를 강제로 넣지 않습니다.
- Plugin 이름은 구현 기술보다 역할을 드러냅니다.
- Build Logic 변경은 전체 Module에 영향을 주므로 Test와 Review를 강화합니다.
- Version Upgrade와 Feature Change를 가능한 한 분리합니다.

---

## 7. Convention Plugin 유형
- Precompiled Script Plugin: Kotlin DSL 파일로 빠르게 구성
- Binary Plugin: Kotlin Class로 복잡한 Logic과 Test 구현

단순 Dependency·Task 설정은 Script Plugin, 조건 분기와 재사용 API가 많으면 Binary Plugin이 적합합니다.

## 8. Plugin 계층

```text
java convention
  -> java-library
  -> spring-app
      -> spring-web
      -> spring-data
      -> spring-modulith
```

하위 Plugin이 어떤 기본 Plugin과 Dependency를 암묵적으로 적용하는지 문서화합니다. 순환 적용과 너무 깊은 계층을 피합니다.

## 9. Lazy Configuration
Gradle Configuration Cache와 Task Avoidance를 위해 `tasks.register`, `tasks.named`, Provider API를 사용합니다. Configuration 단계에서 Environment를 즉시 읽거나 외부 Process를 실행하지 않습니다.

## 10. Dependency 역할
- `api`: Consumer Compile Classpath에 노출
- `implementation`: Module 내부 구현
- `runtimeOnly`: 실행 시 필요
- `compileOnly`: 컴파일만 필요
- `annotationProcessor`: Code Generation
- `testImplementation`: Test 전용

Convention Plugin이 모든 Library를 `api`로 노출하면 Module 경계와 Build 성능이 나빠집니다.

## 11. BOM과 Version Catalog
Catalog Alias는 좌표와 Version 접근을 단순화하고, BOM은 연관 Dependency Version 정합성을 보장합니다. 둘을 함께 사용하되 같은 Version을 여러 위치에서 중복 관리하지 않습니다.

## 12. Custom Source Set
이 사례의 External API Test처럼 별도 Source Set을 만들면 Credential이 필요한 Test를 일반 Build에서 분리할 수 있습니다.

```text
src/test            -> 기본·통합 Test
src/externalApiTest -> 실제 외부 API
```

Classpath 상속, Checkstyle와 실행 Tag를 명시합니다.

## 13. Test Task 분리
Unit, Integration, Migration, Architecture Test를 별도 Task로 두면 병렬성과 실패 원인이 명확합니다. 같은 Test가 두 Task에서 중복 실행되지 않게 Filter를 검증합니다.

## 14. Configuration Cache
Plugin이 Project 객체를 Execution 단계에 Capture하거나 Task에서 즉시 File System을 읽으면 Cache 호환성이 깨질 수 있습니다. 호환되지 않는 Jib Docker Task처럼 이유가 명확한 Task만 제한적으로 제외합니다.

## 15. Build Logic Test
Gradle TestKit으로 Sample Project에 Plugin을 적용하고 다음을 검증합니다.

- 필요한 Plugin·Dependency 적용
- Java Toolchain과 Compiler Option
- Task Dependency
- 잘못된 설정의 명확한 오류
- Configuration Cache 호환성

## 16. 변경 영향 관리
Build Logic 변경은 모든 Module에 전파됩니다. Plugin Upgrade와 업무 변경을 분리하고, 전체 Module Compile·Test를 수행합니다. Deprecated Gradle API는 다음 Major Upgrade 전에 제거합니다.

---

## 17. 실무 사례 적용 진단과 개선 과제

Multi-module Convention Plugin이 공통 Toolchain과 Test를 제공하지만 Plugin 간 책임과 적용 순서가 암묵적이면 Module별 편차와 Configuration Cache 저하가 생깁니다.

Base Java, Spring Application, Library, Integration Test Convention을 분리하고 Lazy Configuration API를 사용합니다. Module이 임의로 Version·Compiler Flag를 덮어쓰지 못하게 Version Catalog/BOM을 단일화하며 Plugin TestKit으로 생성 Task와 설정을 검증합니다.

완료 기준은 새 Module이 최소 선언으로 동일 Quality Gate를 받고, Configuration Cache가 재사용되며, Dependency·Toolchain Drift Report에 예외가 없는 상태입니다.

---

# Reference
- [Gradle Sharing Build Logic](https://docs.gradle.org/current/userguide/sharing_build_logic_between_subprojects.html)
- [Gradle Version Catalogs](https://docs.gradle.org/current/userguide/version_catalogs.html)
- [Gradle Composite Builds](https://docs.gradle.org/current/userguide/composite_builds.html)
- [[Gradle 동작 원리]]
