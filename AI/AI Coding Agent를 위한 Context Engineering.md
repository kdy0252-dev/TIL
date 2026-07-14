---
id: AI Coding Agent를 위한 Context Engineering
started: 2026-07-12
tags:
  - ✅DONE
  - AI
  - Coding-Agent
  - Context-Engineering
group:
  - "[[AI]]"
---

# AI Coding Agent를 위한 Context Engineering

AI Coding Agent에게 “좋은 코드를 작성해 줘”라고 요청하는 것만으로는 팀의 코드가 만들어지지 않는다. 모델은 일반적인 Java와 Spring 지식은 알고 있지만, 특정 저장소가 Hexagonal Architecture를 어떻게 해석하는지, 어떤 Error 처리 방식을 선택했는지, 변경 후 어떤 검증을 통과해야 하는지는 알지 못한다.

이 차이를 메우는 작업이 **Context Engineering**이다. Prompt 한 문장을 정교하게 다듬는 Prompt Engineering보다 넓은 개념으로, Agent가 작업 중 필요한 규칙·Code·도구·실행 결과를 적절한 시점에 제공하는 환경을 설계한다.

---

## 1. Prompt보다 Context가 중요한 이유

같은 요청도 저장소에 따라 올바른 결과가 달라진다.

```text
"예약 조회 API를 추가해 줘"
```

Layered Architecture에서는 Controller가 Service를 직접 호출할 수 있지만, Port와 Adapter를 엄격히 나누는 저장소에서는 In Port를 통과해야 한다. 어떤 팀은 Exception을 던지고 다른 팀은 `Either`를 반환한다. Database Schema 변경에 Liquibase가 필요한지, Test Fixture를 어디에 둘지도 저장소 규칙에 따라 달라진다.

모델이 이런 차이를 추측하게 두면 결과가 매번 달라진다. Context Engineering은 추측해야 할 영역을 줄이고 저장소의 의사결정을 명시적인 입력으로 바꾼다.

---

## 2. 저장소 지침을 계층으로 나누기

모든 규칙을 하나의 거대한 파일에 넣으면 Agent가 핵심을 찾기 어렵고 서로 충돌하는 지침이 쌓인다. Context는 역할에 따라 계층화하는 편이 좋다.

```text
Repository Root
├── AGENTS.md                 # 진입점과 우선순위
├── .agent/
│   ├── guidelines.md         # 저장소 전체 규칙
│   ├── skills/               # 작업별 절차와 검증
│   └── workflows/            # 짧고 반복적인 실행 흐름
└── module/
    └── AGENTS.md             # 모듈에만 적용되는 예외
```

### 진입점

Root의 `AGENTS.md`는 짧아야 한다. Agent가 가장 먼저 읽어야 할 Source of Truth, 응답 언어, 금지 영역과 검증 명령으로 안내하는 역할이면 충분하다.

### 저장소 규칙

`guidelines.md`에는 Architecture Boundary, Naming, Error 처리, Persistence 규칙처럼 대부분의 변경에 적용되는 결정을 둔다. 단순 취향보다 위반했을 때 실제 결함을 만드는 규칙을 우선한다.

### 작업별 지식

Database Migration, Controller 작성, Domain Model Review처럼 특정 상황에만 필요한 절차는 Skill로 분리한다. Agent는 Entity를 수정할 때만 Migration Skill을 읽으므로 불필요한 Context 소비를 줄일 수 있다.

### 지역적 예외

특정 Module만 다른 Framework나 검증 명령을 쓴다면 가까운 위치의 지침으로 범위를 좁힌다. 전역 문서에 예외를 계속 추가하면 모든 작업이 복잡해진다.

---

## 3. 좋은 지침은 판단 기준을 설명한다

규칙만 나열하면 Agent는 비슷하지만 다른 상황에서 기계적으로 적용한다.

```text
나쁜 지침: for 문을 사용하지 않는다.

나은 지침: Collection의 변환·필터링은 Stream을 우선한다.
상태를 여러 번 갱신하거나 조기 종료가 중요한 Algorithm에서는
명령형 표현이 더 명확할 수 있으므로 이유를 설명하고 사용한다.
```

좋은 지침에는 보통 다음 요소가 있다.

- 규칙이 해결하려는 문제
- 적용되는 범위와 적용되지 않는 범위
- 올바른 예제와 Anti-pattern
- 위반 여부를 확인하는 방법
- 다른 규칙과 충돌할 때의 우선순위

예를 들어 “JPA Entity를 바꾸면 Migration을 추가한다”는 지침에는 Entity와 Changelog의 예제, 기존 Migration 수정 금지 여부, 검증 Script까지 연결할 수 있다.

---

## 4. Context의 중복과 충돌

AI 개발 환경은 시간이 지나며 `AGENTS.md`, 다른 Agent용 설정, Workflow와 Skill에 같은 규칙이 복사되기 쉽다. 복사본은 곧 서로 다른 사실이 된다.

