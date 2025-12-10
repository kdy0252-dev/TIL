# Stack (스택)

## 1. 개요 (Overview)
**스택(Stack)**은 데이터를 차곡차곡 쌓아 올리는 형태의 자료구조로, 가장 마지막에 삽입된 데이터가 가장 먼저 삭제되는 **LIFO (Last-In, First-Out, 후입선출)** 구조를 가집니다.
컴퓨터 시스템의 **함수 호출 스택(Call Stack)**, 웹 브라우저의 **뒤로 가기**, 텍스트 에디터의 **실행 취소(Undo)** 등 "가장 최근의 상태로 되돌아가야 하는" 모든 기능의 근간이 되는 핵심적인 자료구조입니다.

---

## 2. 주요 동작 (Operations)
스택은 제한된 접근 지점(Top)을 통해서만 데이터에 접근할 수 있습니다.

- **Push (삽입)**: 스택의 맨 위(Top)에 새로운 데이터를 추가합니다. 공간이 꽉 찼다면 **Stack Overflow**가 발생합니다. 시간 복잡도는 $O(1)$입니다.
- **Pop (삭제)**: 스택의 맨 위(Top)에 있는 데이터를 꺼내서 반환합니다. 스택이 비어 있다면 **Stack Underflow**가 발생합니다. 시간 복잡도는 $O(1)$입니다.
- **Peek (조회)**: Pop과 달리 스택에서 데이터를 제거하지 않고, 맨 위에 어떤 값이 있는지 확인만 합니다. $O(1)$입니다.
- **IsEmpty**: 스택이 비어있는지 확인합니다.

---

## 3. 구현 방식 (Implementation Strategies)

### 3.1 배열 기반 (Array-based)
- 고정된 크기의 배열을 사용하고, `top` 인덱스를 관리합니다.
- **장점**: 구현이 간단하고, 메모리 접근이 연속적이어서 **캐시 히트율(Cache Hit Rate)**이 높습니다. 인덱스를 이용한 빠른 접근이 가능합니다.
- **단점**: 크기가 고정되어 있어 유연하지 않습니다. 동적 배열(ArrayList 등)을 쓰면 크기 조절(Doubling) 시 $O(n)$의 복사 비용이 발생합니다.

### 3.2 연결 리스트 기반 (LinkedList-based)
- 노드를 연결하여 스택을 구현합니다. 새로운 데이터를 Head 앞에 붙이는 방식입니다.
- **장점**: 크기 제한이 없으며(메모리 허용 범위 내), 데이터 삽입/삭제 시 배열 복사 비용이 없습니다.
- **단점**: 노드마다 포인터를 위한 추가 메모리(`next`)가 필요합니다. 메모리가 불연속적이어서 캐시 효율이 떨어집니다.

---

## 4. Java에서의 스택 (java.util.Stack vs Deque)

> **[CAUTION]** Java의 `java.util.Stack` 클래스는 쓰지 마세요!

### 4.1 왜 `java.util.Stack`은 Deprecated (지양)되었나?
1.  **Vector 상속**: `Stack`은 Java 1.0부터 존재한 레거시 클래스인 `Vector`를 상속받습니다. `Vector`는 모든 메서드에 `synchronized` 키워드가 붙어 있어, 단일 스레드 환경에서도 불필요한 락 오버헤드가 발생하여 성능이 떨어집니다.
2.  **LIFO 위반**: `Vector`를 상속받았기에, 스택인데도 `get(index)`나 `insertElementAt()`을 통해 중간 데이터에 접근하거나 삽입할 수 있습니다. 이는 스택의 추상화(ADT)를 깨뜨립니다.

### 4.2 대안: `ArrayDeque`
Java 공식 문서(JavaDoc)에서는 스택이 필요할 때 **`Deque` (Double Ended Queue)** 인터페이스의 구현체인 **`ArrayDeque`**를 사용할 것을 권장합니다.

```java
Deque<Integer> stack = new ArrayDeque<>();
stack.push(1);
stack.push(2);
int value = stack.pop(); // 2
```
- `ArrayDeque`는 동기화를 지원하지 않아 빠릅니다. (멀티구동기화가 필요하다면 `Collections.synchronizedDeque()` 사용)
- 양쪽 끝에서 삽입/삭제가 가능한 덱이지만, `push()` / `pop()` 메서드를 제공하여 스택처럼 완벽하게 사용할 수 있습니다.

---

## 5. 주요 활용 사례 (Applications)

### 5.1 깊이 우선 탐색 (DFS, Depth-First Search)
그래프나 트리 탐색 시, 갈 수 있는 만큼 깊게 들어가고 막히면 돌아오기(Backtracking) 위해 스택을 사용합니다. 재귀 호출 또한 시스템 내부적으로 스택을 사용합니다.

### 5.2 수식 계산 (Postfix / Prefix Evaluation)
후위 표기법(Reverse Polish Notation)으로 된 수식을 계산할 때 사용합니다.
- 식: `3 4 +` -> 스택에 3, 4 넣고 `+` 만나면 4, 3 꺼내서 더해서 7 Push.

### 5.3 괄호 검사 (Parenthesis Matching)
코드 에디터나 컴파일러에서 `()`, `{}`, `[]` 괄호의 짝이 맞는지 검사할 때 사용합니다. 여는 괄호는 Push, 닫는 괄호는 Pop하여 매칭을 확인합니다.

---

## 6. 구현 예제 (Java DFS)

스택을 활용한 간단한 DFS 구현 예제입니다.

```java
import java.util.*;

public class GraphDFS {
    
    // 인접 리스트로 그래프 표현
    static Map<Integer, List<Integer>> graph = new HashMap<>();

    public static void main(String[] args) {
        initGraph();
        dfs(1); // 1번 노드부터 탐색
    }

    static void dfs(int startNode) {
        Deque<Integer> stack = new ArrayDeque<>();
        Set<Integer> visited = new HashSet<>();

        stack.push(startNode);

        while (!stack.isEmpty()) {
        } else if (c == '{') {
            stack.push('}');
        } else if (c == '[') {
            stack.push(']');
        } else if (stack.isEmpty() || stack.pop() != c) {
            return false;
        }
    }
    return stack.isEmpty();
}
```

# Reference