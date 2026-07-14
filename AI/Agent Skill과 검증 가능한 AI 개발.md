---
id: Agent Skill과 검증 가능한 AI 개발
started: 2026-07-13
tags:
  - ✅DONE
  - AI
  - Coding-Agent
  - Agent-Skill
  - Verification
group:
  - "[[AI]]"
---

# Agent Skill과 검증 가능한 AI 개발

LLM은 Code를 빠르게 생성하지만 자신이 만든 결과가 저장소 규칙을 만족하는지 안정적으로 판정하지 못한다. 자연어 자기 검토만 반복하면 같은 모델이 같은 오해를 다시 승인할 수 있다.

이 문제를 줄이는 방법이 **Agent Skill**과 결정론적 검증을 결합하는 것이다. Skill은 특정 작업에 필요한 판단 기준과 실행 절차를 재사용 가능한 단위로 만들고, Compiler·Test·Static Analysis는 결과를 객관적인 신호로 돌려준다.

---

## 1. Skill은 Prompt 조각이 아니다

Skill은 “깔끔하게 Review해라” 같은 짧은 지시가 아니라 하나의 작은 운영 절차다.

```text
입력 조건
  -> 조사할 파일
  -> 판단 규칙
  -> 실행할 Script
  -> 결과 해석
  -> 실패 시 수정과 재검증
```

예를 들어 Database Schema Guard Skill은 다음 질문에 답해야 한다.

- 어떤 변경이 Schema 변경으로 간주되는가?
- Entity와 Migration 사이를 어떻게 연결하는가?
- 기존 Migration을 수정해도 되는가?
- 새 Changelog의 순서는 어떻게 검증하는가?
- 실패 결과를 어떤 형태로 보고하는가?

이 정도로 구체적이어야 다른 Agent와 새 세션에서도 같은 절차를 재현할 수 있다.

---

## 2. Skill의 기본 구조

저장소 안에 Skill을 두면 Code와 함께 Versioning하고 Review할 수 있다.

```text
.agent/skills/liquibase_check/
├── SKILL.md
├── definition.json
└── scripts/
    └── check_liquibase.sh
```

`SKILL.md`는 언제 이 Skill을 사용하는지, 필요한 입력, 검사 항목과 실패 처리 방식을 설명한다. `definition.json` 같은 Metadata는 UI나 Agent Runtime이 Parameter를 받을 때 사용할 수 있다. 반복 가능한 검사는 Script로 구현한다.

자연어 판단과 Script의 역할을 구분하는 것이 중요하다.

| 종류 | 적합한 작업 |
|---|---|
| 자연어 판단 | 이름이 업무 의도를 드러내는가, 책임 분리가 적절한가 |
| 정적 Script | 금지 Import, Package 구조, Annotation 존재 여부 |
| Compiler | Type, Method Signature, 의존성 오류 |
| Test | 관측 가능한 동작과 회귀 |
| Architecture Test | Layer와 Module 의존 방향 |

정규식으로 Domain 설계 품질을 모두 판정하려 하면 False Positive가 많아지고, 자연어로 Import 규칙을 검사하면 누락이 생긴다.

---

## 3. 작은 Skill을 조합하기

하나의 거대한 `code_review` Skill보다 목적이 명확한 작은 Skill이 결과를 해석하기 쉽다.

```text
구조: tree_preview, vertical_slice_check, architectural_layer_check
모델: domain_model_check, value_object_check
경계: either_return_check, named_interface_check
표현: fqcn_check, lambda_naming_check, method_reference_check
영속성: liquibase_check, migration_order_check
Web: validation_check, web_adapter_check
최종: checkstyle, compile, test
```

작게 나누면 변경 종류에 맞는 최소 검증만 선택할 수 있다. Markdown 수정에 Java Domain 검사를 모두 실행할 필요는 없다. 반대로 Entity 변경은 Compile만 성공했다고 끝낼 수 없다.

Skill 이름과 책임이 겹치면 어느 쪽이 Source of Truth인지 불분명해진다. 이름 표기 차이로 같은 Skill이 두 개 생기지 않도록 Catalog와 Naming Convention을 관리한다.

---

## 4. 검증 순서는 비용과 Feedback을 고려한다

검사는 빠르고 국소적인 것부터 느리고 넓은 것으로 진행한다.

```text
1. 변경 파일 형식과 금지 Pattern
2. Package·Architecture 경계
3. Module Compile
4. 영향받은 Unit Test
5. Integration Test
6. 전체 Build
```

처음부터 전체 Build를 실행하면 단순 Formatting 오류도 늦게 발견한다. 반대로 빠른 검사만 통과하고 전체 Test를 생략하면 Module 간 회귀를 놓친다. 변경 위험에 비례해 검증 범위를 넓혀야 한다.

