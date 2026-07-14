---
id: VIM 잊어먹기 쉬운 커맨드
started: 2025-03-14
tags:
  - ✅DONE
  - vim
group:
  - "[[Editer]]"
---
# VIM 잊어먹기 쉬운 커맨드

Vim 명령은 `동작 횟수 + Operator + 범위`라는 문법으로 이해하면 암기량이 줄어든다. 예를 들어 `3dw`는 세 단어를 삭제하고 `ci"`는 따옴표 내부를 바꾼다. 명령 전에는 Normal Mode인지 확인하고, 실수하면 `u`로 되돌린다.

## 커맨드
- **r** : 문자 1개 변경
- **%s/바꿔질문자/바꿀문자/g** : 해당 문자 모두 변경
- **f** : 커서 이후의 문자 찾기
- **F** : 커서 이전의 문자 찾기
- **ctrl + a** : 숫자 1 증가
- **ctrl + x** : 숫자 1 감소
- **{** : 커서 이전의 공백이 있는 라인으로 이동
- **}** : 커서 이후의 공백이 있는 라인으로 이동
- **;** : 마지막 `f`, `F`, `t`, `T` 탐색을 같은 방향으로 반복
- **,** : 마지막 문자 탐색을 반대 방향으로 반복
- **qq ... q** : `q` Register에 Macro 기록
- **@q** : `q` Register Macro 실행
- **10@q** : Macro를 열 번 실행

`.`은 마지막 변경을 반복하고 `;`은 마지막 문자 탐색을 반복하므로 역할이 다르다.

## 치환 범위 이해하기

```vim
:%s/old/new/g
:%s/old/new/gc
:'<,'>s/old/new/g
```

`%`는 전체 File, `g`는 한 줄의 모든 일치 항목, `c`는 각 변경 전 확인을 뜻한다. Search 문자열에 `/`가 많다면 `:%s#old/path#new/path#g`처럼 다른 구분자를 사용할 수 있다. 정규식 Meta Character와 Literal 문자열을 구분하고 중요한 변경은 `c` Option으로 먼저 확인한다.

## Register와 Clipboard

Delete도 Register에 저장되므로 단순 삭제 뒤 붙여넣을 값이 바뀔 수 있다. `"_d`는 Black-hole Register로 삭제하고, `"+y`와 `"+p`는 System Clipboard가 지원되는 Vim에서 복사·붙여넣기한다.

## Macro를 안전하게 쓰기

Macro는 각 줄의 길이가 달라도 견디도록 `0`, `^`, `f`, `w` 같은 상대 이동을 사용한다. 여러 줄에 실행하기 전 한 줄에서 기록하고 다음 줄에서 재생해 결과를 확인한다. 실패 중에는 `Ctrl-C`로 중단하고 `u`로 변경을 되돌린다.

# Reference
[Vim Documentation](https://vimhelp.org/)
[Vim Help - Change](https://vimhelp.org/change.txt.html)
