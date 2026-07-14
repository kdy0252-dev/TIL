---
id: Vertical Slice와 Modular Monolith
started: 2026-05-24
tags:
  - ✅DONE
  - Architecture
  - Modular-Monolith
group:
  - "[[Java Spring Architecture]]"
---
# Vertical Slice와 Modular Monolith

## 1. 개요 (Overview)
**Vertical Slice Architecture**는 Controller·Service·Repository를 전역 레이어별로 모으지 않고 하나의 업무 기능에 필요한 코드를 같은 Slice에 배치합니다. **Modular Monolith**는 이런 Slice의 경계를 엄격히 유지하면서 하나의 Process로 배포합니다.

```text
Layer-first                    Slice-first
controller/                    booking/
service/                         adapter/
repository/                      application/
domain/                        driving/
                                adapter/
                                application/
```

---

## 2. 장점
- 한 기능 변경에 필요한 파일이 같은 경계에 모입니다.
- 도메인별 용어와 모델을 독립적으로 발전시킬 수 있습니다.
- 다른 Slice의 내부 구현 참조를 금지하기 쉽습니다.
- 향후 서비스 분리 시 경계 후보가 명확합니다.
- 단일 Process와 Transaction의 운영 단순성을 유지합니다.

---

## 3. Slice 내부의 Hexagonal Architecture
Vertical Slice와 Hexagonal Architecture는 경쟁 관계가 아닙니다. 각 Slice를 작은 Hexagon으로 구성할 수 있습니다.

```text
booking
  adapter.in.web
      -> application.port.in
          -> application.domain
              -> application.port.out
                  <- adapter.out.persistence
```

모든 작은 CRUD에 과도한 Port를 만들기보다, 외부 기술 교체·테스트 격리·Module 공개 계약에 가치가 있는 경계를 우선합니다.

---

## 4. 공개 계약과 Named Interface
다른 Slice가 내부 Service를 직접 참조하면 Module 경계가 무너집니다. 외부에 필요한 Use Case만 명시적으로 공개합니다.

```java
@NamedInterface("v3/member/lookup")
public interface MemberLookupUseCase {
    Optional<MemberInfo> find(Long memberId);
}
```

```text
driving -> member.application.port.in.method  허용
driving -> member.application.domain.service 금지
driving -> member.adapter.out.persistence    금지
```

공개 계약은 내부 Domain Model보다 안정적인 Resource·Value Object를 반환해야 합니다.

---

## 5. 결합 유형

| 결합 | 통제 방법 |
|---|---|
| Compile-time | Public Package와 Named Interface 제한 |
| Runtime | Event 또는 Port 호출 정책 |
| Data | 공유 Table 직접 접근 금지, 소유 Slice를 통한 접근 |
| Transaction | 동기 호출 범위와 Outbox 경계 결정 |
| Deployment | 하나의 Artifact지만 독립 Module 규칙 유지 |

---

## 6. 실무 사례 적용 관점
이 사례는 회원, 예약, 배차, 운행, 차량, 결제 등 업무 Package를 Top-level Module로 두고 각 내부에 Adapter·Port·Domain을 배치합니다. Spring Modulith의 `@NamedInterface`와 Architecture Test로 Slice 간 접근을 제한합니다.

Orchestrator Slice는 여러 Slice의 공개 Use Case를 조합하지만, 해당 Slice의 내부 Service나 Repository에 접근하지 않습니다.

---

## 7. 분리 시점
다음 조건이 누적될 때 Microservice 분리를 검토합니다.

- 독립적인 확장·배포 주기가 필요합니다.
- 데이터 소유권이 명확하고 분산 Transaction 비용을 감당할 수 있습니다.
- 팀 소유권과 장애 격리가 실제 이점을 제공합니다.
- Network 호출, Eventual Consistency, 운영 비용보다 분리 이점이 큽니다.

---

## 8. Slice 경계 찾기
화면이나 Table이 아니라 업무 Capability와 언어를 기준으로 나눕니다.

- 함께 변경되는 규칙
- 동일한 Transaction 불변식
- 명확한 데이터 소유권
- 다른 팀·업무 용어
- 독립적인 변화 속도

너무 작은 Slice는 계약과 Mapper만 늘리고, 너무 큰 Slice는 내부 결합을 숨깁니다.

