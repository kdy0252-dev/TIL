---
id: Maybe 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---
# Maybe 모나드 (Maybe Monad)

## 1. 존재하지 않을 수 있는 값

### 1-1. ""10억 달러의 실수"" (The Billion Dollar Mistake)
Tony Hoare가 고안한 `null` 참조는 소프트웨어 역사상 가장 값비싼 실수로 불립니다.
-   **NPE (NullPointerException)**: 런타임에 가장 빈번하게 발생하는 치명적 에러.
-   **방어 로직의 오염**: 비즈니스 로직 곳곳에 `if (obj != null)` 코드가 침투하여 가독성을 해침.
-   **의미의 모호성**: `null`이 "값이 없음"인지, "에러"인지, "초기화 안 됨"인지 명확하지 않음.

### 1-2. Maybe의 등장
**Maybe**는 값이 있을 수도 있고(`Just`/`Some`), 없을 수도 있는(`Nothing`/`None`) 상태를 캡슐화한 컨테이너입니다.
-   **Just(value)**: 유효한 값을 포함함.
-   **Nothing**: 값이 없음을 명시적으로 나타냄 (null을 대체).

Java 8부터 도입된 `java.util.Optional`이 바로 이 Maybe 모나드의 구현체입니다.

---

## 2. Maybe 구현해보기

`Optional`이 있지만, 모나드의 동작 원리(Map, FlatMap의 내부 구조)를 이해하기 위해 직접 구현해봅니다.
`Either<L, R>`이 두 개의 타입(Left/Right)을 다뤘다면, `Maybe<T>`는 하나의 타입과 '없음' 상태를 다룹니다.

```java
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.Consumer;

/**
 * Maybe 모나드 구현체 (Educational Purpose)
 * @param <T> 값의 타입
 */
public abstract class Maybe<T> {

    // --- Factory Methods ---

    public static <T> Maybe<T> just(T value) {
        return new Just<>(value);
    }

    public static <T> Maybe<T> nothing() {
        return (Maybe<T>) Nothing.INSTANCE;
    }

    public static <T> Maybe<T> ofNullable(T value) {
        return value == null ? nothing() : just(value);
    }

    // --- Abstract Methods ---

    public abstract boolean isEmpty();
    public abstract T get();

    // --- Monadic Operations ---

    /**
     * 값이 존재할 때만 함수를 적용하여 값을 변환합니다.
     * (Functor 의 map)
     */
    public <U> Maybe<U> map(Function<? super T, ? extends U> mapper) {
        if (isEmpty()) {
            return Maybe.nothing();
        } else {
            return Maybe.ofNullable(mapper.apply(get()));
        }
    }

    /**
     * 값이 존재할 때 함수를 적용하되, 함수가 Maybe를 반환할 때 중첩을 풉니다.
     * (Monad 의 bind)
     */
    public <U> Maybe<U> flatMap(Function<? super T, Maybe<U>> mapper) {
        if (isEmpty()) {
            return Maybe.nothing();
        } else {
            // map과 달리 재포장(wrapping)하지 않고 mapper의 결과를 그대로 반환
            return Objects.requireNonNull(mapper.apply(get()));
        }
    }

    /**
     * 조건이 맞지 않으면 Nothing으로 바꿉니다.
     */
    public Maybe<T> filter(Predicate<? super T> predicate) {
        if (isEmpty()) {
            return this;
        } else {
            return predicate.test(get()) ? this : Maybe.nothing();
        }
    }

    /**
     * 값이 없을 때 기본값을 반환합니다.
     */
    public T getOrElse(T other) {
        return isEmpty() ? other : get();
    }

    /**
     * 값이 있을 때만 특정 동작을 수행합니다.
     */
    public void ifPresent(Consumer<? super T> action) {
        if (!isEmpty()) {
            action.accept(get());
        }
    }

    // --- Implementations ---

    private static final class Just<T> extends Maybe<T> {
        private final T value;

        private Just(T value) {
            this.value = Objects.requireNonNull(value);
        }

        @Override public boolean isEmpty() { return false; }
        @Override public T get() { return value; }
        
        @Override public String toString() { return "Just(" + value + ")"; }
    }

    private static final class Nothing<T> extends Maybe<T> {
        private static final Nothing<?> INSTANCE = new Nothing<>();

        @Override public boolean isEmpty() { return true; }
        @Override public T get() { throw new NoSuchElementException("No value present"); }
        
        @Override public String toString() { return "Nothing"; }
    }
}
```

---

## 3. 실전 활용 시나리오: 중첩된 객체 탐색

