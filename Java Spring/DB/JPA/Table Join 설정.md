---
id: Table Join 설정
started: 2025-03-18
tags:
  - ✅DONE
  - JPA
group: "[[Java Spring DB]]"
---

# JPA 연관 관계 Mapping

JPA 연관 관계는 객체 Graph를 편하게 탐색하기 위한 기능이지 Foreign Key 설계를 대신하지 않는다. Database FK의 소유 Table, Aggregate 경계와 Query 요구를 먼저 정한 뒤 최소한의 방향만 Mapping한다.

## 기본 원칙

- To-one은 `LAZY`를 명시한다.
- To-many Collection은 빈 Collection으로 초기화한다.
- 양방향 Mapping은 양쪽 탐색이 실제로 필요할 때만 사용한다.
- 연관 관계 편의 Method 한곳에서 양쪽을 동기화한다.
- `equals/hashCode/toString`에 Lazy 연관 관계를 넣지 않는다.
- Entity를 Web Response로 직접 직렬화하지 않는다.
- FK Column과 Index는 Liquibase Changelog로 관리한다.

## Many-to-one이 FK를 소유한다

`passenger_booking.booking_id`가 FK이면 `PassengerBookingJpaEntity`가 연관 관계의 소유자다.

```java
@Entity
@Table(name = "passenger_booking")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class PassengerBookingJpaEntity {

    @Id
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "booking_id", nullable = false)
    private BookingJpaEntity booking;

    @Column(name = "passenger_id", nullable = false)
    private Long passengerId;

    static PassengerBookingJpaEntity create(
        Long id,
        BookingJpaEntity booking,
        Long passengerId
    ) {
        PassengerBookingJpaEntity entity = new PassengerBookingJpaEntity();
        entity.id = id;
        entity.booking = Objects.requireNonNull(booking);
        entity.passengerId = Objects.requireNonNull(passengerId);
        return entity;
    }
}
```

## One-to-many의 `mappedBy`

`mappedBy` 값은 Column 이름이 아니라 상대 Entity의 Field 이름이다.

```java
@Entity
@Table(name = "booking")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class BookingJpaEntity {

    @Id
    private Long id;

    @OneToMany(
        mappedBy = "booking",
        cascade = CascadeType.ALL,
        orphanRemoval = true
    )
    private final List<PassengerBookingJpaEntity> passengers = new ArrayList<>();

    public void replacePassengers(List<Long> passengerIds) {
        passengers.clear();
        passengerIds.stream()
                    .map(passengerId -> PassengerBookingJpaEntity.create(
                        TSID.fast().toLong(),
                        this,
                        passengerId
                    ))
                    .forEach(passengers::add);
    }
}
```

Entity 내부 Collection 변경은 JPA Dirty Checking 때문에 Mutable해야 할 수 있다. 외부에는 수정 가능한 Collection을 직접 노출하지 않고 조회 시 `List.copyOf(passengers)`를 반환하는 방법을 고려한다.

## One-to-one

실제 Cardinality가 정말 1:1인지 확인한다. FK에 Unique Constraint가 없다면 Database는 여러 Row가 같은 대상을 참조하는 것을 막지 못한다.

```java
@OneToOne(fetch = FetchType.LAZY, optional = false)
@JoinColumn(name = "profile_id", nullable = false, unique = true)
private DriverProfileJpaEntity profile;
```

공유 Primary Key 관계라면 `@MapsId`를 사용할 수 있다.

```java
@Entity
@Table(name = "driver_profile")
public class DriverProfileJpaEntity {

    @Id
    private Long driverId;

    @MapsId
    @OneToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "driver_id")
    private DriverJpaEntity driver;
}
```

## Many-to-many를 직접 Mapping하지 않는 이유

Join Table에 생성 시각, 역할, 상태와 순서가 추가되는 순간 독립 Entity가 필요하다. 업무 시스템에서는 처음부터 연결 Entity로 모델링하는 편이 변경에 안전하다.

```text
driver <- driver_center_membership -> center
```

`DriverCenterMembershipJpaEntity`가 `driver_id`, `center_id`, `role`, `joined_at`을 갖고 두 개의 Many-to-one을 Mapping한다.

## Aggregate 경계 밖은 ID로 참조하기

Booking Aggregate가 Passenger Aggregate 전체를 JPA 연관 관계로 가지면 한 Aggregate 변경이 다른 Aggregate Loading과 Cascade로 번질 수 있다. 다른 Vertical Slice 또는 Aggregate는 `passengerId` 같은 식별자만 저장하고 필요한 정보는 Query Port로 Batch 조회한다.

```java
@Column(name = "passenger_id", nullable = false)
private Long passengerId;
```

## Cascade와 orphanRemoval

- `cascade = ALL`은 부모와 자식이 같은 Aggregate Lifecycle을 가질 때만 사용한다.
- `REMOVE`가 외부 Aggregate까지 전파되지 않게 한다.
- `orphanRemoval = true`는 Collection에서 제거된 자식 Row를 삭제한다.
- 대량 교체는 `clear + addAll`이 많은 DELETE/INSERT를 만들 수 있으므로 Diff Sync를 고려한다.

## Query 전략

Mapping의 `LAZY/EAGER`만으로 Use Case별 Query를 최적화하지 않는다. 상세는 Fetch Join, 목록은 Projection·Two-step Pagination, 여러 Lazy Collection은 Batch Fetch를 사용한다.

```java
@EntityGraph(attributePaths = "passengers")
@Query("select booking from BookingJpaEntity booking where booking.id = :bookingId")
Optional<BookingJpaEntity> findDetail(@Param("bookingId") long bookingId);
```

## Schema Migration

```yaml
databaseChangeLog:
  - changeSet:
      id: add-passenger-booking-foreign-key
      author: team
      changes:
        - addForeignKeyConstraint:
            baseTableName: passenger_booking
            baseColumnNames: booking_id
            referencedTableName: booking
            referencedColumnNames: id
            constraintName: fk_passenger_booking_booking
        - createIndex:
            tableName: passenger_booking
            indexName: idx_passenger_booking_booking_id
            columns:
              - column:
                  name: booking_id
```

Entity Annotation만 추가하고 Schema Changelog를 빼먹으면 환경마다 Schema가 달라진다.

## 기억할 점

연관 관계 Mapping은 탐색 편의보다 Aggregate와 FK 소유권을 먼저 반영해야 한다. Lazy를 기본으로 하고, 양방향과 Cascade를 최소화하며, 다른 Aggregate는 ID로 참조하고, Query 전략과 Liquibase Migration을 함께 검증한다.