## 9. 데이터 소유권
한 Table은 하나의 Slice가 소유합니다. 다른 Slice가 필요하면 공개 Query Port나 Event로 데이터를 얻습니다.

같은 DB를 사용한다고 Cross-slice Join을 무제한 허용하면 코드 경계보다 강한 데이터 결합이 생깁니다. Reporting처럼 예외가 필요한 경우 Read Model과 소유권을 명시합니다.

## 10. 동기 호출과 Event

| 요구 | 방식 |
|---|---|
| 즉시 결과가 업무 결정에 필요 | 공개 Use Case 동기 호출 |
| 후속 처리·알림 | Event·Outbox |
| 대량 조회·통계 | Read Model·Projection |
| 강한 불변식 | 같은 Aggregate·Transaction 경계 재검토 |

모듈 간 Event가 무조건 느슨한 결합을 만들지는 않습니다. Event Schema와 순서, 재처리도 계약입니다.

## 11. Package Visibility
Java Package-private, Public Interface 전용 Package와 ArchUnit을 조합합니다. 모든 클래스를 Public으로 두고 문서로만 "내부"라고 표시하지 않습니다.

## 12. Module API 설계
공개 API는 내부 Entity보다 안정적인 Command·Resource·Value Object를 사용합니다. 너무 일반적인 CRUD Service보다 업무 의도가 드러나는 Method가 좋습니다.

```text
memberRepository.findById()       나쁨: 내부 Persistence 노출
memberLookupUseCase.findContact() 좋음: 필요한 계약 노출
```

## 13. 순환 의존성
Booking → Driving → Booking 같은 Cycle은 경계가 잘못됐거나 Orchestrator가 필요하다는 신호입니다.

- 상위 Orchestrator로 흐름 이동
- 공통 개념을 독립 Value Object로 추출
- Event로 시간적 결합 분리
- Module 책임 재조정

공통 Module에 모든 것을 옮겨 Cycle을 숨기지 않습니다.

## 14. 테스트
- Slice Domain Unit Test
- Port Contract Test
- Persistence Adapter Integration Test
- Spring Modulith Module Test
- 전체 Architecture Dependency Test

Module Test는 필요한 인접 Module만 Bootstrap하여 전체 Context보다 빠르게 검증할 수 있습니다.

## 15. 진화 전략
처음부터 Microservice 분리를 가정한 Network DTO와 Broker를 모든 경계에 넣지 않습니다. Process 내부 계약을 명확히 하고 실제 분리가 필요할 때 Anti-corruption Adapter와 Remote Contract를 추가합니다.

## 16. Review 체크리스트
- 변경이 한 Slice 안에 응집되는가?
- 다른 Slice의 Adapter·Domain Service를 직접 참조하는가?
- 공개 계약이 내부 모델을 누출하는가?
- Table 소유자가 명확한가?
- Cycle과 Shared Kernel이 증가하는가?

---

## 17. 실무 사례 적용 진단과 개선 과제

이 사례는 업무 Package별 Slice와 `application.port.in.method` 계약, Named Interface 검사를 사용합니다. 그러나 Test의 TODO가 보여주듯 공개 Port와 Orchestrator Package의 최종 규칙이 전환 중이며, 검색·조립 Use Case는 다른 Slice의 데이터를 다수 결합합니다.

부족한 점은 Slice간 허용 의존성이 예외 목록에 기대면 시간이 지나며 경계가 느슨해질 수 있다는 것입니다. 해결하려면 Slice별 `package-info.java` 공개 API를 최소화하고, 다른 Slice의 Domain·Adapter 직접 참조를 전수 검사하며, 결합 조회는 전용 Query Contract 또는 Read Model로 모읍니다.

완료 기준은 Cross-slice Compile Dependency가 공개 Inbound Contract로만 제한되고, ArchUnit/Modulith Verification이 전체 Module에서 실행되며, 예외마다 Owner·만료일·제거 Issue가 있는 상태입니다.

---

# Reference
- [Spring Modulith](https://docs.spring.io/spring-modulith/reference/)
- [[Spring Modulith]]
- [[Hexagonal Architecture]]
- [[jMolecules와 ArchUnit]]
