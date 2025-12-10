---
id: Stream Collector
started: 2025-04-24
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Stream Collector
## Stream의 toArray는 항상 Object[] 을 반환한다.
Stream의 `toArray()` (인자 없는)는 항상 `Object[]` 를 리턴한다.
```java title="Object[]을 반환한다."
Account[] Account = dto.stream()
    .map(dto -> new Account())
    .toArray();
```
는 `Object[]` → `Account[]` 로 캐스팅이 자동으로 안된다.
```java title="Object[]을 반환한다."
Account[] Account = dto.stream()
    .map(dto -> new Account())
    .toArray(Account[]::new);
```
와 같이 반환타입을 지정해주어야한다.
## Stream의 collect() 메서드를 사용하여 다양한 컬렉션으로 변환하기
Stream의 `collect()` 메서드는 스트림의 요소들을 수집하여 다양한 컬렉션으로 변환하는 데 사용된다. `toList()`, `toSet()`, `toMap()` 등의 메서드를 사용하여 List, Set, Map 등으로 변환할 수 있다.
### 1. toList()
```java title="toList()를 사용하여 List로 변환"
List<String> names = Stream.of("Alice", "Bob", "Charlie")
                        .collect(Collectors.toList());
System.out.println(names); // [Alice, Bob, Charlie]
```
`toList()` 메서드는 스트림의 요소들을 List로 수집한다.
### 2. toSet()
```java title="toSet()를 사용하여 Set으로 변환"
Set<String> names = Stream.of("Alice", "Bob", "Charlie", "Alice")
                       .collect(Collectors.toSet());
System.out.println(names); // [Alice, Bob, Charlie]
```
`toSet()` 메서드는 스트림의 요소들을 Set으로 수집한다. 중복된 요소는 제거된다.
### 3. toMap()
```java title="toMap()를 사용하여 Map으로 변환"
Map<String, Integer> nameLengths = Stream.of("Alice", "Bob", "Charlie")
                                       .collect(Collectors.toMap(
                                           name -> name,
                                           String::length
                                       ));
System.out.println(nameLengths); // {Alice=5, Bob=3, Charlie=7}
```
`toMap()` 메서드는 스트림의 요소들을 Map으로 수집한다. 첫 번째 인자는 key를 생성하는 함수이고, 두 번째 인자는 value를 생성하는 함수이다.
### 4. toCollection()
```java title="toCollection()를 사용하여 특정 컬렉션으로 변환"
LinkedList<String> names = Stream.of("Alice", "Bob", "Charlie")
                                .collect(Collectors.toCollection(LinkedList::new));
System.out.println(names); // [Alice, Bob, Charlie]
```
`toCollection()` 메서드는 스트림의 요소들을 특정 컬렉션으로 수집한다. 위 예시에서는 LinkedList로 수집한다.

# Reference