한 문서는 표준 Java Collection을 사용하라고 하고 다른 Workflow는 모든 Collection에 별도 함수형 Library를 쓰라고 할 수 있다. 한 곳에서는 Application Service가 `Either`를 반환하지 말라고 하면서 다른 곳에서는 Domain 전체가 `Either`를 반환해야 한다고 적을 수도 있다.

모델은 충돌을 발견해도 항상 올바른 쪽을 선택하지 않는다. 따라서 다음 구조가 필요하다.

```text
한 규칙 = 한 Source of Truth
다른 문서 = 원문을 복사하지 않고 링크
충돌 시 = 우선순위를 진입점에 명시
예외 = 범위와 만료 조건을 기록
```

지침도 Code처럼 Review 대상이다. 이름이 다른 중복 Skill, 존재하지 않는 Agent를 가리키는 안내, 오래된 Version과 실행되지 않는 명령을 정기적으로 제거해야 한다.

---

## 5. Progressive Disclosure

모든 파일을 대화 시작 시 읽히는 것은 정확도를 높이는 방법처럼 보이지만 Context Window를 낭비하고 현재 작업과 무관한 규칙의 영향력을 키운다.

Progressive Disclosure는 필요한 순간에 필요한 깊이만 제공하는 방식이다.

```text
1. AGENTS.md에서 저장소의 지도를 읽는다.
2. 현재 작업과 관련된 Guidelines만 찾는다.
3. 해당 Skill의 전체 절차를 읽는다.
4. 수정 대상과 가까운 Code·Test를 조사한다.
5. 실행 결과를 새로운 Context로 사용한다.
```

여기서 중요한 점은 Skill을 선택했다면 일부만 훑지 않고 전체 절차를 읽는 것이다. 반대로 관련 없는 Skill까지 모두 불러오지는 않는다.

---

## 6. Code 자체를 Context로 사용하기

문서가 실제 Code와 다르면 Code가 더 강한 증거인 경우가 많다. Agent는 구현 전에 인접한 Feature를 찾아 Package 구조, Test 방식과 Naming을 확인해야 한다.

```text
지침: 원하는 Architecture의 의도
인접 Code: 현재 저장소의 실제 관례
Test: 외부에서 관측 가능한 계약
Build 결과: 변경이 성립하는지에 대한 증거
```

단, 기존 Code에 우연히 남은 예외 하나를 표준으로 오해할 수 있다. 여러 사례를 비교하고 Architecture Test나 공식 지침과 대조해야 한다.

---

## 7. Context에 넣지 말아야 할 것

Context File도 Repository에 저장되므로 Secret, 내부 Token, 운영 고객 데이터와 개인 경로를 넣지 않는다. Agent에게 필요한 것은 Credential 값이 아니라 Credential을 어떤 방식으로 참조하고 어떤 명령이 승인을 요구하는지에 대한 정책이다.

또한 다음 내용은 Context 품질을 낮춘다.

- 이유 없는 “항상”, “절대” 규칙
- 현재 저장소에 존재하지 않는 Tool과 Agent 이름
- 실행할 수 없는 추상적인 검증 요구
- 특정 작업에서 나온 일회성 경로와 임시 값
- 같은 내용을 표현만 바꿔 반복한 문단

---

## 8. Context 품질을 검증하는 방법

좋은 지침은 문서가 길다는 사실이 아니라 결과의 일관성으로 평가한다. 같은 유형의 작은 작업을 여러 번 수행해 다음을 비교할 수 있다.

- Architecture 위치를 올바르게 선택했는가?
- 불필요한 파일까지 수정하지 않았는가?
- 동일한 규칙 위반이 반복되는가?
- Agent가 어떤 검증을 왜 실행했는지 설명할 수 있는가?
- 새 세션에서도 유사한 결과가 나오는가?

반복해서 발생하는 Review 지적은 개인 Prompt로 보완할 것이 아니라 지침이나 자동 검증으로 승격할 후보가 된다.

---

## 마무리

AI Coding Agent의 품질은 모델 성능만으로 결정되지 않는다. 저장소의 의사결정을 얼마나 명확히 표현하고, 필요한 순간에 관련 Context를 제공하며, 실행 결과로 가정을 교정하는지가 더 큰 차이를 만든다.

Context Engineering의 목표는 Agent에게 모든 것을 알려주는 것이 아니다. **추측하면 위험한 결정을 명시하고, 나머지는 Code와 검증 결과에서 발견할 수 있게 만드는 것**이다.

---

# Reference

- [OpenAI Codex - AGENTS.md](https://developers.openai.com/codex/guides/agents-md/)
- [Anthropic - Claude Code Memory](https://docs.anthropic.com/en/docs/claude-code/memory)
- [[Agent Skill과 검증 가능한 AI 개발]]
- [[Vibe Coding의 Guardrail과 권한 설계]]
