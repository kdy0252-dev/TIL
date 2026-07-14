---
id: jMolecules와 ArchUnit
started: 2026-05-14
tags:
  - ✅DONE
  - Java
  - Architecture
  - Testing
group:
  - "[[Java Third-Party]]"
---
# jMolecules와 ArchUnit: 아키텍처를 실행 가능한 규칙으로 만들기

## 1. 개요 (Overview)
아키텍처 문서만으로는 시간이 지날수록 코드가 설계 원칙에서 벗어나는 것을 막기 어렵습니다. **jMolecules**는 DDD와 Hexagonal Architecture의 역할을 어노테이션과 타입으로 표현하고, **ArchUnit**은 컴파일된 바이트코드를 분석하여 패키지·클래스 의존성 규칙을 테스트합니다.

두 도구를 결합하면 "이 클래스는 Outbound Adapter다"라는 의도를 코드에 표시하고, "Domain은 Adapter에 의존하면 안 된다"라는 규칙을 CI에서 자동 검증할 수 있습니다. 이를 **Architecture Fitness Function**이라고 합니다.

---

## 2. 역할 구분

| 도구 | 역할 | 결과 |
|---|---|---|
| jMolecules | DDD·Architecture의 의미를 코드에 표시 | 클래스의 설계 의도가 명시됨 |
| ArchUnit | 실제 의존성 방향과 패키지 규칙 검사 | 위반 시 테스트 실패 |
| Spring Modulith | 애플리케이션 모듈 경계와 공개 인터페이스 검사 | 모듈 간 결합 통제 |

jMolecules가 **어휘**를 제공한다면 ArchUnit은 그 어휘와 프로젝트 규칙을 **강제**합니다.

---

## 3. jMolecules 핵심 모델
jMolecules는 `@AggregateRoot`, `@Entity`, `@ValueObject`, `@Repository` 같은 DDD 개념과 `@Port`, `@Adapter`, `@PrimaryPort`, `@SecondaryAdapter` 같은 아키텍처 역할을 제공합니다.

```java
@AggregateRoot
public final class Booking {
    // 비즈니스 상태와 규칙
}

@Port
public interface SaveBookingOutPort {
    Booking save(Booking booking);
}

@Adapter
public final class BookingPersistenceAdapter implements SaveBookingOutPort {
    // JPA 구현
}
```

어노테이션을 붙였다는 사실만으로 경계가 보호되지는 않습니다. 실제 의존성을 검사하는 테스트가 함께 있어야 합니다.

---

## 4. ArchUnit 검증

```java
@AnalyzeClasses(packages = "com.example")
class HexagonalArchitectureTest {

    @ArchTest
    static final ArchRule domainMustNotDependOnAdapters = noClasses()
            .that().resideInAPackage("..application.domain..")
            .should().dependOnClassesThat()
            .resideInAnyPackage("..adapter..", "org.springframework..", "jakarta.persistence..");
}
```

프로젝트에서는 다음 규칙을 우선 검증해야 합니다.

- Domain Model이 Web·Persistence·Spring·JPA 타입에 의존하지 않습니다.
- Inbound Adapter는 `port.in`을 통해서만 애플리케이션을 호출합니다.
- Outbound Adapter는 `port.out`을 구현합니다.
- 다른 Vertical Slice의 내부 구현을 직접 참조하지 않습니다.
- 외부 Slice에는 명시적으로 공개한 `@NamedInterface`만 노출합니다.
- DTO, JPA Entity, Domain Model이 서로의 레이어로 누출되지 않습니다.

---

## 5. 실무 사례 적용 관점
이 사례는 핵심 업무 애플리케이션, `gateway`, `metrics`에 jMolecules DDD·Hexagonal 의존성을 적용하고, 별도의 Architecture Test Task에서 ArchUnit과 Spring Modulith 검사를 수행합니다.

```text
compile/test
  ├─ unit test
  ├─ integration test
  └─ architectureTest
       ├─ DDD 역할 검사
       ├─ Hexagonal 레이어 검사
       └─ Modulith 경계 검사
```

Architecture Test를 일반 단위 테스트와 분리하면 실패 원인이 명확해지고, CI에서 구조적 회귀를 독립적으로 확인할 수 있습니다.

---

## 6. 주의사항
- 패키지명만 검사하면 클래스의 실제 역할과 어긋날 수 있으므로 어노테이션과 의존성 규칙을 함께 사용합니다.
- 예외 패키지를 계속 추가하면 규칙이 무력화됩니다. 예외에는 만료 조건과 이유가 필요합니다.
- 모든 클래스를 억지로 분류하지 않습니다. 비즈니스 경계 보호에 가치가 있는 규칙부터 추가합니다.
- 테스트가 통과해도 런타임 결합이나 데이터 결합까지 자동으로 해결되는 것은 아닙니다.

