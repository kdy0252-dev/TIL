---
id: Intellij 잊어먹기 쉬운 단축키
started: 2025-05-13
tags:
  - ✅DONE
group:
  - "[[Editer]]"
---
# Intellij 잊어먹기 쉬운 단축키

단축키는 많이 외우는 것보다 반복 작업을 키보드에서 끊지 않는 데 목적이 있다. 아래 표기는 macOS 기본 Keymap 기준이며 IntelliJ 설정, OS 단축키와 Plugin에 따라 달라질 수 있다. `Preferences → Keymap`의 검색창에서 Action 이름으로 현재 Binding을 확인한다.

## Code Folding

- 커서 기준 메소드 펼치기, 닫기
	- Mac : Cmd + `+` / Cmd + `-`
- 코드 전체 펼치기, 접기
	- Mac : Cmd + Shift + `+` / Cmd + Shift + `-`

Code Folding은 긴 File을 탐색할 때 유용하지만, 접힌 코드가 Review와 Debugging에서 보이지 않는 비용도 있다. Method가 항상 접어야 읽힐 정도라면 Folding보다 Class와 Method 책임을 나눌 신호인지 살펴본다.

## Action 이름으로 단축키 찾기

`Cmd + Shift + A`의 **Find Action**에서 `Collapse`, `Expand`, `Reformat Code` 같은 Action을 검색하면 단축키를 기억하지 못해도 실행할 수 있다. 단축키가 충돌하면 Keymap에서 기존 Binding과 OS 예약 키를 확인하고 팀 공용 문서에는 Action 이름도 함께 기록한다.

## 자주 쓰는 탐색 흐름

- `Shift` 두 번: Class, File, Symbol과 Action을 통합 검색한다.
- `Cmd + B`: 선언으로 이동한다.
- `Option + F7`: 사용 위치를 찾는다.
- `Cmd + E`: 최근 File을 연다.
- `Cmd + Option + Left/Right`: 이전·다음 탐색 위치로 이동한다.

정확한 키는 Keymap마다 달라지므로 “선언으로 이동”처럼 의도와 Action 이름을 함께 익히는 편이 다른 OS로 옮길 때도 유용하다.

# Reference
[IntelliJ IDEA - Keyboard shortcuts](https://www.jetbrains.com/help/idea/mastering-keyboard-shortcuts.html)
[IntelliJ IDEA - Code folding](https://www.jetbrains.com/help/idea/working-with-source-code.html#code_folding)
