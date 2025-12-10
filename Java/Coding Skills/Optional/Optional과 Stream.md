---
id: Optional과 Stream
started: 2025-03-06
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Optional과 Stream

## Optinal Chaining
### 값이 있는지 체크
```java title="Optional Chaining 예시"
public String getTeamNameFromDevice(Optional<Device> optDevice){
	return optDevice
    	.map(Device::getOwner)
        .map(User::getTeam)
        .map(Team::getName)
        .orElseThrow(IllegalStateException::new);
}
```
Optional Chaining은 Optional 객체 내에 값이 존재하는지 확인하고, 값이 존재할 경우에만 다음 메서드를 실행하는 방식이다. 위 예시에서는 `optDevice`가 `Device` 객체를 가지고 있다면, `getOwner()`, `getTeam()`, `getName()` 메서드를 순차적으로 호출하여 팀 이름을 반환한다. 만약 `optDevice`가 비어있거나 중간에 null 값이 발생하면 `orElseThrow()` 메서드를 통해 `IllegalStateException` 예외를 발생시킨다.
### 조건을 만족할때 동작
```java title="Optional로 특정 변수에 값이 있다면 동작을 수행시킬 수 있다."
Optional<Integer> newId = Optional.ofNullable(id)
    .filter(service::existsById)
    .map(service::findById);
```
Optional 객체가 특정 조건을 만족하는 경우에만 동작을 수행하도록 할 수 있다. 위 예시에서는 `id`가 null이 아닌 경우에만 `filter()` 메서드를 통해 `service::existsById` 조건을 확인하고, 조건을 만족하면 `map()` 메서드를 통해 `service::findById`를 실행하여 새로운 ID를 가져온다. 만약 `id`가 null이거나 조건을 만족하지 않으면, `newId`는 빈 Optional 객체가 된다.
## Method Chaining
### Stream으로 Map 생성하기
```java title="Stream으로 Map 생성하기"
Map<String, ValueDto> newList  
    = list.stream()  
                 .collect(Collectors.toMap(  
                     this::getKey,  
                     this::generateValue  
                 ));
```
**설명:**
Stream을 사용하여 List를 Map으로 변환하는 예시이다. `stream()` 메서드를 통해 List를 Stream으로 변환하고, `collect()` 메서드를 사용하여 Stream의 각 요소를 key-value 쌍으로 변환하여 Map으로 수집한다. `Collectors.toMap()` 메서드는 key와 value를 생성하는 함수를 인자로 받는다.
*   `this::getKey`: Stream의 각 요소에서 key를 추출하는 메서드 레퍼런스이다.
*   `this::generateValue`: Stream의 각 요소에서 value를 생성하는 메서드 레퍼런스이다.
**추가 설명:**
Stream을 사용하면 데이터를 변환하고 수집하는 다양한 작업을 간결하게 표현할 수 있다. `map()`, `filter()`, `reduce()` 등 다양한 메서드를 사용하여 데이터를 처리할 수 있으며, `collect()` 메서드를 사용하여 결과를 List, Map, Set 등 다양한 형태로 수집할 수 있다.
### Optional을 Stream으로 변환하기
Java 9부터는 Optional 객체를 Stream으로 변환할 수 있다. 이를 통해 Optional 객체가 값을 가지고 있을 때만 Stream 연산을 수행할 수 있다.
```java title="Optional을 Stream으로 변환하는 예시"
Optional<String> optionalValue = Optional.of("example");
Stream<String> stream = optionalValue.stream();
stream.forEach(System.out::println); // "example" 출력
```
만약 Optional이 비어있다면, `stream()` 메서드는 빈 Stream을 반환한다. 이를 통해 NullPointerException을 방지하고 안전하게 Stream 연산을 수행할 수 있다.
### Stream에서 Optional로 변환하기
Stream에서 특정 조건을 만족하는 첫 번째 요소를 Optional로 반환할 수 있다.
```java title="Stream에서 Optional로 변환하는 예시"
List<String> list = Arrays.asList("a", "b", "c");
Optional<String> firstElement = list.stream()
                                     .filter(s -> s.startsWith("b"))
                                     .findFirst();
System.out.println(firstElement.orElse("Not Found")); // "b" 출력
```
`findFirst()` 메서드는 Stream에서 첫 번째 요소를 Optional로 반환한다. 만약 Stream이 비어있다면, 빈 Optional을 반환한다.

# Reference
[Optional Chaining](https://velog.io/@hksdpr/JAVA-Optional%EC%9D%98-%EC%B6%A9%EA%B2%A9%EC%A0%81%EC%9D%B8-%EC%82%AC%EC%9A%A9%EB%B2%95-map%EC%9D%84-%EC%9D%B4%EC%9A%A9%ED%95%9C-%EC%B2%B4%EC%9D%B4%EB%8B%9D)