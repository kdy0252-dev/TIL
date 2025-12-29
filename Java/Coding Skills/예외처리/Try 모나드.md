---
id: Try 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---
# Try 모나드 (Try Monad)

## 1. 예외를 감싸 안은 연산

### 1-1. 예외 처리의 딜레마
`Either`가 명시적인 에러 반환값(값으로서의 에러)을 다룬다면, **Try**는 **"던져진 예외(Exception)"**를 잡아내어 값으로 변환하는 데 특화된 모나드입니다.
-   **기존**: `try-catch` 블록은 문(Statement)이라서 값을 반환하지 못하고, 코드 흐름을 끊습니다.
-   **Try**: 예외가 발생할 수 있는 연산을 캡슐화하여, **성공(Success)** 또는 **실패(Failure)**라는 두 가지 상태를 가진 객체로 만듭니다.

Scala 언어의 `scala.util.Try`에서 유래했으며, Java에서는 비검사 예외(Unchecked Exception)가 많은 환경을 제어하기 위해 유용합니다.

---

## 2. Java에서의 Implementation

Java에서는 `Stream`이나 `Optional`과 달리 `Checked Exception` 처리가 까다롭습니다.
`Try` 모나드는 이러한 Checked Exception을 람다 내부에서 우아하게 처리하도록 도와줍니다.

```java
import java.util.Objects;
import java.util.function.Function;
import java.util.function.Consumer;
import java.util.function.Supplier;

/**
 * Try 모나드 구현체
 * @param <T> 성공 시 값의 타입
 */
public abstract class Try<T> {

    // --- Factory Methods ---

    public static <T> Try<T> of(CheckedSupplier<T> supplier) {
        try {
            return new Success<>(supplier.get());
        } catch (Throwable t) {
            return new Failure<>(t);
        }
    }

    public static <T> Try<T> success(T value) {
        return new Success<>(value);
    }

    public static <T> Try<T> failure(Throwable t) {
        return new Failure<>(t);
    }

    // --- Functional Interface for Checked Exception ---
    @FunctionalInterface
    public interface CheckedSupplier<T> {
        T get() throws Throwable;
    }
    
    @FunctionalInterface
    public interface CheckedFunction<T, R> {
        R apply(T t) throws Throwable;
    }

    // --- Abstract Methods ---

    public abstract boolean isSuccess();
    public abstract boolean isFailure();
    public abstract T get();
    public abstract Throwable getCause();

    // --- Monadic Operations ---

    /**
     * 성공한 경우 함수를 적용합니다. 함수 실행 중 예외가 발생하면 Failure로 전환됩니다.
     */
    public <U> Try<U> map(CheckedFunction<? super T, ? extends U> mapper) {
        if (isSuccess()) {
            try {
                return new Success<>(mapper.apply(get()));
            } catch (Throwable t) {
                return new Failure<>(t);
            }
        } else {
            return (Try<U>) this;
        }
    }

    /**
     * 성공한 경우 Try를 반환하는 함수를 적용합니다 (FlatMap).
     */
    public <U> Try<U> flatMap(CheckedFunction<? super T, Try<U>> mapper) {
        if (isSuccess()) {
            try {
                return mapper.apply(get());
            } catch (Throwable t) {
                return new Failure<>(t);
            }
        } else {
            return (Try<U>) this;
        }
    }

    /**
     * 실패했을 경우 복구 로직을 수행합니다.
     */
    public Try<T> recover(CheckedFunction<? super Throwable, ? extends T> recoverFunc) {
        if (isFailure()) {
            try {
                return new Success<>(recoverFunc.apply(getCause()));
            } catch (Throwable t) {
                return new Failure<>(t); // 복구 중 또 에러나면 새로운 Failure
            }
        } else {
            return this;
        }
    }

    /**
     * 값을 꺼내오되 실패 시 기본값을 반환합니다.
     */
    public T getOrElse(T other) {
        return isSuccess() ? get() : other;
    }

    // --- Implementations ---

    private static final class Success<T> extends Try<T> {
        private final T value;

        private Success(T value) {
            this.value = value;
        }

        @Override public boolean isSuccess() { return true; }
        @Override public boolean isFailure() { return false; }
        @Override public T get() { return value; }
        @Override public Throwable getCause() { throw new UnsupportedOperationException("Success has no cause"); }
        
        @Override public String toString() { return "Success(" + value + ")"; }
    }

    private static final class Failure<T> extends Try<T> {
        private final Throwable cause;

        private Failure(Throwable cause) {
            this.cause = Objects.requireNonNull(cause);
        }

        @Override public boolean isSuccess() { return false; }
        @Override public boolean isFailure() { return true; }
        @Override public T get() { throw new RuntimeException(cause); } // 혹은 SneakyThrows
        @Override public Throwable getCause() { return cause; }

        @Override public String toString() { return "Failure(" + cause + ")"; }
    }
}
```

