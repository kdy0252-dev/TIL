# Dynamic Programming (DP, 동적 계획법)

## 1. 개요 (Overview)
**동적 계획법(Dynamic Programming, DP)**은 복잡한 문제를 작은 하위 문제(Sub-problem)로 나누고, 그 해답을 저장(Memoization)하여 재사용함으로써 전체 문제를 해결하는 알고리즘 최적화 기법입니다.
이름에 'Dynamic'이 들어가지만, 실제로는 "기억하며 풀기" 또는 "점화식 풀이"에 가깝습니다. 리처드 벨만(Richard Bellman)이 연구비를 따내기 위해 있어 보이는 이름을 붙였다는 일화가 있습니다.

DP는 **Brute Force(완전 탐색)**로 풀면 지수 시간($O(2^n)$)이 걸리는 문제를 다항 시간($O(n^2)$ 또는 $O(n)$)으로 획기적으로 줄여줍니다.

---

## 2. 핵심 조건 (Key Preconditions)
DP를 적용하기 위해서는 반드시 두 가지 조건이 충족되어야 합니다.

### 2.1 중복되는 부분 문제 (Overlapping Subproblems)
동일한 작은 문제들이 반복해서 나타나야 합니다.
- **예**: 피보나치 수열 `f(5)`를 구하기 위해서는 `f(4)`와 `f(3)`이 필요하고, `f(4)`를 구하기 위해 다시 `f(3)`과 `f(2)`가 필요합니다. 여기서 `f(3)`이 중복 호출됩니다.
- **반례**: 병합 정렬(Merge Sort)의 분할 정복은 하위 문제가 서로 독립적이며 중복되지 않으므로 DP가 아닙니다.

### 2.2 최적 부분 구조 (Optimal Substructure)
부분 문제의 최적해를 조합하면 전체 문제의 최적해가 되어야 합니다.
- **예**: 서울에서 부산까지 가는 최단 경로가 대전을 거쳐간다면, (서울->대전 최단 경로) + (대전->부산 최단 경로)가 곧 전체 최단 경로입니다.

---

## 3. 구현 방식 (Approaches)

### 3.1 Top-Down (Memoization)
- **방식**: 큰 문제를 호출하고, 필요한 하위 문제가 계산되지 않았다면 계산 후 저장(Caching)합니다. 주로 재귀(Recursion)를 사용합니다.
- **장점**: 직관적이며, 문제 해결에 필요한 하위 문제만 계산하므로(Lazy Evaluation) 때로는 더 빠를 수 있습니다.
- **단점**: 재귀 깊이가 깊어지면 `StackOverflowError`가 발생할 수 있습니다.

### 3.2 Bottom-Up (Tabulation)
- **방식**: 가장 작은 문제(`dp[0]`)부터 시작하여 차근차근 답을 채워나가며 최종 문제(`dp[n]`)에 도달합니다. 주로 반복문(For-loop)을 사용합니다.
- **장점**: 재귀 오버헤드가 없고, 모든 하위 문제를 순차적으로 해결하므로 메모리 최적화(Sliding Window)가 가능합니다.
- **단점**: 불필요한 하위 문제까지 모두 계산할 수도 있습니다.

---

## 4. 대표 예제 및 패턴 (Common Patterns)

### 4.1 0/1 배낭 문제 (Knapsack Problem)
용량이 $W$인 배낭에 무게($w_i$)와 가치($v_i$)가 다른 물건들을 담을 때, 가치의 합이 최대가 되도록 하는 문제입니다. (물건은 쪼갤 수 없음)

#### 점화식
$$
dp[i][w] = \max(dp[i-1][w], \quad dp[i-1][w - w_i] + v_i)
$$
- $dp[i][w]$: $i$번째 물건까지 고려했고 배낭 용량이 $w$일 때의 최대 가치.
- **Case 1**: 물건을 안 넣는 경우 ($dp[i-1][w]$)
- **Case 2**: 물건을 넣는 경우 ($dp[i-1][w - w_i] + v_i$) - (단, $w \ge w_i$)

#### Java 구현 (1차원 배열 최적화)
```java
public class Knapsack {
    public int solve(int W, int[] wt, int[] val, int n) {
        int[] dp = new int[W + 1];

        for (int i = 0; i < n; i++) {
            // 뒤에서부터 채워야 중복 사용을 방지할 수 있음 (0/1 Knapsack)
            for (int w = W; w >= wt[i]; w--) {
                dp[w] = Math.max(dp[w], dp[w - wt[i]] + val[i]);
            }
        }
        return dp[W];
    }
}
```

### 4.2 최장 공통 부분 수열 (LCS, Longest Common Subsequence)
두 문자열 `ABCBDAB`와 `BDCABA`의 최장 공통 부분 수열의 길이(BCAB, BDCB 등 길이 4)를 구합니다.

#### 점화식
$$
dp[i][j] = \begin{cases}
0 & \text{if } i=0 \text{ or } j=0 \\
dp[i-1][j-1] + 1 & \text{if } X[i] == Y[j] \\
\max(dp[i-1][j], dp[i][j-1]) & \text{if } X[i] \neq Y[j]
\end{cases}
$$

#### Java 구현
```java
public class LCS {
    public int solve(char[] X, char[] Y, int m, int n) {
        int[][] dp = new int[m + 1][n + 1];

        for (int i = 1; i <= m; i++) {
            for (int j = 1; j <= n; j++) {
                if (X[i - 1] == Y[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1; // 문자가 같으면 대각선 값 + 1
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]); // 다르면 이전 최댓값 계승
                }
            }
        }
        return dp[m][n];
    }
}
```

### 4.3 최장 증가 부분 수열 (LIS, Longest Increasing Subsequence)
수열 `[10, 20, 10, 30, 20, 50]` 에서 가장 긴 증가하는 부분 수열(10, 20, 30, 50)의 길이를 구합니다.

- **$O(n^2)$ 방식**: 이중 루프 DP.
- **$O(n \log n)$ 방식**: 이진 탐색(Lower Bound) 활용.

```java
// O(n^2) DP
public int lis(int[] arr) {
    int n = arr.length;
    int[] dp = new int[n];
    Arrays.fill(dp, 1);
    int max = 1;

    for (int i = 1; i < n; i++) {
        for (int j = 0; j < i; j++) {
            if (arr[i] > arr[j]) {
                dp[i] = Math.max(dp[i], dp[j] + 1);
            }
        }
        max = Math.max(max, dp[i]);
    }
    return max;
}
```

---

## 5. DP 문제 풀이 전략 (Strategy)
1. **상태(State) 정의**: 문제가 무엇을 요구하는지 파악하여 dp 배열의 인덱스가 무엇을 의미할지 결정합니다 (예: `dp[i]` = $i$번째 날까지의 최대 수익).
2. **점화식(Recurrence Relation) 세우기**: 가장 어려운 단계입니다. 이전 상태(`dp[i-1]`, `dp[i-2]`)와 현재 상태(`dp[i]`)의 관계를 수식으로 표현합니다.
3. **기저 조건(Base Case) 설정**: `dp[0]`이나 `dp[1]` 같은 초기값을 설정하여 무한 루프나 인덱스 오류를 방지합니다.
4. **구현**: Top-Down 또는 Bottom-Up 중 편한 것으로 구현합니다.

# Reference
- [GeeksforGeeks - Dynamic Programming](https://www.geeksforgeeks.org/dynamic-programming/)
- [Baekjoon Online Judge - DP Problems](https://www.acmicpc.net/problem/tag/25)
- [Introduction to Algorithms (CLRS)](https://mitpress.mit.edu/books/introduction-algorithms)