---

## 7. DDD 어노테이션 의미
jMolecules 어노테이션은 Framework 기능을 추가하기보다 설계 의미를 표현합니다.

- `@AggregateRoot`: 일관성 경계의 진입점
- `@Entity`: Identity로 구분되는 Domain Object
- `@ValueObject`: 값으로 동등성을 판단하는 불변 객체
- `@Repository`: Aggregate 저장·복원 계약
- `@Service`: Entity에 자연스럽게 속하지 않는 Domain Operation

어노테이션을 붙였다고 Aggregate가 올바르게 설계되는 것은 아닙니다. Transaction 불변식과 참조 방향이 실제 의미와 일치해야 합니다.

## 8. Hexagonal 어노테이션
Primary Adapter·Port는 외부가 Application을 호출하는 방향, Secondary Port·Adapter는 Application이 외부 기술을 호출하는 방향을 나타냅니다.

```text
Web Adapter -> Primary Port -> Domain -> Secondary Port <- JPA Adapter
```

이 용어를 Package 구조와 Architecture Test에서 동일하게 사용합니다.

## 9. ArchUnit Layer Rule

```java
layeredArchitecture()
        .consideringOnlyDependenciesInLayers()
        .layer("Adapter").definedBy("..adapter..")
        .layer("Application").definedBy("..application..")
        .whereLayer("Application").mayNotAccessLayers("Adapter");
```

Layered Rule만으로 Vertical Slice 간 내부 참조를 막지 못하므로 Slice Rule을 별도로 둡니다.

## 10. Freeze와 Baseline
Legacy 위반이 많아 규칙을 즉시 적용할 수 없다면 현재 위반을 Baseline으로 Freeze하고 신규 위반만 막는 전략이 있습니다. Baseline이 영구 면죄부가 되지 않도록 감소 목표를 관리합니다.

## 11. Spring Modulith와 차이
ArchUnit은 임의의 Class Dependency 규칙을 표현하고, Spring Modulith는 Application Module, Named Interface와 Cycle을 이해합니다. jMolecules는 DDD·Architecture Role을 표현합니다.

세 도구의 검사를 중복시키기보다 역할별로 나눕니다.

## 12. Test 실패 메시지
규칙 이름과 `because()`에 아키텍처 이유를 기록합니다. "금지"만 표시하면 개발자가 올바른 대안을 찾기 어렵습니다.

```java
rule.because("다른 Slice는 공개된 UseCase 계약을 통해서만 호출해야 한다");
```

## 13. 허용 의존성
Java·표준 Annotation·공통 Value Object처럼 허용할 Package를 좁게 정의합니다. `..global..` 전체 허용은 Shared Kernel이 비대해지는 통로가 될 수 있습니다.

## 14. CI 분리
Architecture Test를 별도 Task로 실행하면 단위 Test 실패와 구조 위반을 구분할 수 있습니다. 다만 일반 `check`에도 Dependency를 걸어 우회되지 않게 합니다.

## 15. 도입 순서
1. Package 구조와 용어를 합의합니다.
2. Domain→Adapter 금지처럼 명확한 규칙부터 적용합니다.
3. Slice 내부 참조를 제한합니다.
4. Named Interface를 도입합니다.
5. Baseline 위반을 점진적으로 제거합니다.

## 16. 검증 대상이 아닌 것
Runtime Reflection, Configuration 값, SQL Join, Event 순서와 Network Policy는 Class Dependency Test만으로 검증되지 않습니다. Integration·Contract·Runtime Observability가 별도로 필요합니다.

---

## 17. 실무 사례 적용 진단과 개선 과제

ArchUnit과 Named Interface Test가 구조 회귀를 막지만 TODO와 예외가 존재하고 모든 Architecture Decision을 자동 검사하지는 못합니다. Test가 Package 이름에 과도하게 결합하면 올바른 Refactor도 큰 수정이 필요합니다.

핵심 규칙을 의존 방향, 공개 Contract, Domain의 Framework 독립성으로 구분하고 위반 Baseline은 감소만 허용합니다. 예외에는 이유·Owner·만료일을 둡니다. Modulith Verification과 ArchUnit의 중복은 줄이고 실패 메시지에 수정 방향을 넣습니다.

완료 기준은 신규 Slice가 별도 수작업 없이 규칙 대상이 되고, 예외 수가 Dashboard나 Report에서 보이며, 현재 TODO 규칙이 최종 Package 계약으로 전환된 상태입니다.

---

# Reference
- [jMolecules](https://github.com/xmolecules/jmolecules)
- [jMolecules Integrations](https://github.com/xmolecules/jmolecules-integrations)
- [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- [Spring Modulith Verification](https://docs.spring.io/spring-modulith/reference/verification.html)