---

## 3. 실전 활용 시나리오: JSON 파일 파싱

### 3-1. 시나리오
파일 경로를 받아 -> 파일을 읽고 -> JSON으로 파싱하여 -> 데이터를 추출한다.
IO 예외, 파싱 예외 등 다양한 예외가 발생할 수 있습니다.

#### 1. 기존 방식 (Nested Try-Catch)
```java
public Data readData(String path) {
    String content;
    try {
        content = Files.readString(Paths.get(path));
    } catch (IOException e) {
        throw new RuntimeException("Read Error", e);
    }

    try {
        return parseJson(content);
    } catch (JsonParseException e) {
        // 이미 파일을 읽었는데 파싱에서 터짐.. 로깅하고 null? 예외?
        System.err.println("Parse Error");
        return null; 
    }
}
```

#### 2. Try 활용 방식 (Pipeline)

```java
public class TryDemo {
    
    // 가정: 각 단계는 예외를 던질 수 있음
    public static String readFile(String path) throws IOException { ... }
    public static Data parseJson(String json) throws ParseException { ... }

    public static void main(String[] args) {
        String path = "config.json";

        Try<Data> result = Try.of(() -> readFile(path)) // 1. 파일 읽기 시도
            .map(json -> json.trim())             // 2. 간단한 가공 (String -> String)
            .flatMap(json -> Try.of(() -> parseJson(json))) // 3. 파싱 시도 (Try 중첩 풀기)
            .recover(ex -> {
                // 4. 에러 발생 시 복구 전략
                if (ex instanceof IOException) return new Data("Default Config");
                throw ex; // 알 수 없는 에러는 그대로 둠 (혹은 다른 처리)
            });

        // 결과 소비
        if (result.isSuccess()) {
            System.out.println("Loaded: " + result.get());
        } else {
            System.err.println("Failed: " + result.getCause().getMessage());
        }
    }
}
```

---

## 4. Try 모나드의 핵심 가치

### 4-1. 예외의 선형화
-   전통적인 예외 처리는 코드를 수직으로 분리시킵니다(Try 블록과 Catch 블록).
-   `Try`는 성공 경로(Happy Path)를 따라 코드를 수평으로(선형적으로) 작성하게 해 줍니다. 실패는 파이프라인 내부에서 조용히 전파됩니다.

### 4-2. 자원 해제 문제 (AutoCloseable)
-   `Try-with-resources` 구문과 결합하기 약간 까다로울 수 있습니다.
-   일부 구현체(Vavr)는 `Try.withResources(() -> ...)`를 지원하여 이 문제를 해결합니다.

### 4-3. Either vs Try
-   **Try**: 예외(Exception) 처리에 특화됨. `Failure`는 항상 `Throwable`을 가짐.
-   **Either**: 더 범용적임. `Left`가 꼭 예외일 필요 없음(String 에러 메시지, 에러 코드 Enum 등).

## 5. 결론

| 특징 | Try-Catch | Try Monad |
| :--- | :--- | :--- |
| **관점** | 에러 핸들링은 로직과 별개 | 에러도 비즈니스 흐름의 일부 |
| **람다** | Checked Exception 처리 불가 (Wrapper 필요) | 내부에서 Catch하여 Failure로 변환 |
| **합성** | 불가능 | `flatMap`으로 예외 유발 함수 합성 가능 |

Spring WebFlux나 CompletableFuture 같은 비동기 API에서도 `success/error` 채널이 분리된 스트림 처리를 하는데, 이는 `Try` 모나드의 사상과 맞닿아 있습니다.

# Reference
- [Vavr Library - Try](https://docs.vavr.io/#_try)
- [Scala Try Documentation](https://www.scala-lang.org/api/current/scala/util/Try.html)