Build 실패를 다룰 때도 전체 Log를 Context에 넣는 대신 첫 Root Cause, 실패 Task와 관련 Stack Trace를 추출한다. Log가 너무 크면 중요한 Error가 Context에서 밀려날 수 있다.

---

## 5. Closed-loop Agent Workflow

검증 가능한 AI 개발은 Code 생성으로 끝나지 않고 Feedback Loop를 완성한다.

```text
요구사항 이해
  -> 기존 Code와 Test 조사
  -> 최소 변경
  -> 정적 검사
  -> Compile·Test
  -> 실패 원인 분석
  -> 수정
  -> 같은 검사 재실행
  -> Diff Review
```

핵심은 실패한 검사를 수정 후 반드시 다시 실행하는 것이다. “문제를 고쳤으니 통과할 것”이라는 설명은 증거가 아니다. 최종 응답에는 실행한 검증과 실행하지 못한 검증을 구분해 기록한다.

---

## 6. Architecture 규칙을 실행 가능하게 만들기

“Hexagonal Architecture를 따른다”는 문장만으로는 팀마다 해석이 다르다. 이를 검사 가능한 규칙으로 분해해야 한다.

- Domain은 Web DTO와 JPA Entity를 참조하지 않는다.
- Inbound Adapter는 공개 In Port를 통해 Application을 호출한다.
- Persistence Adapter는 Out Port를 구현한다.
- 다른 Vertical Slice의 구현 Package를 직접 참조하지 않는다.
- 외부 공개 계약은 Named Interface로 명시한다.

Directory 검사 Script는 Layer 누락을 빠르게 찾을 수 있지만 Package 간 실제 의존성까지 보장하지는 못한다. ArchUnit이나 jMolecules 같은 Architecture Test와 함께 사용해야 한다.

---

## 7. Skill이 실패하기 쉬운 경우

### 문서와 Script가 다르다

`SKILL.md`는 A를 검사한다고 설명하지만 Script는 오래된 Package 이름만 검색할 수 있다. Skill 자체에도 Test Fixture와 예상 결과가 필요하다.

### 규칙이 지나치게 절대적이다

모든 `if`와 `for`를 실패로 판정하면 상태 머신, 성능이 중요한 Loop와 Guard Clause까지 나쁜 Code로 취급한다. 자동 검사는 결함 가능성이 높은 범위에 집중하고 판단이 필요한 경우 Review 항목으로 남긴다.

### Production Code를 Test에 맞춘다

Test 작성 편의를 위해 Production Constructor의 Visibility를 넓히거나 Setter를 추가하면 검증이 설계를 훼손한다. Fixture와 Test Builder가 Production Boundary를 따라야 한다.

### 검증이 변경 범위와 무관하다

Agent가 항상 같은 10개 검사를 기계적으로 실행하면 비용이 커지고 신호가 약해진다. 변경 파일과 Dependency Graph를 기준으로 검증 Matrix를 선택한다.

---

## 8. Skill의 품질을 측정하기

Skill도 운영하면서 개선해야 한다.

- 실제 결함을 얼마나 잡았는가?
- 정상 Code를 잘못 실패시키는 비율은 얼마인가?
- 사람이 반복해서 지적하는데 Skill이 놓치는 것은 무엇인가?
- 평균 실행 시간과 실패 후 복구 시간은 얼마인가?
- 특정 Agent 제품 없이도 절차를 실행할 수 있는가?

좋은 Skill은 모델을 더 창의적으로 만드는 것이 아니라 결과의 편차를 줄인다. 개인의 암묵적인 Review 습관을 팀이 실행할 수 있는 Engineering Asset으로 바꾼다.

---

## 마무리

AI가 작성한 Code를 신뢰하는 가장 좋은 방법은 AI에게 자신감을 묻는 것이 아니다. 저장소의 규칙을 Skill로 구조화하고 Compiler, Test와 Architecture Check가 반증할 기회를 주는 것이다.

Agent Skill의 최종 목표는 자동화 개수를 늘리는 데 있지 않다. **실패를 빠르게 발견하고, 원인을 설명하며, 수정 후 같은 조건에서 다시 증명하는 개발 Loop**를 만드는 데 있다.

---

# Reference

- [OpenAI Codex - Agent Skills](https://developers.openai.com/codex/skills/)
- [ArchUnit User Guide](https://www.archunit.org/userguide/html/000_Index.html)
- [[AI Coding Agent를 위한 Context Engineering]]
- [[Vibe Coding의 Guardrail과 권한 설계]]
