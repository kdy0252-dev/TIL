---
id: RSQL과 QueryDSL 동적 검색
started: 2026-05-21
tags:
  - ✅DONE
  - Java-Spring
  - JPA
  - Query
group:
  - "[[Java Spring DB JPA]]"
---
# RSQL과 QueryDSL을 이용한 동적 검색

## 1. 개요 (Overview)
검색 API는 필터가 늘어날수록 Controller 파라미터와 Repository 메서드 조합이 폭발합니다. **RSQL**은 클라이언트가 필터 조건을 문자열 문법으로 표현하게 하고, **QueryDSL**은 서버에서 조건을 타입 안전한 Predicate와 SQL로 구성하게 합니다.

```text
HTTP filter
  -> RSQL Parser
  -> 검증된 검색 조건
  -> QueryDSL Predicate
  -> JPA Query
  -> Projection / Resource
```

RSQL은 외부 검색 언어이고 QueryDSL은 내부 쿼리 구성 도구입니다. 둘의 책임을 분리해야 외부 입력이 Persistence 구현으로 직접 침투하지 않습니다.

---

## 2. RSQL 문법

```text
status==ACTIVE
name==*kim*
createdAt=ge=2026-01-01
status=in=(ACTIVE,INACTIVE);centerId==100
```

- `;`: AND
- `,`: OR
- `==`, `!=`: 동등·부정
- `=gt=`, `=ge=`, `=lt=`, `=le=`: 범위 비교
- `=in=`, `=out=`: 집합 포함·제외

허용 필드와 연산자를 서버에서 화이트리스트로 제한해야 합니다. Entity 필드명을 그대로 공개하면 내부 모델 변경이 API 호환성 문제로 이어지고, 의도하지 않은 관계 탐색이나 고비용 쿼리가 허용될 수 있습니다.

---

## 3. QueryDSL 역할
QueryDSL은 생성된 Q-Type을 사용하여 문자열 기반 JPQL의 오타와 타입 오류를 컴파일 시점에 줄입니다.

```java
BooleanExpression condition = booking.status.eq(status)
        .and(booking.centerId.eq(centerId))
        .and(booking.createdAt.goe(startAt));

return queryFactory
        .select(booking.id, booking.status, booking.createdAt)
        .from(booking)
        .where(condition)
        .orderBy(booking.createdAt.desc())
        .fetch();
```

동적 조건은 `BooleanExpression`을 반환하는 작은 함수로 분리하고, null 조건은 `where()`에서 무시하도록 구성할 수 있습니다.

---

## 4. 실무 사례 적용 구조
이 사례의 `RsqlFilterSupport`는 외부 필터 문자열을 파싱하고, Slice별 Field Binding이 API 필드와 QueryDSL 경로를 연결합니다. 복합 검색은 Custom JPA Repository에서 실행합니다.

```text
Controller
  -> Search Command / Criteria
  -> RsqlFilterSupport
  -> Slice-specific Field Bindings
  -> CustomJpaRepository
  -> QueryDSL
```

공통 파서는 문법 처리에 집중하고, 각 Slice는 자신이 공개할 검색 필드와 타입 변환을 소유합니다. 이 구조는 공통 모듈이 모든 도메인의 필드를 아는 문제를 피합니다.

---

## 5. Projection과 결합
목록 조회에서 전체 Entity를 Hydration할 필요가 없다면 필요한 컬럼만 Projection으로 조회합니다.

```java
queryFactory
        .select(Projections.constructor(
                BookingSearchRow.class,
                booking.id,
                booking.status,
                booking.bookerName
        ))
        .from(booking)
        .where(condition)
        .fetch();
```

검색 결과는 쓰기 Domain Model이 아니라 조회 전용 Row·Resource로 반환하는 것이 CQRS 관점에서도 명확합니다.

---

## 6. 운영 주의사항
- 정렬 필드도 화이트리스트로 검증합니다.
- 관계 컬렉션 Fetch Join과 Paging을 동시에 사용하지 않습니다.
- 검색 깊이, 조건 수, `IN` 항목 수를 제한합니다.
- 와일드카드 선행 검색은 일반 B-Tree Index를 활용하기 어렵습니다.
- API 필드명과 Entity 필드명을 분리하여 Persistence 모델을 숨깁니다.
- 생성 SQL과 실행 계획을 부하 데이터 기준으로 검증합니다.

---

## 7. Parser와 AST
RSQL Parser는 문자열을 AND·OR·Comparison Node로 이루어진 AST로 변환합니다.

