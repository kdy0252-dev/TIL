---
id: ArrayEqualsTest
started: 2025-04-25
tags:
  - ✅DONE
  - Java
group: "[[Java Coding Skills]]"
---
# 배열 요소 비교 테스트
## 배열 요소 비교 시 주의사항
배열의 내용을 비교할 때는 단순히 `"=="` 연산자를 사용하면 안 된다. `"=="` 연산자는 배열의 참조 주소를 비교하기 때문에, 내용이 같더라도 다른 객체라면 `false`를 반환한다. 따라서 배열의 내용을 비교하려면 각 요소들을 순회하며 비교하거나, `Arrays.equals()` 또는 `Arrays.deepEquals()` 메서드를 사용해야 한다.
## 1. Arrays.equals()
1차원 배열의 요소들을 비교할 때 사용한다. **순서까지 같아야** `true`를 반환한다.
```java title="Arrays.equals()를 사용한 배열 비교 예시 (순서 중요)"
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class ArrayEqualsTest {

    @Test
    void testArrayEquals() {
        int[] expected = {1, 2, 3, 4, 5};
        int[] actual = {1, 2, 3, 4, 5};

        assertTrue(Arrays.equals(expected, actual));
    }

    @Test
    void testArrayEqualsOrderMatters() {
        int[] expected = {1, 2, 3};
        int[] actual = {3, 2, 1};

        assertFalse(Arrays.equals(expected, actual)); // 순서가 다르므로 false
    }
}
```
*   `Arrays.equals(expected, actual)`은 두 배열의 모든 요소가 같은지 비교하여 같으면 `true`, 다르면 `false`를 반환한다. 순서가 다르면 `false`를 반환한다.
## 2. Arrays.deepEquals()
다차원 배열의 요소들을 비교할 때 사용한다. **순서까지 같아야** `true`를 반환한다.
```java title="Arrays.deepEquals()를 사용한 다차원 배열 비교 예시 (순서 중요)"
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class ArrayDeepEqualsTest {

    @Test
    void testArrayDeepEquals() {
        int[][] expected = {{1, 2}, {3, 4}};
        int[][] actual = {{1, 2}, {3, 4}};

        assertTrue(Arrays.deepEquals(expected, actual));
    }

    @Test
    void testArrayDeepEqualsOrderMatters() {
        int[][] expected = {{1, 2}, {3, 4}};
        int[][] actual = {{3, 4}, {1, 2}};

        assertFalse(Arrays.deepEquals(expected, actual)); // 순서가 다르므로 false
    }
}
```
*   `Arrays.deepEquals(expected, actual)`은 두 다차원 배열의 모든 요소가 같은지 재귀적으로 비교하여 같으면 `true`, 다르면 `false`를 반환한다. 순서가 다르면 `false`를 반환한다.
## 3. Assertions.assertArrayEquals()
JUnit에서 제공하는 assert 메서드로, 배열의 내용을 비교할 때 사용한다. **순서까지 같아야** 통과한다.
```java title="assertArrayEquals()를 사용한 배열 비교 예시 (순서 중요)"
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class AssertArrayEqualsTest {

    @Test
    void testAssertArrayEquals() {
        int[] expected = {1, 2, 3, 4, 5};
        int[] actual = {1, 2, 3, 4, 5};

        assertArrayEquals(expected, actual);
    }

    @Test
    void testAssertArrayEqualsWithMessage() {
        int[] expected = {1, 2, 3};
        int[] actual = {1, 2, 4};

        assertArrayEquals(expected, actual, "배열의 내용이 다릅니다.");
    }

    @Test
    void testAssertArrayEqualsOrderMatters() {
        int[] expected = {1, 2, 3};
        int[] actual = {3, 2, 1};

        assertThrows(AssertionError.class, () -> assertArrayEquals(expected, actual)); // 순서가 다르므로 AssertionError 발생
    }
}
```
*   `assertArrayEquals(expected, actual)`은 두 배열의 모든 요소가 같은지 비교하여 다르면 AssertionError를 발생시킨다. 순서가 다르면 AssertionError를 발생시킨다.
*   `assertArrayEquals(expected, actual, message)`는 배열이 다를 경우 지정된 메시지를 함께 출력한다.
## 4. 순서 상관없이 요소만 같은지 비교하는 방법
배열의 순서가 중요하지 않고 요소 구성만 같은지 비교하려면, `Arrays.sort()`로 정렬한 후 비교하거나, `HashSet`을 사용하여 비교할 수 있다.
### 4.1. Arrays.sort() 후 비교
```java title="Arrays.sort() 후 비교하는 예시"
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class ArrayEqualsIgnoreOrderTest {

    @Test
    void testArrayEqualsIgnoreOrder() {
        int[] expected = {1, 2, 3};
        int[] actual = {3, 1, 2};

        Arrays.sort(expected);
        Arrays.sort(actual);

        assertArrayEquals(expected, actual); // 순서 상관없이 요소만 같으면 통과
    }
}
```
*   `Arrays.sort()`를 사용하여 두 배열을 정렬한 후 `assertArrayEquals()`로 비교하면, 순서에 상관없이 요소 구성만 같은지 확인할 수 있다.
### 4.2. HashSet을 사용하여 비교
```java title="HashSet을 사용하여 비교하는 예시"
import java.util.Arrays;
import java.util.HashSet;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class ArrayEqualsIgnoreOrderUsingSetTest {

    @Test
    void testArrayEqualsIgnoreOrderUsingSet() {
        int[] expected = {1, 2, 3};
        int[] actual = {3, 1, 2};

        HashSet<Integer> expectedSet = new HashSet<>(Arrays.stream(expected).boxed().toList());
        HashSet<Integer> actualSet = new HashSet<>(Arrays.stream(actual).boxed().toList());

        assertEquals(expectedSet, actualSet); // 순서 상관없이 요소만 같으면 통과
    }
}
```
*   배열을 `HashSet`으로 변환하여 비교하면, 순서에 상관없이 요소 구성만 같은지 확인할 수 있다.
*   `Arrays.stream(array).boxed().toList()`를 사용하여 int[]를 `List<Integer>`로 변환한 후 `HashSet`을 생성한다.
## 다양한 타입의 배열 비교
### 객체 배열 비교
```java title="객체 배열 비교 예시"
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class ObjectArrayEqualsTest {

    @Test
    void testObjectArrayEquals() {
        String[] expected = {"apple", "banana", "cherry"};
        String[] actual = {"apple", "banana", "cherry"};

        assertArrayEquals(expected, actual);
    }
}
```
### List와 배열 비교
```java title="List와 배열 비교 예시"
import java.util.Arrays;
import java.util.List;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.util.ArrayList;

public class ListToArrayEqualsTest {

    @Test
    void testListToArrayEquals() {
        List<String> expectedList = Arrays.asList("apple", "banana", "cherry");
        String[] actualArray = {"apple", "banana", "cherry"};

        assertArrayEquals(expectedList.toArray(), actualArray);
    }
}
```
**주의:** `assertArrayEquals()`는 배열을 인자로 받으므로, List를 배열로 변환해야 한다.
# Reference