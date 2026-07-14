---
id: TSID Primary Key
started: 2025-05-16
tags:
  - ✅DONE
  - Java
  - JPA
  - Database
group:
  - "[[Java Spring DB]]"
---

# TSID를 Database Primary Key로 사용하는 이유

Primary Key는 Row를 구분하는 값이지만, 생성 전략은 Index 쓰기 성능, 분산 환경과 외부 노출 방식에 영향을 준다. `AUTO_INCREMENT`는 단순하지만 Database에 Insert하기 전 ID를 알기 어렵고 여러 Database Node가 같은 범위에서 ID를 만들기 어렵다. Random UUID는 분산 생성이 쉽지만 B-tree Index에 무작위 위치로 삽입된다.

**TSID(Time-Sorted Unique Identifier)** 는 시간 정보를 앞부분에 두고 Random·Node 정보를 결합해 대체로 시간순으로 정렬되는 64-bit ID를 만든다.

## 64-bit 값을 나누어 생각하기

구현마다 세부 Bit 구성은 다를 수 있지만 개념은 다음과 같다.

```text
| timestamp bits | random / node / counter bits |
```

Timestamp가 상위 Bit에 있으므로 나중에 만든 값이 대체로 더 크다. 같은 Millisecond에 여러 ID가 만들어져도 나머지 Bit가 충돌을 방지한다.

`long` 하나에 들어가므로 PostgreSQL `BIGINT`, Java `Long`과 자연스럽게 대응한다. 128-bit UUID보다 PK와 이를 참조하는 Foreign Key Index가 작다.

## B-tree Index와 시간 정렬

Database B-tree의 Leaf Page는 Key 순서로 정렬된다. Random UUID는 Tree의 여러 위치에 삽입돼 Page Split과 Cache Miss를 늘릴 수 있다. 시간순 Key는 Index 오른쪽 끝에 가까운 위치로 들어가 Write Locality가 좋아지는 경향이 있다.

하지만 완전히 증가하는 Key는 특정 Page에 Write가 집중될 수 있다. TSID는 “언제나 가장 빠른 PK”가 아니라 분산 생성, 크기와 Index Locality의 균형이다. 실제 선택은 Insert Throughput과 Index 크기로 검증한다.

## Application에서 먼저 ID 만들기

```java
public final class Member {
    private final Long id;

    private Member(Long id) {
        this.id = id;
    }

    public static Member create() {
        return new Member(TSID.fast().toLong());
    }
}
```

Entity를 Persistence하기 전에 ID를 알 수 있으므로 Aggregate 내부 참조, Outbox Event와 Trace에 같은 식별자를 사용할 수 있다. ID 생성을 Domain Factory에 둘지 Persistence Adapter에 둘지는 ID가 Domain Identity인지 저장 기술인지에 따라 결정한다.

## JPA Mapping

```java
@Entity
@Table(name = "member")
public class MemberEntity {
    @Id
    @Column(name = "member_id", nullable = false, updatable = false)
    private Long id;
}
```

Application에서 ID를 생성한다면 `@GeneratedValue`를 함께 사용하지 않는다. Hibernate 전용 Generator Annotation을 사용할 수도 있지만 Library Version과 Hibernate Version 호환성을 확인해야 한다.

Schema는 다음처럼 명시한다.

```sql
CREATE TABLE member (
    member_id BIGINT PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);
```

Java의 signed `long`과 다른 언어의 Number 범위도 고려한다. JavaScript `Number`는 모든 64-bit 정수를 정확하게 표현하지 못하므로 API에서는 문자열로 전달하는 편이 안전하다.

```json
{"memberId": "784029384720193536"}
```

## 시간 정보의 의미와 한계

TSID에서 대략적인 생성 시간을 읽을 수 있지만 이를 업무의 `created_at` 대신 사용하면 안 된다.

- Clock 오차와 역행이 있을 수 있다.
- ID 생성 시간과 Transaction Commit 시간은 다르다.
- 외부에 노출하면 생성 시점과 대략적인 발급량을 추측할 수 있다.
- 정렬은 시간순에 가깝지만 완전한 업무 순서를 보장하지 않는다.

정확한 감사 시간은 별도 Column으로 저장하고 Database 또는 합의된 Clock Source를 사용한다.

## Node와 충돌 관리

여러 Process가 같은 Millisecond에 ID를 만들 때 Random Bit가 충분해야 한다. Node ID를 사용하는 구현이라면 Instance마다 고유한 값이 필요하고, Container 재시작과 Autoscaling에서 중복 할당되지 않아야 한다.

Birthday Problem 때문에 Random 공간이 작고 동시 생성량이 많으면 충돌 확률이 빠르게 증가한다. Database PK 제약은 마지막 안전망이며, 충돌 시 재생성 정책과 Metric이 필요하다.

## UUID, Sequence와 비교

| 방식 | 분산 생성 | 크기 | 시간 정렬 | 주요 주의점 |
|---|---|---:|---|---|
| DB Sequence | DB 의존 | 64-bit | 증가 | DB 왕복·Allocation 전략 |
| Random UUID | 쉬움 | 128-bit | 없음 | Index Locality와 크기 |
| UUIDv7 | 쉬움 | 128-bit | 시간 정렬 | 표현 크기 |
| TSID | 쉬움 | 64-bit | 대체로 가능 | Clock·충돌 공간·노출 |

## 기억할 점

TSID의 핵심은 “시간이 들어간 멋진 ID”가 아니라 Application에서 분산 생성할 수 있는 작은 정수 Key와 B-tree 친화적인 정렬 특성을 함께 얻는 것이다. 생성량, 충돌 확률, API 표현과 Database Index를 하나의 설계로 검토해야 한다.

# Reference

- [TSID Creator](https://github.com/f4b6a3/tsid-creator)
