---
id: Key 설정
started: 2025-03-13
tags:
  - Java
  - JPA
  - DB
  - Spring
  - ✅DONE
group: "[[Java Spring JPA]]"
---
# Table Key 설정

Database Key는 단순히 Annotation을 붙이는 문제가 아니다. Primary Key는 Row의 정체성을 나타내고, Unique Constraint는 업무적으로 중복되면 안 되는 값의 조합을 보호한다. Application에서 먼저 중복을 조회하더라도 동시에 들어온 두 Transaction을 완전히 막을 수 없으므로 최종 불변식은 Database Constraint로 보장해야 한다.

## Primary Key와 Unique Key의 차이

| 구분 | 목적 | NULL | Table당 개수 |
|---|---|---|---:|
| Primary Key | Row Identity와 Foreign Key 참조 | 허용하지 않음 | 1개 |
| Unique Constraint | 업무상 중복 금지 | DBMS 정책에 따라 여러 NULL 가능 | 여러 개 |

`id`는 기술적 Primary Key로 사용하고 `(tenant_id, external_id)` 같은 업무 식별자를 Unique Constraint로 보호할 수 있다. 업무 값이 바뀔 수 있다면 이를 Primary Key로 사용했을 때 모든 Foreign Key 갱신 비용이 커진다.

## 예시코드
### 2개 이상의 컬럼을 유니크 컬럼으로 설정
```Java title="두개의 컬럼에 대해서 유니크 Key를 설정할 수 있음."
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(
    name = "custom_entity",
    uniqueConstraints = {
        @UniqueConstraint(
            name = "uk_custom_entity_custom_ids",
            columnNames = {"custom_id", "custom_id2"}
        )
    })
public class CustomEntity extends CreateTimeField {
    @Id
    @GeneratedValue
    private Long id;
  
    @Column(nullable = false)
    private String customId;
  
    @Column(nullable = false)  
    private String customId2;  
}
```

Constraint 이름을 명시하면 운영 오류와 Migration에서 어떤 규칙이 실패했는지 찾기 쉽다. `columnNames`에는 Java Field 이름이 아니라 실제 Database Column 이름을 사용한다.

## NULL과 Unique Constraint

SQL의 `NULL`은 “값을 모른다”는 의미라 서로 같다고 비교되지 않을 수 있다. PostgreSQL의 일반 Unique Constraint는 여러 NULL을 허용한다. 두 Column 중 하나가 Nullable이면 기대와 달리 중복 Row가 들어갈 수 있다.

업무상 값이 반드시 필요하면 `nullable = false`와 `NOT NULL` Constraint를 함께 사용한다. NULL도 하나만 허용해야 한다면 DBMS가 지원하는 `NULLS NOT DISTINCT` 또는 Expression·Partial Index를 검토한다.

## 조회와 Index

대부분의 DBMS는 Unique Constraint를 검증하기 위한 Unique Index를 만든다. `(custom_id, custom_id2)` Index는 두 값을 함께 조회하거나 왼쪽 Column부터 조건에 사용하는 Query에 유용하다. 반대로 `custom_id2`만 검색하는 Query에는 충분하지 않을 수 있다.

Column 순서는 중복 규칙에는 영향을 주지 않지만 Query Plan에는 영향을 줄 수 있다. 실제 조회 Pattern과 Cardinality를 보고 정한다.

## Application 검증만으로 부족한 이유

```text
Transaction A: 중복 조회 -> 없음
Transaction B: 중복 조회 -> 없음
Transaction A: INSERT
Transaction B: INSERT
```

Database Constraint가 없다면 두 Row가 모두 저장된다. 사용자에게 친절한 메시지를 주기 위한 사전 조회는 가능하지만, Race Condition을 막는 최종 장치는 Unique Constraint다. 저장 시 Constraint 위반을 업무 오류로 변환한다.

## Schema Migration

JPA Annotation은 이미 존재하는 운영 Database를 자동으로 안전하게 변경하지 않는다. Liquibase나 Flyway Migration으로 같은 Constraint를 추가한다.

```sql
ALTER TABLE custom_entity
ADD CONSTRAINT uk_custom_entity_custom_ids
UNIQUE (custom_id, custom_id2);
```

기존 중복 Data가 있으면 Migration이 실패하므로 먼저 중복을 조회하고 정리 정책을 결정한다. 큰 Table에서는 Index 생성 Lock과 시간을 확인하고 Online·Concurrent 생성 전략을 검토한다.

## 기억할 점

Key 설계는 Annotation 사용법보다 “어떤 중복을 Database가 절대 허용하지 않아야 하는가”를 표현하는 일이다. Entity Mapping, Migration, NULL 정책과 실제 Query Index를 함께 설계해야 한다.

# Reference
