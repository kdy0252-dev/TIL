---
id: Stream map과 flatmap
started: 2025-04-25
tags:
  - Java
  - ✅DONE
group: "[[Java Coding Skills]]"
---
# Stream map과 flatmap
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
## 프리미티브 타입의 배열은 함수가 따로 존재한다.
*   `flatMapToInt`
*   `flatMapToLong`
*   `flatMapToDouble`
*   등등
Java의 제네릭은 프리미티브 타입을 지원하지 않기 때문에, 프리미티브 타입의 스트림을 생성하려면 별도의 함수를 사용해야 한다.

# Reference