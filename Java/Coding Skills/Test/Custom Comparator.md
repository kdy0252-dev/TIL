---
id: Custom Comparator
started: 2025-04-25
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Custom Comparator
## Custom Comparator란?
Custom Comparator는 Java에서 기본적으로 제공하는 비교 방식 외에, 개발자가 직접 정의한 기준으로 객체를 비교할 수 있도록 하는 인터페이스다. `Comparator` 인터페이스를 구현하여 `compare()` 메서드를 오버라이드하면, 원하는 방식으로 객체를 정렬하거나 비교할 수 있다.
### Comparator를 통해서 값이 완전히 같지 않더라도 커스텀 Comparator를 만들어서 사용 할 수 있다.
```Java title="Custom Conparator를 사용하여 객체 내의 Object또한 비교 할 수 있다."
// 1) LocalDateTime 비교용 Comparator 정의
Comparator<LocalDateTime> truncatedComparator = Comparator.comparing(dt -> dt.truncatedTo(ChronoUnit.SECONDS));
// 2) 필드 비교 시 해당 타입에 이 Comparator 사용
assertThat(ctlInfoList)
    .usingRecursiveComparison()
    .withComparatorForType(truncatedComparator, LocalDateTime.class)
    .ignoringFields("filename", "ctlOer")
    .isEqualTo(expectedCtlList);
```
## 예제 코드
### 예시 1: 나이와 이름으로 정렬
```java title="나이와 이름으로 정렬하는 Custom Comparator"
public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String getName() {
        return name;
    }

    public int getAge() {
        return age;
    }
}

Comparator<Person> ageAndNameComparator = Comparator.comparing(Person::getAge)
                                                    .thenComparing(Person::getName);

List<Person> people = Arrays.asList(
    new Person("Alice", 30),
    new Person("Bob", 25),
    new Person("Charlie", 30),
    new Person("David", 25)
);

people.sort(ageAndNameComparator);

people.forEach(person -> System.out.println(person.getName() + " " + person.getAge()));
// Bob 25
// David 25
// Alice 30
// Charlie 30
```
*   `Person` 객체를 나이(`age`)를 기준으로 먼저 정렬하고, 나이가 같은 경우 이름(`name`)을 기준으로 정렬한다.
*   `Comparator.comparing()` 메서드를 사용하여 나이를 기준으로 정렬하고, `thenComparing()` 메서드를 사용하여 이름을 기준으로 정렬한다.
### 예시 2: null 처리와 함께 정렬
```java title="null 처리와 함께 정렬하는 Custom Comparator"
Comparator<String> nullSafeStringComparator = Comparator.nullsFirst(Comparator.naturalOrder());

List<String> strings = Arrays.asList("Alice", null, "Bob", "Charlie", null);

strings.sort(nullSafeStringComparator);

strings.forEach(System.out::println);
// null
// null
// Alice
// Bob
// Charlie
```
*   `null` 값을 안전하게 처리하면서 문자열을 정렬한다.
*   `Comparator.nullsFirst()` 메서드를 사용하여 `null` 값을 컬렉션의 맨 앞으로 정렬한다. `Comparator.naturalOrder()`는 기본적인 문자열 정렬을 수행한다.
## 언제 사용하면 좋을까?
*   **기본 정렬 기준이 없을 때**: 객체가 자연적인(natural) 정렬 순서를 가지지 않을 때 Custom Comparator를 사용해 정렬 기준을 정의할 수 있다.
*   **특정 필드 기준으로 정렬하고 싶을 때**: 객체의 특정 필드 값을 기준으로 정렬하고 싶을 때 Custom Comparator를 사용해 정렬 기준을 정의할 수 있다.
*   **복잡한 정렬 조건을 적용하고 싶을 때**: 여러 필드를 조합하거나, 특정 조건에 따라 정렬 순서를 변경하고 싶을 때 Custom Comparator를 사용해 복잡한 정렬 조건을 정의할 수 있다.
## 사용할 때 주의할 점
*   **일관성 유지**: `compare()` 메서드는 일관성을 유지해야 한다. 즉, `compare(a, b)`가 양수이면 `compare(b, a)`는 음수여야 하고, `compare(a, b)`가 0이면 `compare(b, a)`도 0이어야 한다.
*   **NullPointerException 주의**: 비교 대상 객체가 `null`일 수 있는 경우, `NullPointerException`이 발생하지 않도록 주의해야 한다. `Comparator.nullsFirst()` 또는 `Comparator.nullsLast()`를 사용하여 `null` 값을 안전하게 처리할 수 있다.
*   **equals() 메서드와의 관계**: `compare(a, b)`가 0이면 `a.equals(b)`가 참인 것이 일반적이지만, 필수는 아니다. 하지만 `equals()` 메서드와 `compare()` 메서드의 결과가 다를 경우 혼란을 초래할 수 있으므로, 가능한 한 일치시키는 것이 좋다.

# Reference