### 3-1. 시나리오
보험 회사 시스템에서 사용자(`User`) -> 보험(`Insurance`) -> 보장명(`Name`)을 조회하려 합니다.
모든 단계는 `null`일 수 있습니다.

#### 0. 데이터 모델
```java
class User {
    Insurance insurance;
    public Insurance getInsurance() { return insurance; }
}
class Insurance {
    String name;
    public String getName() { return name; }
}
```

#### 1. 기존 방식 (Deep Null Check)
```java
public String getInsuranceNameLegacy(User user) {
    if (user != null) {
        Insurance insurance = user.getInsurance();
        if (insurance != null) {
            String name = insurance.getName();
            if (name != null) {
                return name;
            }
        }
    }
    return "Unknown";
}
```
**문제점**: 들여쓰기(Indent)가 깊어지고, 핵심 로직이 `null` 체크에 파묻힙니다.

#### 2. Maybe (Optional) 활용 방식
```java
import java.util.Optional; // Java의 표준 Maybe

public String getInsuranceNameModern(User user) {
    return Optional.ofNullable(user)
        // 1. User가 있으면 Insurance 추출 (없으면 이 단계에서 Empty 리턴되고 체인 종료)
        .map(User::getInsurance) 
        // 2. Insurance가 있으면 Name 추출
        .map(Insurance::getName)
        // 3. 최종적으로 값이 있으면 리턴, 없으면 기본값
        .orElse("Unknown");
}
```

#### 3. flatMap이 필요한 경우
만약 getter 메서드들이 이미 `Optional`을 반환하도록 설계되어 있다면 `flatMap`을 써야 합니다.

```java
class ModernUser {
    public Optional<ModernInsurance> getInsurance() { ... }
}
class ModernInsurance {
    public Optional<String> getName() { ... }
}

public String getNameDeep(ModernUser user) {
    return Optional.ofNullable(user)
        .flatMap(ModernUser::getInsurance) // map을 쓰면 Optional<Optional<Insurance>>가 됨
        .flatMap(ModernInsurance::getName)
        .orElse("Unknown");
}
```

---

## 4. Maybe 모나드의 의의

### 4-1. 제어 흐름의 추상화
-   `map`과 `flatMap`은 값이 **'있을 때만'** 함수를 실행한다는 제어 로직을 내포하고 있습니다.
-   개발자는 `null`인지 확인하는 조건문(If)을 작성하는 대신, **"값이 있다면 할 작업"**에만 집중하면 됩니다.

### 4-2. 타입 시스템을 통한 문서화
-   반환 타입이 `String`이면, 이 메서드는 절대 `null`을 주지 않음을 보장해야 합니다.
-   반환 타입이 `Optional<String>`이면, 사용자는 "아, 값이 없을 수도 있구나"를 즉시 인지하고 `orElse` 등으로 대비할 수 있습니다.

### 4-3. 팁 & 주의사항
1.  **필드에 Optional 사용 지양**: `Optional`은 직렬화(Serializable)를 구현하지 않았으므로, 클래스의 멤버 필드로 사용하는 것은 권장되지 않습니다 (주로 반환 타입용).
2.  **Collection에 Optional 사용 금지**: `Optional<List<Str>>`은 최악입니다. 빈 리스트는 그 자체로 '없음'을 의미하므로 그냥 `List`를 반환하세요.
3.  **Primitive Optional**: 성능이 중요하다면 `OptionalInt`, `OptionalLong` 등을 사용하세요 (Boxing 비용 제거).

---

## 5. 결론

| 특징 | Null Check | Maybe (Optional) |
| :--- | :--- | :--- |
| **안전성** | 개발자의 실수로 NPE 발생 가능 | 컴파일 타임에 처리 강제 가능 |
| **가독성** | 깊은 중첩 (Arrow code) | 메서드 체이닝 (Fluent API) |
| **의도 표현** | `null`의 의미 파악 모호 | 명시적인 '존재하지 않음' 표현 |

**Maybe 모나드**는 불확실성(Uncertainty)이라는 부수 효과(Side-effect)를 격리하고 제어하여, 더욱 견고하고 선언적인 코드를 작성하게 해주는 함수형 프로그래밍의 핵심 도구입니다.

# Reference
- [Java Optional Documentation](https://docs.oracle.com/javase/8/docs/api/java/util/Optional.html)
- [Tired of Null Pointer Exceptions? Consider Using Java SE 8's Optional!](https://www.oracle.com/technical-resources/articles/java/java8-optional.html)