```text
status==ACTIVE;name==*kim*
  -> AndNode
      ├─ Comparison(status, ==, ACTIVE)
      └─ Comparison(name, ==, *kim*)
```

Visitor가 AST를 순회해 내부 검색 조건을 만듭니다. Parser Node를 Repository까지 그대로 넘기면 외부 문법이 Persistence에 결합되므로 중간 Criteria로 변환합니다.

## 8. Field Binding

```text
API field `centerId`
  -> 타입 Long
  -> 허용 연산 [==, =in=]
  -> QueryDSL path booking.centerId
```

Field별 타입 변환, 허용 연산, 정렬 가능 여부와 비용 등급을 정의합니다. 사용자가 임의의 Nested Path를 만들지 못하게 합니다.

## 9. BooleanExpression 조합
AND·OR 우선순위를 AST 구조대로 보존합니다. 문자열을 단순 Split하면 괄호와 Escape를 잘못 처리하기 쉽습니다.

빈 조건의 의미를 전체 조회로 할지 오류로 할지 API 정책을 정합니다. 관리자 API라도 무제한 전체 조회는 위험합니다.

## 10. Wildcard와 Escape
RSQL `*`를 SQL `%`로 바꿀 때 사용자가 보낸 `%`, `_`, Escape 문자를 처리합니다. 단순 문자열 결합이 아니라 Bind Parameter와 명시적인 Escape를 사용합니다.

## 11. 날짜와 Time Zone
날짜만 받은 조건과 Instant 조건을 구분합니다.

```text
createdDate==2026-07-14
  -> Asia/Seoul 00:00 이상
  -> 다음 날 00:00 미만
  -> UTC Instant로 변환
```

`<= 23:59:59.999`보다 반개구간을 사용합니다.

## 12. Pagination 안정성
동일 정렬 값이 많으면 Page 사이에 중복·누락이 생길 수 있습니다. 마지막 Tie-breaker로 Unique ID를 추가합니다.

대규모 Offset Pagination은 뒤 Page로 갈수록 느려지므로 Cursor 방식도 검토합니다.

## 13. Count Query
Spring Page는 전체 Count Query를 추가 실행합니다. 복잡한 Join에서 Count가 본 조회보다 비쌀 수 있습니다. Total이 필요 없는 화면은 Slice·Cursor를 사용합니다.

## 14. QueryDSL Fetch Join
To-one Fetch Join은 N+1을 줄일 수 있지만 To-many Collection Fetch Join과 Paging 조합은 Row 폭증과 Memory Paging을 만들 수 있습니다. ID Page 조회 후 필요한 데이터를 Batch 조회하는 2단계 전략을 사용합니다.

## 15. 보안과 DoS
- Filter 문자열 길이
- AST Node 수와 중첩 깊이
- IN 항목 수
- 조회 기간
- Page Size
- 허용 Sort

를 제한하고 고비용 필드에는 별도 권한이나 API를 둡니다.

## 16. 테스트
- Parser 우선순위와 괄호
- Enum·숫자·날짜 변환 오류
- 허용되지 않은 필드·연산자
- Wildcard Escape
- Tenant 조건 강제 적용
- 안정적인 Paging
- 생성 SQL과 Index 사용

---

## 17. 실무 사례 적용 진단과 개선 과제

동적 검색과 QueryDSL·Specification이 여러 목록 API에 적용돼 있지만 허용 Field, Operator, Sort, 최대 조건 깊이를 Endpoint마다 일관되게 제한하는 중앙 계약은 더 강화할 필요가 있습니다. 자유 검색은 기능인 동시에 비싼 Query를 사용자가 만들 수 있는 입력 표면입니다.

Parser 결과를 Entity Field에 직접 반사하지 말고 공개 Search Field Registry에 매핑합니다. 최대 AST Node·IN 항목·Page Size, Query Timeout을 두고 Slow Query와 실행 계획을 데이터 분포별로 검증합니다. Wildcard Prefix와 비선택적 조건은 별도 Endpoint나 Search Engine 전환 기준을 둡니다.

완료 기준은 미허용 Field·Operator가 4xx로 일관되게 거부되고, 악성 복합 조건이 제한 시간 내 차단되며, 대표 조건 조합의 Index 사용과 P95가 회귀 Test로 관리되는 상태입니다.

---

# Reference
- [RSQL Parser](https://github.com/jirutka/rsql-parser)
- [QueryDSL](https://querydsl.com/)
- [[Projection과 Hydration]]
- [[CQRS Pattern]]
