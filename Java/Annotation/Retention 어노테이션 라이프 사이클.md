---
id: Retention 어노테이션 라이프 사이클
started: 2025-04-25
tags:
  - Java
  - ✅DONE
group: "[[Java Annotation]]"
---
# @Retention 어노테이션 라이프 사이클

Annotation은 Code에 붙이는 Metadata다. `@Retention`은 이 Metadata를 Source, Class File, Runtime 중 어디까지 보존할지 결정한다. “얼마나 오래 사는가”보다 **누가 Annotation을 읽어야 하는가**를 기준으로 선택한다.

- RetentionPolicy.SOURCE : 소스 코드(.java) 단계까지 어노테이션이 남아있는다. (가장 빨리 사라짐)
- RetentionPolicy.CLASS : 클래스 파일(.class) 단계까지 어노테이션이 남아있는다.
- RetentionPolicy.RUNTIME : Runtime Reflection으로 읽을 수 있도록 남는다.

## SOURCE

-   사실상 코드를 생성해주는 어노테이션이 대부분 여기에 해당한다.
-   Lombok의 `@Getter`, `@Setter` 와 같은 어노테이션은 컴파일 단계에서 class 파일을 생성할때 중간 코드를 생성 한 이후에 어노테이션이 사라진다.
-   주로 컴파일러에게 특정 작업을 지시하는 데 사용됩니다.
-   **컴파일 과정에서만 의미가 있으며, 생성된 바이트코드에는 포함되지 않습니다.**
-   **코드 분석 도구 또는 빌드 프로세스에서 활용될 수 있습니다.**

## CLASS

-   Lombok의 `@NonNull` 어노테이션이 Class 정책에 해당한다.
-   소스를 생성하는 관점에서는 Source 정책을 사용해도 되는데 메타데이터를 읽어 올 수도 없으면서 왜 Class 정책이 있는가?
-   IDE는 라이브러리를 현재 소스코드에서 사용하더라도 경고나 타입체킹을 해야하는데 이 라이브러리들은 실제 소스코드가 존재하는 것이 아닌 .class 파일만 존재한다. 즉 `@NonNull`같은 어노테이션을 사용해서 라이브러리를 빌드하더라도 인텔리제이와 같은 IDE에서 부가기능을 이용하려면 Class 레벨의 정책이 필요한 것이다.
-   컴파일러가 컴파일 시 특정 정보를 참조하거나, 바이트코드 조작에 사용될 수 있습니다.
-   **바이트코드에 포함되지만, 런타임에는 JVM에 의해 무시됩니다.**
-   **AOP(Aspect-Oriented Programming) 도구에서 활용되어, 컴파일된 클래스를 수정할 수 있습니다.**

## RUNTIME
-   런타임까지 어노테이션이 남아있다. 대부분의 Spring 어노테이션이 여기에 해당하는데 컴포넌트 스캔을 한다던지 스프링 컨텍스트에서 빈을 가져온다던지 하는 것들이 여기에 해당한다.
-   즉 런타임에 어노테이션이 남아있다는 것은 Reflection API 등을 사용하여 어노테이션 정보를 알수가 있다는 의미이다.
-   리플렉션을 사용하여 런타임에 어노테이션 정보를 읽고 활용할 수 있습니다.
-   **JVM에 의해 유지되며, 런타임 시에 리플렉션을 통해 접근 가능합니다.**
-   **DI(Dependency Injection) 컨테이너, ORM(Object-Relational Mapping) 프레임워크 등에서 널리 사용됩니다.**

## 직접 Annotation 만들기

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Audited {
    String action();
}
```

Runtime에서 Reflection으로 읽을 수 있다.

```java
Method method = PaymentService.class.getDeclaredMethod("pay");
Audited audited = method.getAnnotation(Audited.class);
if (audited != null) {
    System.out.println(audited.action());
}
```

같은 Annotation을 `CLASS`로 바꾸면 Class File에는 기록되지만 `getAnnotation()`으로는 얻을 수 없다. Bytecode Scanner나 Instrumentation Tool은 Class File을 직접 분석해 사용할 수 있다.

## Retention과 Target은 다른 역할이다

`@Target`은 Annotation을 붙일 수 있는 위치를 제한한다.

```text
TYPE: Class와 Interface
METHOD: Method
FIELD: Field
PARAMETER: Parameter
ANNOTATION_TYPE: 다른 Annotation
TYPE_USE: Generic과 Cast를 포함한 Type 사용 위치
```

`@Retention(RUNTIME)`이라고 모든 위치에 붙일 수 있는 것은 아니다. Target, Retention, Documented와 Inherited를 함께 설계한다.

## @Inherited의 제한

`@Inherited`는 Class에 붙은 Annotation을 Subclass가 `getAnnotation()`으로 조회할 때 상속하게 한다. Method와 Field Annotation에는 적용되지 않고 Interface 구현 관계에도 자동 적용되지 않는다. Spring은 자체 Annotation 탐색 규칙을 제공할 수 있으므로 순수 Java Reflection과 결과가 다를 수 있다.

## 어떤 정책을 선택할까

| 소비자 | 적합한 정책 | 예시 |
|---|---|---|
| Compiler·Source Generator | SOURCE | 정적 검사 Hint |
| Bytecode Tool·IDE | CLASS | Class File Metadata |
| Spring·Reflection 기반 Framework | RUNTIME | DI, AOP, ORM |

필요 이상으로 `RUNTIME`을 선택한다고 큰 성능 문제가 즉시 생기지는 않지만 Public Runtime 계약이 되고 Reflection 처리 범위가 넓어진다. 실제 소비 시점에 맞는 가장 짧은 정책을 선택한다.

## 기억할 점

Retention은 Annotation이 수행할 동작을 정의하지 않는다. Metadata를 어디까지 운반할지만 정한다. 실제 동작은 Compiler, Bytecode Tool 또는 Runtime Framework가 Annotation을 읽고 구현한다.

# Reference
