---
id: Either 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---
# Either 모나드 (Either Monad)

## 1. 예외를 값으로 다루기

### 1-1. 전통적인 예외 처리의 한계
Java에서 전통적인 예외 처리(`try-catch`)는 다음과 같은 문제점을 가집니다.
1.  **제어 흐름의 단절**: 예외가 발생하면 코드의 실행 흐름이 점프(Jump)하여 로직을 파악하기 어렵습니다.
2.  **Side Effect**: 메서드 시그니처만으로는 어떤 예외가 던져질지 명확히 알기 어렵습니다(Unchecked Exception의 경우).
3.  **합성 불가**: 여러 연산을 함수형으로 파이프라인(`Streaming`)처럼 연결할 때, 예외 처리가 섞이면 코드가 지저분해집니다.

### 1-2. Either의 등장
**Either**는 두 가지 가능한 타입의 값 중 하나만 가질 수 있는 컨테이너입니다.
-   **Left**: 주로 '실패', '에러', '예외' 정보를 담습니다. (관례적으로 오른쪽이 올바른(Right) 쪽이라서, 왼쪽은 아닌 쪽)
-   **Right**: '성공', '정상적인 값'을 담습니다.

이를 통해 **"실패할 수도 있는 연산의 결과"** 자체를 **값(Value)**으로 리턴받아, 함수형 프로그래밍 방식으로 우아하게 처리할 수 있습니다. `java.util.Optional`이 "값이 있거나 없음"을 다룬다면, `Either`는 "값이 있거나 실패 이유가 있음"을 다룹니다.

---

## 2. Java에서의 Implementation

Java 표준 라이브러리(Stream API, Optional)는 `Either`를 제공하지 않습니다. (Vavr 같은 라이브러리에 존재).
학습을 위해 직접 POJO로 구현해 보며 내부 동작을 이해해 봅니다.

```java
import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.function.Function;
import java.util.function.Consumer;

/**
 * Either 모나드 구현체
 * @param <L> Left(에러) 타입
 * @param <R> Right(성공) 타입
 */
public abstract class Either<L, R> {

    // --- Factory Methods ---

    public static <L, R> Either<L, R> left(L value) {
        return new Left<>(value);
    }

    public static <L, R> Either<L, R> right(R value) {
        return new Right<>(value);
    }

    // --- Abstract Methods ---

    public abstract boolean isLeft();
    public abstract boolean isRight();
    public abstract L getLeft();
    public abstract R get();

    // --- Monadic Operations ---

    /**
     * 값을 변환합니다 (Right인 경우에만 적용).
     * Optional.map과 유사합니다.
     */
    public <T> Either<L, T> map(Function<? super R, ? extends T> mapper) {
        if (isRight()) {
            return Either.right(mapper.apply(get()));
        } else {
            // 타입 캐스팅: Left값은 그대로 유지하면서 타입만 L, T로 변경
            return (Either<L, T>) this;
        }
    }

    /**
     * 값을 변환하고 구조를 평탄화합니다 (Right인 경우).
     * Optional.flatMap과 유사합니다.
     */
    public <T> Either<L, T> flatMap(Function<? super R, Either<L, T>> mapper) {
        if (isRight()) {
            return mapper.apply(get());
        } else {
            return (Either<L, T>) this;
        }
    }

    /**
     * Left일 때와 Right일 때의 처리를 각각 정의하여 최종 값을 도출합니다.
     * 패턴 매칭과 유사한 효과를 냅니다.
     */
    public <T> T fold(Function<? super L, ? extends T> leftMapper, 
                      Function<? super R, ? extends T> rightMapper) {
        if (isRight()) {
            return rightMapper.apply(get());
        } else {
            return leftMapper.apply(getLeft());
        }
    }

    /**
     * 성공(Right) 시 값을 반환하고, 실패(Left) 시 대체값을 반환합니다.
     */
    public R getOrElse(R other) {
        return isRight() ? get() : other;
    }
    
    /**
     * Right일 때만 특정 동작(소비)을 수행합니다.
     */
    public void ifRight(Consumer<? super R> action) {
        if (isRight()) {
            action.accept(get());
        }
    }

    // --- Implementations ---

    private static final class Left<L, R> extends Either<L, R> {
        private final L value;

        private Left(L value) {
            this.value = Objects.requireNonNull(value);
        }

        @Override public boolean isLeft() { return true; }
        @Override public boolean isRight() { return false; }
        @Override public L getLeft() { return value; }
        @Override public R get() { throw new NoSuchElementException("Is Left: " + value); }
        
        @Override public String toString() { return "Left(" + value + ")"; }
    }

    private static final class Right<L, R> extends Either<L, R> {
        private final R value;

        private Right(R value) {
            this.value = Objects.requireNonNull(value);
        }

        @Override public boolean isLeft() { return false; }
        @Override public boolean isRight() { return true; }
        @Override public L getLeft() { throw new NoSuchElementException("Is Right: " + value); }
        @Override public R get() { return value; }

        @Override public String toString() { return "Right(" + value + ")"; }
    }
}
```

---

## 3. 실전 활용 시나리오

