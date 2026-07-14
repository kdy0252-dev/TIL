---
id: Projection과 Hydration
started: 2026-05-20
tags:
  - ✅DONE
  - JPA
  - DDD
  - Architecture
group:
  - "[[Java Spring DB JPA]]"
---
# Projection과 Hydration: 조회 모델과 도메인 복원

## 1. 개요 (Overview)
**Projection**은 원본 데이터의 일부 필드나 계산 결과를 목적에 맞는 형태로 투영하는 것입니다. **Hydration**은 DB Row나 직렬화 데이터로 객체의 상태를 채우는 과정입니다. DDD에서는 저장된 상태로 Domain Object를 다시 만드는 과정을 **Reconstitution(재구성·복원)**이라고 더 명확히 부르기도 합니다.

```text
Read Path:  Table -> Projection -> Query Row -> Resource
Write Path: Table -> Entity/Data -> Reconstitution -> Domain Model
```

같은 DB 조회라도 목록 화면을 만드는 것과 Aggregate의 비즈니스 로직을 실행하기 위해 복원하는 것은 목적이 다릅니다.

---

## 2. Projection

### 2.1 Interface Projection

```java
public interface MemberSearchProjection {
    Long getId();
    String getName();
    String getMobileNumber();
}
```

필요한 Column만 조회하여 목록 API의 메모리와 Network 비용을 줄일 수 있습니다.

### 2.2 DTO·Record Projection

```java
public record MemberSearchRow(Long id, String name, String mobileNumber) {
}
```

Constructor Projection은 결과 구조가 명시적이고 Persistence Framework 외부로 전달하기 쉽습니다.

### 2.3 Dynamic Projection

```java
<T> List<T> findByStatus(MemberStatus status, Class<T> projectionType);
```

같은 조건에 여러 Projection을 사용할 수 있지만, 호출자가 Persistence 세부 타입을 선택하게 되면 경계가 흐려질 수 있습니다.

---

## 3. Hydration과 Reconstitution
ORM은 기본 Constructor와 Reflection을 사용하여 JPA Entity를 Hydration합니다. Domain Model은 ORM Hydration과 분리하고 명시적인 `load()` 또는 `reconstitute()` Factory로 복원할 수 있습니다.

```java
public static Member reconstitute(
        Long id,
        MemberStatus status,
        MemberProfile profile,
        Audit audit
) {
    return new Member(id, status, profile, audit);
}
```

```java
public Member toDomain(MemberJpaEntity entity) {
    return Member.reconstitute(
            entity.getId(),
            entity.getStatus(),
            profileMapper.toDomain(entity),
            auditMapper.toDomain(entity)
    );
}
```

`create()`는 새로운 Identity와 기본 상태를 만들고 비즈니스 생성 규칙을 검증합니다. `reconstitute()`는 이미 검증되어 저장된 상태를 복원하므로 두 Factory의 의미를 섞지 않아야 합니다.

---

## 4. Mapper의 역할

| 변환 | 담당 |
|---|---|
| HTTP Request → Command | Web Adapter |
| JPA Entity → Persistence Data | Persistence Mapper 또는 MapStruct |
| Persistence Data → Domain | Domain `load()` / `reconstitute()` |
| Query Projection → Resource | Query Adapter·Assembler |
| Domain → JPA Entity | Persistence Mapper |

Mapper가 DB를 추가 조회하거나 업무 정책을 판단하면 Mapping과 Orchestration이 섞입니다.

---

## 5. Projection과 CQRS
조회 API는 화면에 필요한 데이터를 여러 Table에서 직접 Projection할 수 있습니다. 이때 Domain Aggregate를 모두 Hydration한 뒤 Getter로 DTO를 만드는 과정은 불필요할 수 있습니다.

```text
Command Side
  JPA Entity -> Reconstitution -> Aggregate -> Business Method -> Save

Query Side
  SQL / QueryDSL / jOOQ -> Projection -> Resource
```

Projection은 Domain 규칙을 우회하여 상태를 변경하는 용도로 사용하지 않습니다. 쓰기는 Aggregate를 복원한 뒤 비즈니스 메서드를 호출합니다.

---

## 6. 실무 사례 적용 관점
이 사례는 회원 검색에서 Interface Projection으로 필요한 Row만 읽고, 상세 업무 처리에서는 Persistence Mapper가 `Member.reconstitute()`를 호출합니다. 여러 Domain Model은 `Data`를 받는 정적 `load()` Factory를 사용합니다. Metrics는 jOOQ Query 결과를 통계 Snapshot과 Query Model로 직접 투영합니다.

이 세 방식은 목적에 따라 구분됩니다.

- **검색 목록**: 가벼운 Projection
- **업무 상태 변경**: 완전한 Aggregate Reconstitution
- **통계 조회**: SQL 집계 결과를 Read Model로 Projection

---

## 7. 흔한 실수
- 모든 조회에서 Entity 전체를 Hydration하여 N+1과 메모리 낭비를 만듭니다.
- Projection Interface를 Application Core의 공용 모델로 사용합니다.
- `create()`를 복원에도 사용하여 ID나 기본값을 다시 생성합니다.
- Mapper가 Setter로 Domain 불변식을 우회합니다.
- Lazy Proxy가 Web 응답 직렬화 시점에 초기화됩니다.

---

## 8. Closed와 Open Projection
Spring Data Interface Projection은 단순 Getter만 있으면 필요한 Column을 최적화할 수 있는 Closed Projection입니다. SpEL이나 Entity 전체가 필요한 계산이 들어가면 Open Projection이 되어 최적화가 제한될 수 있습니다.

