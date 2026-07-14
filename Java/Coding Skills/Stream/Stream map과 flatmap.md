---
id: Stream map과 flatmap
started: 2025-04-25
tags:
  - Java
  - ✅DONE
group: "[[Java Coding Skills]]"
---
# Stream map과 flatmap

`map`과 `flatMap`의 차이는 “배열을 펼친다”는 문법보다 **하나의 입력이 몇 개의 출력이 되는가**로 이해하면 쉽다.

```text
map:     1 -> 1 변환
flatMap: 1 -> 0..N 변환을 한 Stream으로 연결
```
## Map이란?
Stream의 `map()` 메서드는 스트림의 각 요소에 함수를 적용하여 새로운 스트림을 생성하는 중간 연산(Intermediate Operation)이다. 각 요소를 변환하는 데 사용된다.
```java title="map() 정의"
<R> Stream<R> map(Function<? super T, ? extends R> mapper);
```
*   **파라미터:** `Function<? super T, ? extends R> mapper`
    *   `T`: 스트림 요소의 타입
    *   `R`: 새로운 스트림 요소의 타입
*   **리턴 타입:** `Stream<R>`
**동작 방식:**
1.  스트림의 각 요소를 순회한다.
2.  각 요소에 `mapper` 함수를 적용하여 새로운 값으로 변환한다.
3.  변환된 값들을 요소로 하는 새로운 스트림을 생성한다.
## FlatMap이란?
Stream의 `flatMap()` 메서드는 스트림의 각 요소에 함수를 적용하여 새로운 스트림을 생성한 후, 생성된 모든 스트림을 하나의 스트림으로 평탄화(Flatten)하는 중간 연산이다. 중첩된 스트림을 하나의 스트림으로 합치는 데 사용된다.
```java title="flatMap() 정의"
<R> Stream<R> flatMap(Function<? super T, ? extends Stream<? extends R>> mapper);
```
*   **파라미터:** `Function<? super T, ? extends Stream<? extends R>> mapper`
    *   `T`: 스트림 요소의 타입
    *   `R`: 새로운 스트림 요소의 타입
*   **리턴 타입:** `Stream<R>`
**동작 방식:**
1.  스트림의 각 요소를 순회한다.
2.  각 요소에 `mapper` 함수를 적용하여 새로운 스트림을 생성한다.
3.  생성된 모든 스트림을 하나의 스트림으로 합쳐서 평탄화한다.
## Map 사용 예시
```java title="map 사용 예시"
List<String> names = Arrays.asList("Alice", "Bob", "Charlie");
List<String> upperNames = names.stream()
            .map(String::toUpperCase)
            .toList();
System.out.println(upperNames); // [ALICE, BOB, CHARLIE]
```
*   `names` 리스트의 각 요소를 대문자로 변환하여 새로운 리스트 `upperNames`를 생성한다.
*   `String::toUpperCase`는 각 문자열을 대문자로 변환하는 메서드 레퍼런스이다.
## FlatMap 사용 예시
```java title="FlatMap 사용 예시"
List<String> sentences = Arrays.asList("I love Java", "I love coding");
List<String> words = sentences.stream()
            .map(s -> s.split(" "))  // Stream<String[]> 생성
            .flatMap(Arrays::stream) // Stream<String[]> → Stream<String> 으로 평탄화
            .toList();
System.out.println(words); // [I, love, Java, I, love, coding]
```
*   `sentences` 리스트의 각 문장을 공백을 기준으로 분리하여 단어 스트림을 생성한다.
*   `s -> s.split(" ")`는 각 문장을 단어 배열로 변환하는 람다 표현식이다.
*   `Arrays::stream`은 배열을 스트림으로 변환하는 메서드 레퍼런스이다.
*   `flatMap()`을 사용하여 각 문장에서 생성된 단어 스트림들을 하나의 스트림으로 합쳐서 평탄화한다.
## Map과 FlatMap의 차이점

