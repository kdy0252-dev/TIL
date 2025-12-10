# Tree (트리)

## 1. 개요 (Overview)
**트리(Tree)**는 노드(Node)들이 나무 가지처럼 연결된 비선형 **계층적(Hierarchical)** 자료구조입니다.
리스트, 스택, 큐와 같은 선형 구조와 달리 데이터 간의 1:N 관계(부모-자식 관계)를 표현하는 데 적합합니다. 파일 시스템, HTML DOM 구조, DB 인덱스, 라우팅 테이블 등 컴퓨터 과학 전반에서 광범위하게 사용됩니다.

---

## 2. 기본 용어 (Terminology)
- **Root (루트)**: 트리의 가장 꼭대기에 있는 노드. (부모가 없는 유일한 노드)
- **Node (노드)**: 트리를 구성하는 각 요소. (Key + Data + Link)
- **Edge (간선)**: 노드와 노드를 연결하는 선.
- **Parent / Child**: 연결된 두 노드 중 상위가 부모, 하위가 자식.
- **Sibling (형제)**: 같은 부모를 가진 노드들.
- **Leaf (리프/단말)**: 자식이 없는 말단 노드.
- **Depth (깊이)**: 루트에서 해당 노드까지의 간선 수. (루트 = 0)
- **Height (높이)**: 어떤 노드에서 가장 깊은 리프까지의 간선 수. (트리의 높이 = 루트의 높이)
- **Degree (차수)**: 한 노드가 가진 자식 노드의 수.

---

## 3. 이진 트리 (Binary Tree)
모든 노드가 **최대 2개의 자식**(Left, Right)만을 가지는 트리입니다. 가장 많이 쓰이는 형태입니다.

### 3.1 이진 트리의 종류
1.  **전 이진 트리 (Full Binary Tree)**: 모든 노드가 0개 또는 2개의 자식을 갖는 트리.
2.  **완전 이진 트리 (Complete Binary Tree)**: 마지막 레벨을 제외한 모든 레벨이 꽉 차 있고, 마지막 레벨은 왼쪽부터 채워진 트리. (힙의 기본 구조)
3.  **포화 이진 트리 (Perfect Binary Tree)**: 모든 내부 노드가 2개의 자식을 갖고, 모든 리프 노드가 같은 레벨에 있는 완벽한 피라미드 형태. ($2^h - 1$개의 노드)
4.  **편향 이진 트리 (Skewed Binary Tree)**: 모든 노드가 한쪽 자식만 있어 선형(LinkedList)처럼 된 트리. 탐색 효율이 $O(n)$으로 떨어짐.

---

## 4. 이진 탐색 트리 (BST, Binary Search Tree)
탐색을 효율적으로 하기 위해 특정 규칙을 적용한 이진 트리입니다.
- **규칙**: `왼쪽 자식 키 < 부모 키 < 오른쪽 자식 키`
- **검색/삽입/삭제**: 평균 $O(\log n)$.
- **문제점**: 데이터가 정렬되어서 들어오면 편향 트리(Skewed)가 되어 최악의 경우 $O(n)$이 됩니다. 이를 해결하기 위해 **AVL 트리**나 **Red-Black 트리** 같은 밸런스 트리(Balanced Tree)를 사용합니다. (Java의 `TreeMap`, `TreeSet`은 Red-Black Tree 사용)

---

## 5. 트리 순회 (Traversal)
트리의 모든 노드를 빠짐없이 한 번씩 방문하는 방법입니다.

### 5.1 깊이 우선 순회 (DFS 계열)
재귀나 스택을 사용합니다.
1.  **전위 순회 (Pre-order)**: `Root -> Left -> Right` (트리 복사 시 유용)
2.  **중위 순회 (In-order)**: `Left -> Root -> Right` (BST에서 사용 시 오름차순 정렬됨)
3.  **후위 순회 (Post-order)**: `Left -> Right -> Root` (폴더 용량 계산, 트리 삭제 시 유용 - 자식부터 처리)

### 5.2 너비 우선 순회 (BFS 계열)
4.  **레벨 순회 (Level-order)**: `Layer 0 -> Layer 1 -> Layer 2...` (큐 사용)

---

## 6. 구현 예제 (Java)

간단한 이진 트리와 순회 메서드 구현입니다.

```java
import java.util.*;

class Node {
    int data;
    Node left, right;

    public Node(int item) {
        data = item;
        left = right = null;
    }
}

public class BinaryTree {
    Node root;

    // 1. 전위 순회 (Pre-order): Root -> L -> R
    void printPreorder(Node node) {
        if (node == null) return;
        System.out.print(node.data + " ");
        printPreorder(node.left);
        printPreorder(node.right);
    }

    // 2. 중위 순회 (In-order): L -> Root -> R
    void printInorder(Node node) {
        if (node == null) return;
        printInorder(node.left);
        System.out.print(node.data + " ");
        printInorder(node.right);
    }

    // 3. 후위 순회 (Post-order): L -> R -> Root
    void printPostorder(Node node) {
        if (node == null) return;
        printPostorder(node.left);
        printPostorder(node.right);
        System.out.print(node.data + " ");
    }

    // 4. 레벨 순회 (Layer-order): BFS
    void printLevelOrder() {
        if (root == null) return;
        
        Queue<Node> queue = new LinkedList<>();
        queue.add(root);

        while (!queue.isEmpty()) {
            Node tempNode = queue.poll();
            System.out.print(tempNode.data + " ");

            if (tempNode.left != null) queue.add(tempNode.left);
            if (tempNode.right != null) queue.add(tempNode.right);
        }
    }

    public static void main(String[] args) {
        BinaryTree tree = new BinaryTree();
        /*
                1
               / \
              2   3
             / \
            4   5
        */
        tree.root = new Node(1);
        tree.root.left = new Node(2);
        tree.root.right = new Node(3);
        tree.root.left.left = new Node(4);
        tree.root.left.right = new Node(5);

        System.out.print("In-order: ");
        inOrder(root); // Output: 4 2 5 1 3
    }

    // 중위 순회 (Recursion)
    public static void inOrder(TreeNode node) {
        if (node == null) return;
        
        inOrder(node.left);        // L
        System.out.print(node.val + " "); // Root
        inOrder(node.right);       // R
    }
}
```

# Reference