Projection에 복잡한 계산을 넣기보다 Query에서 계산하거나 Application Assembler로 이동합니다.

## 9. Nested Projection
연관 객체의 Nested Projection은 편리하지만 Join과 Hydration 범위가 커질 수 있습니다. To-many 관계를 중첩하면 Row 중복과 N+1을 확인합니다.

목록 API는 Root ID Page를 먼저 조회하고 관련 데이터를 `IN` Batch로 가져와 조립하는 방식이 안정적일 수 있습니다.

## 10. Entity Hydration 과정

```text
ResultSet
  -> Entity Instance 생성
  -> Basic Field 주입
  -> Persistence Context 등록
  -> Association Proxy 연결
  -> 필요 시 Lazy Initialization
```

Hydrated Entity는 Persistence Context에서 Identity Map과 Dirty Checking의 대상입니다. Read-only 조회에서도 Entity 수가 많으면 Memory와 Snapshot 비용이 발생합니다.

## 11. Partial Entity 문제
일부 Column만 Entity Constructor에 채워 "가벼운 Entity"를 만들면 미조회 필드와 실제 null을 구분하기 어렵고 저장 시 데이터 손실 위험이 있습니다. 일부 조회는 Entity가 아니라 Projection Type을 사용합니다.

## 12. Reconstitution 불변식
저장 데이터도 손상되었을 수 있습니다. `reconstitute()`가 어느 수준의 검증을 할지 정합니다.

- 구조적으로 불가능한 값은 거부
- 역사적으로 허용되던 Legacy 상태는 별도 Migration
- 현재 생성 규칙과 과거 복원 규칙을 구분

복원 실패는 단순 500이 아니라 데이터 무결성 Alert로 관측합니다.

## 13. Aggregate 조립
Aggregate가 여러 Table로 저장되면 Persistence Adapter가 Row를 모아 Data 구조를 만든 뒤 Domain Factory를 호출합니다.

```text
Root Entity + Children + Value Rows
  -> AggregateData
  -> Aggregate.reconstitute(data)
```

Domain이 JPA Collection·Proxy를 직접 받지 않게 합니다.

## 14. Snapshot
변경 가능한 원본의 특정 시점 상태를 통계·감사에 보존할 때 Snapshot Model을 사용합니다. Snapshot은 현재 Aggregate를 다시 Hydration하는 것과 다르게 당시 의미를 고정합니다.

사례의 Metrics의 Usage Purpose Snapshot은 원본 변경 이후에도 집계 의미를 재현하는 데 사용될 수 있습니다.

## 15. Read Model Hydration
Redis나 JSON에서 조회 Resource를 복원하는 것도 넓은 의미의 Hydration입니다. 이 객체는 Domain Aggregate가 아니므로 Business Method를 제공하지 않고 조회 계약에 집중합니다.

## 16. Lazy Loading과 OSIV
OSIV를 끄면 Web 직렬화 시점의 암묵적 Lazy Loading을 막을 수 있습니다. Application Transaction 안에서 필요한 데이터를 명시적으로 조회하고 Resource로 변환합니다.

## 17. 성능 비교

| 방식 | SQL Column | Persistence Context | 용도 |
|---|---|---|---|
| Entity Hydration | 전체 또는 다수 | 사용 | 상태 변경 |
| Interface Projection | 필요 필드 | 제한적 | 단순 목록 |
| DTO Projection | 필요 필드 | 없음 | API·통계 조회 |
| jOOQ Row | 명시 필드·집계 | 없음 | 복잡한 SQL |

## 18. 테스트
- Projection Query가 필요한 Column만 조회하는지 확인합니다.
- Lazy Association 추가 Query 수를 검사합니다.
- Entity→Data→Domain 복원 결과를 검증합니다.
- `create()`와 `reconstitute()`의 ID·기본값 차이를 확인합니다.
- 손상된 저장 상태의 처리 정책을 테스트합니다.
- Read Model이 Domain 변경 경로로 사용되지 않는지 Architecture Test로 막습니다.

---

## 19. 실무 사례 적용 진단과 개선 과제

Member·Booking·Driving 조회는 Interface Projection과 Batch Loader를 적극 사용해 전체 Entity Hydration과 N+1을 줄이고 있습니다. 다만 하나의 조회 Use Case가 여러 Projection과 Map 조립을 거치며, 큰 `*-all` 조회와 Count Query는 데이터 증가 시 비용이 커질 가능성이 있습니다.

해결하려면 주요 Endpoint별 Query 수, 반환 Row, Hydrated Entity 수, Heap과 P95를 Baseline으로 남깁니다. 무제한 `all`은 상한·Cursor·Export Job으로 바꾸고, Projection Field 변경은 Query/Assembler Contract Test로 보호합니다. 쓰기 흐름에는 부분 Projection을 Entity처럼 저장하지 않는 규칙을 Arch Review에 포함합니다.

완료 기준은 주요 목록 API가 고정된 Query 수로 동작하고 데이터 10배 Test에서도 Heap과 P95 기준을 만족하며, OSIV 없이 LazyInitializationException과 N+1이 재현되지 않는 상태입니다.

---

# Reference
- [[k6 부하 테스트와 성능 검증]]
- [Spring Data JPA Projections](https://docs.spring.io/spring-data/jpa/reference/repositories/projections.html)
- [[CQRS Pattern]]
- [[RSQL과 QueryDSL 동적 검색]]
- [[jOOQ 타입 안전 SQL]]
- [[MapStruct]]