| 구분    | Map                                 | FlatMap                         |
| ----- | ----------------------------------- | ------------------------------- |
| 목적    | 스트림의 각 요소를 변환                       | 스트림의 각 요소를 스트림으로 변환 후 평탄화       |
| 반환 타입 | Stream\<R>                          | Stream\<R>                      |
| 함수    | Function\<T, R>                     | Function\<T, Stream\<R>>        |
| 사용 시점 | 각 요소를 1:1로 변환할 때                    | 각 요소를 1:N으로 변환 후 하나의 스트림으로 합칠 때 |
| 결과    | 스트림의 요소 수가 변하지 않음                   | 스트림의 요소 수가 변할 수 있음              |
| 중첩 구조 | 중첩 구조가 발생할 수 있음 (Stream<Stream<T>>) | 중첩 구조가 발생하지 않음 (Stream<T>)      |

`map`도 결과 요소 수가 항상 같다고 단정할 수는 없다. Mapper 하나가 `null`을 반환해도 요소 자체는 남지만 이후 `filter`가 제거할 수 있고, Infinite Stream처럼 전체 크기를 정의하기 어려운 경우도 있다. 핵심 계약은 각 입력 요소를 결과 하나로 Mapping한다는 점이다.

## 중첩 Collection 펼치기

```java
record Order(List<OrderLine> lines) {}

List<OrderLine> allLines = orders.stream()
    .flatMap(order -> order.lines().stream())
    .toList();
```

`map(Order::lines)`만 사용하면 `Stream<List<OrderLine>>`이 된다. 각 List를 다시 순회하려면 중첩 Loop가 필요하다. `flatMap`은 내부 Stream의 수명도 관리하고 모든 요소를 외부 Stream으로 연결한다.

## 0개로 변환하는 flatMap

Optional을 Stream으로 바꾸면 값이 없는 입력을 자연스럽게 제거할 수 있다.

```java
List<Member> members = memberIds.stream()
    .map(repository::findById)  // Stream<Optional<Member>>
    .flatMap(Optional::stream)  // Stream<Member>
    .toList();
```

다만 이 예제는 ID마다 Query가 발생할 수 있다. 표현의 모양과 실행 비용을 별도로 판단한다.

## flatMap과 자원

File Line Stream처럼 닫아야 하는 Resource를 Mapper에서 열면 수명 관리가 복잡해진다.

```java
try (Stream<String> lines = Files.lines(path)) {
    return lines.flatMap(this::parseWords).toList();
}
```

여러 File을 `flatMap(Files::lines)`으로 열면 동시에 열린 Resource와 예외 처리를 주의해야 한다. Stream이 Lazy하므로 Terminal Operation이 끝날 때까지 Resource가 살아 있어야 한다.

## Lazy Evaluation

`map`과 `flatMap`은 중간 연산이므로 호출 시 즉시 모든 요소를 처리하지 않는다.

```java
Stream<String> pipeline = names.stream()
    .map(name -> {
        System.out.println(name);
        return name.toUpperCase();
    });

// 아직 출력 없음
List<String> result = pipeline.toList();
```

Terminal Operation이 실행될 때 요소가 Pipeline을 하나씩 통과한다. 이 덕분에 `findFirst`, `limit` 같은 Short-circuit 연산은 필요한 만큼만 처리할 수 있다.

## 순수 함수가 중요한 이유

Mapper가 외부 List를 수정하거나 Counter를 증가시키면 Lazy 실행 순서와 Parallel Stream에서 결과를 예측하기 어렵다. 입력을 받아 새 값을 반환하는 순수한 함수를 우선한다.

```java
List<String> normalized = names.stream()
    .map(String::trim)
    .filter(name -> !name.isEmpty())
    .map(String::toLowerCase)
    .toList();
```

## 기억할 점

`map`은 값을 다른 값으로 바꾸고, `flatMap`은 각 값이 만든 작은 Stream들을 하나의 흐름으로 연결한다. Type을 `Stream<List<T>>`, `Stream<Optional<T>>`, `Stream<Stream<T>>`처럼 직접 적어보면 어느 연산이 필요한지 분명해진다.
## 프리미티브 타입의 배열은 함수가 따로 존재한다.
*   `flatMapToInt`
*   `flatMapToLong`
*   `flatMapToDouble`
*   등등
Java의 제네릭은 프리미티브 타입을 지원하지 않기 때문에, 프리미티브 타입의 스트림을 생성하려면 별도의 함수를 사용해야 한다.

# Reference
