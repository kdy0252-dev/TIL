```
# Heap (Priority Queue)

## 1. 개요 (Overview)
**힙(Heap)**은 **최댓값**이나 **최솟값**을 빠르게 찾아내기 위해 고안된 **완전 이진 트리(Complete Binary Tree)** 기반의 자료구조입니다.
일반적인 큐(Queue)는 먼저 들어온 데이터가 먼저 나가는 FIFO(First-In, First-Out) 구조이지만, 힙은 데이터의 삽입 순서와 상관없이 **우선순위(Priority)가 높은 데이터가 먼저 나가는** 우선순위 큐(Priority Queue)를 구현하는 데 가장 효율적입니다.

---

## 2. 주요 특징 및 성질 (Properties)
1.  **완전 이진 트리**: 마지막 레벨을 제외하고 모든 레벨이 완전히 채워져 있으며, 마지막 레벨은 왼쪽부터 차곡차곡 채워져 있어야 합니다. 이는 배열로 효율적인 구현이 가능하게 합니다.
2.  **힙 속성 (Heap Property)**:
    *   **최대 힙 (Max Heap)**: 부모 노드의 키 값이 자식 노드의 키 값보다 크거나 같아야 합니다. (Root = Max)
    *   **최소 힙 (Min Heap)**: 부모 노드의 키 값이 자식 노드의 키 값보다 작거나 같아야 합니다. (Root = Min)
3.  **반정렬 상태**: 힙은 형제(Sibling) 노드 간의 대소 관계는 정해져 있지 않습니다. "느슨한 정렬 상태"를 유지합니다.

---

## 3. 동작 원리 (Mechanism)

힙은 보통 **배열(Array)**을 사용하여 구현합니다.
*   인덱스 $i$인 노드의 왼쪽 자식: $2 \times i + 1$ (0-index 기준)
*   인덱스 $i$인 노드의 오른쪽 자식: $2 \times i + 2$
*   인덱스 $i$인 노드의 부모: $(i - 1) / 2$

### 3.1 삽입 (Insert) - $O(\log n)$
1.  새로운 원소를 트리의 **가장 마지막 위치**에 추가합니다.
2.  **Sift-Up (Up-Heap)**: 추가된 원소와 부모를 비교하여, 힙 속성이 위배되면(자식이 더 우선순위가 높으면) 위치를 교환(Swap)합니다.
3.  이 과정을 힙 속성이 만족될 때까지 루트 방향으로 반복합니다.

### 3.2 삭제 (Delete / Extract) - $O(\log n)$
1.  루트 노드(최선순위)를 제거하고 반환합니다.
2.  트리의 **가장 마지막 원소**를 루트 자리로 이동시킵니다.
3.  **Sift-Down (Down-Heap)**: 루트로 올라온 원소와 자식들을 비교하여, 힙 속성이 위배되면 더 우선순위가 높은 자식과 교환합니다.
4.  이 과정을 힙 속성이 만족될 때까지 리프 방향으로 반복합니다.

### 3.3 힙 생성 (Heapify) - $O(n)$
정렬되지 않은 배열을 힙으로 만드는 과정입니다. 리프 노드가 아닌 마지막 노드부터 역순으로 Sift-Down을 수행하면 $O(n)$ 시간에 완료됩니다. (단순 삽입 반복은 $O(n \log n)$).

---

## 4. 힙 정렬 (Heap Sort)
힙을 이용한 정렬 알고리즘입니다.
1.  주어진 데이터로 최대 힙을 구성합니다 (Heapify).
2.  루트(최대값)를 마지막 요소와 바꾼 뒤, 힙 크기를 1 줄이고 Sift-Down을 수행합니다.
3.  이 과정을 반복하면 배열이 오름차순으로 정렬됩니다.
*   **시간 복잡도**: $O(n \log n)$ (Best, Avg, Worst 모두)
*   **공간 복잡도**: $O(1)$ (In-place sorting)
*   **특징**: 퀵 정렬보다 느리지만 안정적인 성능을 보장합니다.

---

## 5. Java 구현 예제 (PriorityQueue)

Java에서는 `java.util.PriorityQueue`가 최소 힙(Min Heap)으로 구현되어 있습니다.

### 5.1 기본 사용법 (Min Heap)
```java
public class MinHeapExample {
    public static void main(String[] args) {
        // 기본이 최소 힙
        PriorityQueue<Integer> pq = new PriorityQueue<>();

        pq.offer(5);
        pq.offer(1);
        pq.offer(3);

        while (!pq.isEmpty()) {
            System.out.println(pq.poll()); // 1, 3, 5 순서로 출력
        }
    }
}
```

### 5.2 최대 힙 (Max Heap)
```java
PriorityQueue<Integer> maxPq = new PriorityQueue<>(Collections.reverseOrder());
maxPq.offer(5);
maxPq.offer(1);
// 5, 1 순서로 poll됨
```

### 5.3 사용자 정의 객체 (Custom Object)
`Comparable`을 구현하거나 `Comparator`를 제공해야 합니다.

```java
class Task implements Comparable<Task> {
    String name;
    int priority;

    public Task(String name, int priority) {
        this.name = name;
        this.priority = priority;
    }

    // 우선순위 높은 것(숫자가 큰 것)이 먼저 나오도록 설정
    @Override
    public int compareTo(Task o) {
        return o.priority - this.priority;
    }
}

// 사용
PriorityQueue<Task> tasks = new PriorityQueue<>();
tasks.offer(new Task("Coding", 1));
tasks.offer(new Task("Meeting", 5)); // 먼저 나옴
```

---

## 6. 활용 사례 (Use Cases)
*   **다익스트라(Dijkstra) 알고리즘**: 최단 경로 탐색 시 가장 비용이 적은 간선을 빠르게 선택하기 위해 사용.
*   **프림(Prim) 알고리즘**: 최소 신장 트리(MST) 구현.
*   **스케줄링**: 운영체제의 작업 스케줄링.
*   **중앙값 구하기**: 최대 힙과 최소 힙 두 개를 사용하여 실시간으로 들어오는 데이터 스트림의 중앙값을 $O(1)$에 조회.

# Reference
- [Java PriorityQueue Doc](https://docs.oracle.com/javase/8/docs/api/java/util/PriorityQueue.html)
- [Visual Algo - Heap](https://visualgo.net/en/heap)
- [Introduction to Algorithms (CLRS) - Heapsort](https://mitpress.mit.edu/books/introduction-algorithms)
```