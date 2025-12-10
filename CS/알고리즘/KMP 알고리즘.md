---
id: KMP 알고리즘
started: 2025-05-05
tags:
  - ✅DONE
group:
  - "[[알고리즘]]"
---
# KMP 알고리즘

```java title="KMP 알고리즘"
for(int i=1;i<n;i++){
	while(j>0 && s[i] != s[j]){
		j = pi[j-1];
	}
	if(s[i]==s[j]){
		j++;
		pi[i]=j;
	}
}
```

```text title="s[i] s[j]가 1번 미스매치된 이후 모두 매치되는 경우"
ababab

i=1, j=0
s[i]=b
s[j]=a  mismatch j=0
pi 0 0

i=2, j=0
s[i]=a
s[j]=a  match j=1
0 0 1 

i=3, j=1
s[i]=b
s[j]=b match j=2
0 0 1 2

i=4, j=2
s[i]=a
s[j]=a match j=3
0 0 1 2 3

i=5, j=3
s[i]=a
s[j]=a match j=4
0 0 1 2 3 4
```


```text title="s[i] s[j]가 3번 미스매치되는 경우"
abcabcabx

i=1, j=0
s[i]=b
s[j]=a  mismatch j=0
pi 0 0

i=2, j=0
s[i]=c
s[j]=a  mismatch j=0
0 0 0

i=3, j=0
s[i]=a
s[j]=a match j=1
0 0 0 1

i=4, j=1
s[i]=b
s[j]=b match j=2
0 0 0 1 2

i=5, j=2
s[i]=c
s[j]=c match j=3
0 0 0 1 2 3

i=6, j=3
s[i]=a
s[j]=a match j=4
0 0 0 1 2 3 4

i=7, j=4
s[i]=b
s[j]=b match j=5
0 0 0 1 2 3 4 5

i=8, j=5
s[i]=x
s[j]=c mismatch j=5
0 0 0 1 2 3 4 5 0

접두사      접미사      일치여부
-------   -------    -----
a         b          X
ab        ab         ✅
abc       cab        X
abca      bcab       X
abcab     abcab      ✅ → 현재 매칭된 영역 (pi[7]=5는 abcab까지)
abcabc    cabc       X
abcabca   bcabc      X
abcabcab  abcabcab   X (전체 문자열은 제외 = proper prefix/suffix 규칙)

따라서 미스매치될때마다 마지막으로 일치했던 구간으로 jump
즉 인덱스 2로 j가 점프한다. 거기서도 s[i]=x s[j]=c 이므로 매치되지 않으니
j가 인덱스 0로 점프한다

최종적으로 i=8 j=0

pi[i] = 0
```

# Reference