### 3-1. 시나리오: 사용자 입력 파싱 및 DB 조회
상황: 문자열 ID를 받아서 -> 정수로 파싱하고 -> DB에서 유저를 찾고 -> 이름을 반환한다.
이 과정에서 **파싱 에러**와 **DB 조회 실패**가 발생할 수 있다.

#### 0. 준비 코드 (가정)
```java
record User(int id, String name) {}

class Repository {
    // DB 조회 예시: 짝수 ID만 존재한다고 가정
    public static Either<String, User> findById(int id) {
        if (id % 2 == 0) return Either.right(new User(id, "User" + id));
        else return Either.left("User not found with id: " + id);
    }
}
```

#### 1. 기존 방식 (Try-Catch 지옥)
```java
public String getUserDateLegacy(String inputId) {
    try {
        int id = Integer.parseInt(inputId); // 예외 발생 가능 1
        User user = null;
        try {
            // 이 방식은 예외를 던지는 대신 null 체크를 하거나 커스텀 예외를 써야 함
            // 여기선 예시를 위해 생략
        } catch (Exception e) {
            return "DB Error";
        }
        // ... 코드가 깊어지고 지저분함
        return user.name();
    } catch (NumberFormatException e) {
        return "Invalid ID format";
    }
}
```

#### 2. Either 활용 방식 (Chaining)
```java
public class EitherDemo {
    
    // 파싱 로직을 Either로 감싸기
    public static Either<String, Integer> parseId(String input) {
        try {
            return Either.right(Integer.parseInt(input));
        } catch (NumberFormatException e) {
            return Either.left("Invalid Input: not a number");
        }
    }

    public static void main(String[] args) {
        String input = "124";

        // 파이프라인형 처리
        String result = parseId(input)
            // 1. 파싱 성공 시 DB 조회 (flatMap: Either -> Either)
            .flatMap(id -> Repository.findById(id))
            // 2. DB 조회 성공 시 이름 추출 (map: User -> String)
            .map(User::name)
            // 3. 최종 처리 (fold: 에러 처리 vs 성공 처리)
            .fold(
                error -> "[ERROR] " + error,
                name -> "[SUCCESS] User name is " + name
            );

        System.out.println(result);
    }
}
```

**[실행 결과 시뮬레이션]**
1. `input = "124"` (성공)
   - parseId -> Right(124)
   - findById(124) -> Right(User(124, "User124"))
   - map -> Right("User124")
   - fold -> "[SUCCESS] User name is User124"

2. `input = "abc"` (파싱 실패)
   - parseId -> Left("Invalid Input...")
   - flatMap -> 실행 안됨 (그대로 Left 전파)
   - map -> 실행 안됨 (그대로 Left 전파)
   - fold -> "[ERROR] Invalid Input: not a number"

3. `input = "123"` (DB 없음)
   - parseId -> Right(123)
   - findById(123) -> Left("User not found...")
   - map -> 실행 안됨 (그대로 Left 전파)
   - fold -> "[ERROR] User not found with id: 123"

---

## 4. 모나드(Monad) 관점에서의 해석

`Either`가 모나드라고 불리는 이유는 다음 조건(모나드 법칙)을 대부분 만족하며 동작하기 때문입니다.

1.  **Unit (Return)**: 값을 모나드 컨테이너로 감싸는 방법 (`Either.right(v)`).
2.  **Bind (FlatMap)**: `M<T>` 타입과 `T -> M<U>` 함수를 받아 `M<U>`를 반환하는 연산 (`flatMap`). 
    -   이 `bind` 연산을 통해 "실패할 수 있는 연산들"을 연속적으로 연결할 수 있습니다.
    -   중간에 하나라도 `Left`가 발생하면, 이후의 연산(`map`, `flatMap`)들은 모두 무시되고 `Left`가 끝까지 전달되는 **"Short-circuit"** 효과가 발생합니다.

## 5. 결론 및 요약

| 특징 | Try-Catch | Either Monad |
| :--- | :--- | :--- |
| **흐름 제어** | 예외 발생 시 점프, 코드 블록 분리 | 데이터 흐름처럼 선형적으로 처리 |
| **타입 안정성** | Checked Exception 외엔 명시 안 됨 | 반환 타입에 에러 가능성이 명시됨 (`Either<Err, User>`) |
| **합성** | 어렵음 (중첩 try-catch) | 쉬움 (`flatMap` 체이닝) |
| **가독성** | 비즈니스 로직과 에러 처리가 섞임 | 비즈니스 로직(Happy Path)과 에러 처리(fold)가 분리됨 |

Java에서는 `Stream`이나 `Optional`을 통해 모나드적 사고에 익숙해져 있습니다. 비즈니스 로직에서 "실패 이유"가 중요할 때는 `Optional` 대신 `Either`를 직접 구현하거나 라이브러리를 사용하여 처리하면, 훨씬 견고하고 유지보수하기 쉬운 코드를 작성할 수 있습니다.

# Reference
- [Vavr Library - Either](https://docs.vavr.io/#_either)
- [Monad in Java](https://dzone.com/articles/functor-and-monad-examples-in-java)