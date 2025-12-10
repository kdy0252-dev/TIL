---
id: Java Generic
started: 2025-05-08
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# Java Generic

## Generic이란?
Generic은 클래스나 메서드를 정의할 때, 타입을 미리 지정하지 않고 필요할 때 지정할 수 있도록 하는 기능이다. 마치 함수에 인자를 넘겨주듯이, 타입도 필요에 따라 넘겨줄 수 있게 하는 것이라고 생각하면 된다.

```java title="제네릭을 사용하는 예시"
ArrayList<Integer> list_1 = new ArrayList<Integer>();
ArrayList<String> list_2 = new ArrayList<String>();
ArrayList<Double> list_3 = new ArrayList<Double>();
ArrayList<Character> list_4 = new ArrayList<Character>();
```
위 예시처럼, ArrayList를 사용할 때마다 Integer, String, Double, Character 등 타입을 지정해야 한다. 만약 Generic이 없다면, 모든 타입을 Object로 받아서 사용해야 하고, 값을 꺼내올 때마다 타입 캐스팅을 해야 한다.

Generic을 사용하면, 컴파일 시점에 타입이 결정되므로 타입 안정성을 확보할 수 있고, 불필요한 타입 캐스팅을 줄일 수 있다.
> [!Info] 컴파일타임에 사용할 파라미터의 타입을 체크하고, 필요한 구현체를 만들어주는 것이 Generic의 핵심이다!
즉, 특정 타입을 지정하는 것이 아니라 필요에 따라 타입을 지정할 수 있는 Generic 타입이라는 의미다!
## 장점
*   **타입 안정성**: 컴파일타임에 타입 체크를 수행하므로 런타임에 타입 에러가 발생할 가능성을 줄여준다.
*   **코드 재사용성**: Generic 타입을 사용하면 여러 타입에 대해 동일한 코드를 재사용할 수 있다.
*   **타입 캐스팅 불필요**: Generic 타입을 사용하면 값을 꺼내올 때 타입 캐스팅을 할 필요가 없다.
## Generic 타입의 종류
```java title="Generic Type의 종류"
<T>  // Type
<E>  // Element
<K>  // Key
<V>  // Value
<N>  // Number
```
Generic 타입 이름은 관례적으로 한 글자로 된 대문자를 사용한다. 기능상으로는 차이가 없고, 어떤 의미로 사용할지를 나타내는 용도이다.
## Generic 선언문
```java title="제네릭 타입 선언문 예시"
public class ClassName <T> { ... }
public interface InterfaceName <T> { ... }
```

```java title="실 사용 예시"
public class HashMap <K, V> { ... }
```
Generic 클래스나 인터페이스를 선언할 때, 타입 파라미터를 지정할 수 있다. 위 예시처럼, HashMap은 K와 V라는 두 개의 타입 파라미터를 가진다.
> [!Warning] 타입 파라미터로 선언할 수 있는 것은 Reference Type만 가능하다. Primitive Type (int, char, double 등)은 사용할 수 없다.
```java title="generic method"
public <T> T genericMethod(T o) {}
```
클래스와는 다르게 메서드에서 사용할 때는 `<T>`처럼 미리 선언해야 사용할 수 있다.
## Generic Class
```java title="Generic Class Example"
static class Node<K,V> implements Map.Entry<K,V> {
    final int hash;
    final K key;
    V value;
    Node<K,V> next;

    Node(int hash, K key, V value, Node<K,V> next) {
        this.hash = hash;
        this.key = key;
        this.value = value;
        this.next = next;
    }

    public final K getKey()        { return key; }
    public final V getValue()      { return value; }
    public final String toString() { return key + "=" + value; }

    public final int hashCode() {
        return Objects.hashCode(key) ^ Objects.hashCode(value);
    }

    public final V setValue(V newValue) {
        V oldValue = value;
        value = newValue;
        return oldValue;
    }

    public final boolean equals(Object o) {
        if (o == this)
            return true;

        return o instanceof Map.Entry<?, ?> e
                && Objects.equals(key, e.getKey())
                && Objects.equals(value, e.getValue());
    }
}
```
위 예시는 Java의 HashMap 내부의 static Class Node의 구현체다. K와 V라는 Generic 타입을 사용하여 Key와 Value의 타입을 지정할 수 있도록 했다.
## 제한된 Generic (Bounded Types)
Generic 타입을 사용할 때, 특정 타입만 사용하도록 제한할 수 있다.
```java title="제한된 Generic Example"
<T extends 상위타입>  // T는 상위타입의 하위 타입만 가능
<T super 하위타입>    // T는 하위타입의 상위 타입만 가능
```
예를 들어, Number 클래스의 하위 타입만 사용하도록 제한하려면 `<T extends Number>`와 같이 사용할 수 있다.
## WildCard
`?`는 WildCard라고 하며, Generic 타입을 특정 타입으로 지정하지 않을 때 사용한다. WildCard는 주로 메서드의 파라미터 타입으로 사용되며, 어떤 타입이든 받을 수 있다는 의미를 나타낸다.
## 제한된 WildCard
WildCard도 Generic 타입처럼 특정 타입만 사용하도록 제한할 수 있다.
```java title="제한된 Wild Card Example"
<? extends T>	// T와 T의 자손 타입만 가능
<? super T>	    // T와 T의 부모 타입만 가능
<?>		        // 모든 타입 가능. <? extends Object>랑 같은 의미
```
## Generic super 키워드의 사용 예시
```java title="super를 사용하지 않는 예시"
public class SaltClass <E extends Comparable<E>> { ... }
public class Student implements Comparable<Student> {
	@Override
	public int compareTo(Person o) { ... };
}
public class Main {
	public static void main(String[] args) {
		SaltClass<Student> a = new SaltClass<Student>();
	}
}
```

```java title="using super keyword example"
public class SaltClass <E extends Comparable<E>> { ... }	// Error가능성 있음
public class SaltClass <E extends Comparable<? super E>> { ... }	// 안전성이 높음
public class Person {...}
public class Student extends Person implements Comparable<Person> {
	@Override
	public int compareTo(Person o) { ... };
}
public class Main {
	public static void main(String[] args) {
		SaltClass<Student> a = new SaltClass<Student>();
	}
}
```
`<? super E>`는 E 또는 E의 상위 타입을 Comparable 인터페이스의 타입 파라미터로 사용할 수 있도록 한다. 이를 통해 더 넓은 범위의 타입을 처리할 수 있게 된다.

# Reference
[Java Generic](https://st-lab.tistory.com/153)