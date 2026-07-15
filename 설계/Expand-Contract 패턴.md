---
id: Expand-Contract 패턴
started: 2026-07-15
tags:
  - ✅DONE
  - Architecture
  - Database
  - Migration
group:
  - "[[Software Design]]"
---

# Expand-Contract(확장-축소) 패턴: 서비스를 멈추지 않고 계약을 바꾸는 방법

운영 중인 시스템의 Database Column, API Payload 또는 Event Schema를 한 번에 바꾸면 구버전과 신버전이 동시에 실행되는 배포 구간에서 장애가 발생한다. Expand-Contract는 기존 계약을 즉시 없애지 않고 새 계약을 먼저 추가한 뒤, Consumer와 Data를 옮기고, 마지막에 기존 계약을 제거하는 점진적 변경 방식이다. Parallel Change라고도 부른다.

```text
Expand                 Migrate                         Contract
새 계약 추가           사용처·Data 이동               기존 계약 제거
Old + New 지원    ->   New 사용 비율 확대        ->   New만 지원
```

핵심은 Migration SQL을 세 파일로 나누는 데 있지 않다. 일정 기간 두 계약이 공존하도록 설계하고, 전환 완료를 수치로 증명한 다음 파괴적 변경을 별도 배포로 실행하는 것이 핵심이다.

## 왜 한 번에 바꾸면 장애가 나는가

Kubernetes에 Application Pod가 20개 있고 Rolling Deployment를 한다고 가정하자. 배포 도중에는 다음 상태가 정상적으로 발생한다.

```text
10:00  구버전 Pod 20개 + 기존 Schema
10:02  구버전 Pod 20개 + 확장된 Schema
10:05  구버전 Pod 12개 + 신버전 Pod 8개 + 확장된 Schema
10:10  신버전 Pod 20개 + 확장된 Schema
```

신버전 배포 직전에 기존 Column을 삭제하면 아직 실행 중인 구버전 Pod의 Query가 실패한다. 반대로 Application을 먼저 배포했는데 새 Column이 없다면 신버전 Pod가 실패한다. Message Consumer, Batch, 운영 Script와 BI Query처럼 배포 대상에서 빠진 Consumer가 있으면 위험은 더 커진다.

따라서 무중단 변경에는 최소한 다음 호환성이 필요하다.

- 확장된 Schema는 구버전 Application도 사용할 수 있어야 한다.
- 전환 중 Application은 Old Data와 New Data를 모두 읽을 수 있어야 한다.
- Contract는 Old Reader와 Old Writer가 0이라는 증거가 생긴 뒤 실행해야 한다.
- Rollback할 Release가 어떤 Schema와 Data를 기대하는지 알아야 한다.

## 세 단계보다 정확한 다섯 단계

실무에서는 Expand, Migrate, Contract를 다음 다섯 단계로 쪼개면 배포 판단이 명확해진다.

| 단계 | Schema | Write | Read | 완료 조건 |
|---|---|---|---|---|
| 0. 준비 | Old | Old | Old | 불변식·지표·Consumer 목록 정의 |
| 1. 확장 | Old + New | Old | Old | 구버전이 확장 Schema에서 정상 |
| 2. 호환 배포 | Old + New | Old + New | New 우선, Old Fallback | 신·구버전 동시 실행 정상 |
| 3. 이관 | Old + New | Old + New | New 우선 | Backfill 100%, 불일치 0 |
| 4. 전환 | Old + New | New | New | Old Read/Write 0, Rollback 조건 재정의 |
| 5. 축소 | New | New | New | 기존 계약과 호환 Code 제거 |

하나의 Release에 1단계와 5단계를 함께 넣으면 Expand-Contract가 아니다. Contract는 적어도 신버전이 완전히 배포되고 관측 기간을 지난 다음 Release로 분리한다.

---

# 실 사례: 예약의 승객 정보를 관계형 구조로 무중단 전환하기

## 기존 구조와 문제

초기 시스템은 예약 생성 시 승객 정보를 `bookings` Table에 복사했다.

```sql
CREATE TABLE bookings (
    id                    BIGINT PRIMARY KEY,
    tenant_id             BIGINT NOT NULL,
    customer_external_key VARCHAR(100) NOT NULL,
    customer_name         VARCHAR(100) NOT NULL,
    customer_phone        VARCHAR(30) NOT NULL,
    status                VARCHAR(30) NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL
);
```

서비스가 성장하면서 같은 승객의 연락처 수정, 동의 상태, 접근 제어와 중복 정보 관리가 필요해졌다. 목표는 승객을 별도 관계형 Table로 정규화하고 `bookings.passenger_id`가 이를 참조하게 만드는 것이다.

```text
Before
bookings(customer_external_key, customer_name, customer_phone)

After
passengers(id, tenant_id, external_key, name, phone)
bookings(passenger_id -> passengers.id)
```

구조화된 승객 정보를 JSONB Column 하나에 넣지 않는다. 조회, 무결성, Index와 Domain 관계가 필요한 Data이므로 명시적인 Column과 Foreign Key로 모델링한다.

## 0단계: 불변식과 성공 조건 정의

Migration 전에 “완료”를 Query 가능한 조건으로 만든다.

- 모든 예약은 같은 Tenant의 승객 한 명을 참조한다.
- `(tenant_id, external_key)`는 승객을 식별하는 Unique Key다.
- 승객과 예약의 Tenant 및 External Key가 일치해야 한다.
- 같은 External Key의 과거 Snapshot이 다르면 가장 최근 예약의 값을 초기 승객 정보로 사용한다.
- Backfill은 중단 후 재실행해도 같은 결과를 만들어야 한다.
- 전환 중 예약 생성과 수정은 Old/New 표현을 함께 갱신한다.
- `passenger_id IS NULL` 예약 수가 0이 된 후에만 `NOT NULL`을 적용한다.

전화번호만으로 동일 인물을 합치면 가족 공용 번호나 재사용 번호 때문에 잘못 병합될 수 있다. 이 사례에서는 기존에 존재하는 안정적인 `customer_external_key`를 Identity로 사용한다. 안정적인 Key가 없다면 기술 Migration보다 Identity 정책 결정이 먼저다.

## 1단계: Expand Migration

기존 Migration을 수정하지 않고 새 ChangeSet을 기존 `origin/main` 이력 뒤에 추가한다. 첫 Migration은 새 Table과 Nullable FK만 추가한다. 아직 기존 Column을 삭제하거나 `NOT NULL`을 적용하지 않는다.

```xml
<changeSet id="20260715-01-expand-passenger-reference" author="backend">
    <createTable tableName="passengers">
        <column name="id" type="BIGINT">
            <constraints primaryKey="true" nullable="false"/>
        </column>
        <column name="tenant_id" type="BIGINT">
            <constraints nullable="false"/>
        </column>
        <column name="external_key" type="VARCHAR(100)">
            <constraints nullable="false"/>
        </column>
        <column name="name" type="VARCHAR(100)">
            <constraints nullable="false"/>
        </column>
        <column name="phone" type="VARCHAR(30)">
            <constraints nullable="false"/>
        </column>
        <column name="updated_at" type="TIMESTAMP WITH TIME ZONE">
            <constraints nullable="false"/>
        </column>
    </createTable>

    <addUniqueConstraint
        tableName="passengers"
        columnNames="tenant_id, external_key"
        constraintName="uk_passengers_tenant_external_key"/>

    <addUniqueConstraint
        tableName="passengers"
        columnNames="tenant_id, id"
        constraintName="uk_passengers_tenant_id"/>

    <addColumn tableName="bookings">
        <column name="passenger_id" type="BIGINT"/>
    </addColumn>
</changeSet>
```

대형 Table의 Index 생성은 일반 `CREATE INDEX`가 Write를 오래 막을 수 있다. PostgreSQL에서는 Transaction 밖의 `CREATE INDEX CONCURRENTLY`를 별도 ChangeSet으로 실행하고 실패한 Invalid Index를 감시한다.

```xml
<changeSet
    id="20260715-02-index-booking-passenger"
    author="backend"
    runInTransaction="false">
    <sql>
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bookings_passenger_id
            ON bookings (passenger_id)
    </sql>
</changeSet>
```

기존 Row 전체를 즉시 검사하는 FK 추가가 부담이라면 PostgreSQL의 `NOT VALID`로 새 Write부터 보호하고, Backfill 이후 별도로 검증한다.

```sql
ALTER TABLE bookings
    ADD CONSTRAINT fk_bookings_passenger
    FOREIGN KEY (tenant_id, passenger_id)
    REFERENCES passengers (tenant_id, id)
    NOT VALID;
```

복합 FK는 Application Bug가 다른 Tenant의 승객 ID를 저장하는 것을 Database에서도 차단한다. `passengers.id`가 전역 Unique더라도 Tenant 격리를 무결성 제약에 드러내면 운영 Query와 사고 분석이 명확해진다.

Migration 도구가 생성한 SQL을 그대로 신뢰하지 않는다. Production 적용 전에 예상 Lock, 실행 시간, Table Rewrite 여부와 Rollback이 아니라 Roll-forward 가능한 복구 절차를 검토한다.

## 2단계: 호환 Application 배포

확장 Schema가 모든 환경에 적용된 뒤 호환 Application을 배포한다. 이 버전은 새 예약을 저장할 때 Passenger와 기존 Snapshot을 같은 DB Transaction에서 함께 저장한다.

### Out Port는 Either로 실패를 표현한다

```java
public interface PassengerPort {

    Either<PassengerError, Passenger> findOrCreate(PassengerIdentity identity);
}

public interface BookingPort {

    Either<BookingError, Booking> save(Booking booking);
}
```

### 내부 Writer가 두 표현을 원자적으로 만든다

```java
@Component
@RequiredArgsConstructor
public class CompatibleBookingWriter {

    private final PassengerPort passengerPort;
    private final BookingPort bookingPort;

    public Either<CreateBookingError, Booking> write(CreateBookingCommand command) {
        return passengerPort.findOrCreate(command.passengerIdentity())
            .mapLeft(CreateBookingError::passengerFailure)
            .map(passenger -> Booking.createCompatible(command, passenger))
            .flatMap(booking -> bookingPort.save(booking)
                .mapLeft(CreateBookingError::bookingFailure));
    }
}
```

`Booking.createCompatible`은 `passenger_id`와 구버전이 읽을 `customer_*` Snapshot을 모두 채운다. 두 Table이 같은 Database에 있으므로 하나의 Local Transaction으로 묶을 수 있다. 서로 다른 Database나 Service에 쓰는 Dual Write라면 이 코드만으로 원자성이 생기지 않으며 Outbox, CDC 또는 별도 Reconciliation이 필요하다.

### 최상위 Service는 Either를 밖으로 노출하지 않는다

```java
@Service
@Application
@RequiredArgsConstructor
public class CreateBookingService implements CreateBookingUseCase {

    private final BookingAccessValidator accessValidator;
    private final CompatibleBookingWriter bookingWriter;
    private final BookingExceptionMapper exceptionMapper;

    @Override
    @Transactional
    public BookingResource create(CreateBookingCommand command) {
        accessValidator.validate(command.actor(), command.tenantId());

        Booking booking = bookingWriter.write(command)
            .getOrElseThrow(exceptionMapper::toException);

        return BookingResource.from(booking);
    }
}
```

Controller-facing Service는 권한 검사, 저장, 응답 변환이라는 업무 흐름만 보여 준다. Domain과 Out Port의 `Either`는 Service 경계에서 Application Exception으로 바꾸고 `@RestControllerAdvice`가 HTTP 응답을 만든다.

### Read는 New 우선, Old Fallback

Backfill이 끝나기 전에는 `passenger_id`가 없는 기존 Row가 존재한다. 조회 Adapter는 두 형태를 읽되 어느 경로가 사용됐는지 Metric을 남긴다.

```java
@Component
@RequiredArgsConstructor
public class CompatiblePassengerResolver {

    private final PassengerQueryPort passengerQueryPort;
    private final Counter legacyFallbackCounter;

    public Either<PassengerError, PassengerView> resolve(BookingRow booking) {
        return Optional.ofNullable(booking.passengerId())
            .<Either<PassengerError, PassengerView>>map(passengerId ->
                passengerQueryPort.findView(passengerId)
            )
            .orElseGet(() -> {
                legacyFallbackCounter.increment();
                return Either.right(PassengerView.fromLegacySnapshot(booking));
            });
    }
}
```

Fallback은 영구 기능이 아니다. Contract 조건을 판단할 수 있도록 `legacy_read_fallback_total` 같은 Metric으로 관측한다.

## 3단계: 기존 Data Backfill

Application 배포와 대량 Data 이관을 같은 작업으로 묶지 않는다. Backfill은 Online Traffic과 Lock을 경쟁하므로 작은 Batch, Keyset Pagination, 재시작 가능한 Checkpoint와 Rate Limit을 사용한다.

### Offset Pagination을 피한다

`OFFSET 10000000`은 앞 Row를 계속 읽어 버려야 하고 실행 중 Data 변경에 취약하다. 마지막 처리 ID를 기준으로 다음 Batch를 가져온다.

```sql
SELECT id,
       tenant_id,
       customer_external_key,
       customer_name,
       customer_phone
FROM bookings
WHERE passenger_id IS NULL
  AND id > :last_processed_id
ORDER BY id
LIMIT :batch_size;
```

Worker를 여러 개 실행한다면 `FOR UPDATE SKIP LOCKED`를 사용할 수 있지만 긴 Transaction으로 Row Lock을 오래 잡지 않게 Batch 크기와 Commit 주기를 제한한다.

### 멱등 Backfill SQL

```sql
INSERT INTO passengers (
    id,
    tenant_id,
    external_key,
    name,
    phone,
    updated_at
)
SELECT generate_tsid(),
       booking.tenant_id,
       booking.customer_external_key,
       booking.customer_name,
       booking.customer_phone,
       booking.created_at
FROM bookings booking
WHERE booking.passenger_id IS NULL
  AND booking.id > :from_id
  AND booking.id <= :to_id
ON CONFLICT (tenant_id, external_key) DO UPDATE
SET name = EXCLUDED.name,
    phone = EXCLUDED.phone,
    updated_at = EXCLUDED.updated_at
WHERE EXCLUDED.updated_at > passengers.updated_at;

UPDATE bookings booking
SET passenger_id = passenger.id
FROM passengers passenger
WHERE booking.passenger_id IS NULL
  AND booking.tenant_id = passenger.tenant_id
  AND booking.customer_external_key = passenger.external_key
  AND booking.id > :from_id
  AND booking.id <= :to_id;
```

`generate_tsid()`는 프로젝트에서 사용하는 TSID 생성 방식을 나타낸다. 실제로 Database 함수가 없다면 Application에서 ID를 미리 생성하거나 프로젝트 표준 ID 생성기를 사용한다. `updated_at` 비교 때문에 Batch 실행 순서와 관계없이 가장 최근 Snapshot이 남으며, 같은 범위를 다시 실행해도 Unique Key와 `passenger_id IS NULL` 조건 때문에 중복 Row가 늘지 않는다. Migration 중 발생한 실시간 승객 수정은 더 최신 `updated_at`을 기록해 오래된 Backfill이 덮어쓰지 못하게 해야 한다.

### Backfill Application Service

```java
@Service
@Application
@RequiredArgsConstructor
public class BackfillBookingPassengerService implements BackfillBookingPassengerUseCase {

    private final BookingPassengerBackfillBatch backfillBatch;
    private final BackfillCheckpointPort checkpointPort;
    private final BackfillExceptionMapper exceptionMapper;

    @Override
    public BackfillSummary backfill(BackfillCommand command) {
        BackfillCheckpoint checkpoint = checkpointPort.load(command.jobId())
            .getOrElseThrow(exceptionMapper::toException);

        BackfillSummary summary = backfillBatch.execute(command, checkpoint)
            .getOrElseThrow(exceptionMapper::toException);

        checkpointPort.save(summary.checkpoint())
            .getOrElseThrow(exceptionMapper::toException);
        return summary;
    }
}
```

최상위 Service는 Checkpoint 조회, Batch 실행, Checkpoint 저장만 조율한다. SQL 실행, Retry 가능한 DB Error 분류, Batch 크기 조절과 Row Mapping은 `BookingPassengerBackfillBatch` 내부로 내린다.

### 진행률과 정합성 Query

단순 처리 건수만 보지 말고 남은 Row와 값 불일치를 모두 측정한다.

```sql
-- Backfill coverage
SELECT COUNT(*) AS missing_passenger_reference
FROM bookings
WHERE passenger_id IS NULL;

-- Tenant boundary and identity consistency
SELECT COUNT(*) AS inconsistent_booking_count
FROM bookings booking
JOIN passengers passenger ON passenger.id = booking.passenger_id
WHERE passenger.tenant_id <> booking.tenant_id
   OR passenger.external_key <> booking.customer_external_key;
```

과거 `customer_name`과 `customer_phone`은 예약 생성 시점의 Snapshot이므로 현재 승객 정보와 다를 수 있다. 이를 무조건 불일치로 세면 정상적인 변경까지 오류가 된다. 대신 Dual-write 배포 이후 생성된 예약만 Write 시점의 비교 대상으로 삼고, 과거 Data는 명시한 최신값 선택 규칙을 검증한다.

완료 조건의 예시는 다음과 같다.

- `missing_passenger_reference = 0`
- `inconsistent_booking_count = 0`
- `legacy_read_fallback_total` 증가량이 관측 기간 동안 0
- 새 Write의 Old/New 비교 실패율이 0
- Backfill DB CPU, WAL, Replica Lag와 Lock Wait가 허용 범위 이내

## 4단계: Cutover

Backfill이 끝났다고 즉시 Column을 삭제하지 않는다. 먼저 Read를 New 전용으로 바꾸고 Old Fallback을 끈다. Canary에서 시작해 Traffic 비율을 올리고 Error Rate와 Fallback Metric을 확인한다.

```text
1% New-only Read -> 10% -> 50% -> 100%
```

그다음 Old Snapshot Write를 중단한다. 이 시점부터 Old Application으로 단순 Rollback하면 새 예약을 정상적으로 읽지 못할 수 있다. Rollback 대상 Release가 New Schema를 읽을 수 있는 호환 버전인지 확인해야 한다.

Feature Flag는 전환 속도를 제어하는 수단이지 Schema 호환성을 대신하지 않는다. Process Memory Flag만으로 DB Migration 상태를 추정하지 말고, 배포 환경과 Schema Version을 명시적으로 관리한다.

## 5단계: Contract Migration

Old Reader와 Writer가 0이고 관측 기간이 끝난 뒤 무결성 제약을 강화한다. PostgreSQL에서는 FK 검증과 `NOT NULL` 적용을 별도 단계로 나눠 Lock 시간을 관리한다.

```sql
ALTER TABLE bookings
    VALIDATE CONSTRAINT fk_bookings_passenger;

ALTER TABLE bookings
    ADD CONSTRAINT ck_bookings_passenger_id_not_null
    CHECK (passenger_id IS NOT NULL) NOT VALID;

ALTER TABLE bookings
    VALIDATE CONSTRAINT ck_bookings_passenger_id_not_null;

ALTER TABLE bookings
    ALTER COLUMN passenger_id SET NOT NULL;
```

마지막 Contract Migration에서 기존 Column을 삭제한다.

```xml
<changeSet id="20260820-01-contract-booking-passenger" author="backend">
    <preConditions onFail="HALT">
        <sqlCheck expectedResult="0">
            SELECT COUNT(*) FROM bookings WHERE passenger_id IS NULL
        </sqlCheck>
    </preConditions>

    <dropColumn tableName="bookings" columnName="customer_external_key"/>
    <dropColumn tableName="bookings" columnName="customer_name"/>
    <dropColumn tableName="bookings" columnName="customer_phone"/>
</changeSet>
```

Contract Migration은 처음 Expand Migration 파일에 뒤늦게 추가하지 않는다. 이미 실행된 Migration은 이력이며, 새로운 파괴적 변경은 새로운 파일로 추가한다. Branch Migration은 `origin/main`에 존재하는 모든 관련 Migration 뒤에 등록해 Merge 이후 실행 순서가 뒤집히지 않게 한다.

Column 삭제 전에 다음 Consumer를 다시 확인한다.

- Application과 과거 Release
- Batch, Scheduler와 Data Export Job
- BI Dashboard와 직접 SQL 사용자
- CDC Connector와 Sink Mapping
- 읽기 Replica를 사용하는 도구
- 장애 복구 Script와 운영 Runbook

---

# API 계약의 Expand-Contract

Database뿐 아니라 외부 API의 Field 이름 변경에도 같은 원리가 적용된다. `customer`를 `passenger`로 바로 바꾸면 Mobile App처럼 강제 Update할 수 없는 Consumer가 실패한다.

## API Expand

Request는 일정 기간 Old/New Field를 모두 허용하되 둘이 동시에 들어와 값이 다르면 거절한다. Response에는 새 Field를 추가하고 기존 Field는 Deprecated로 표시한다.

```java
public record CreateBookingRequest(
    @Deprecated
    PassengerRequest customer,
    PassengerRequest passenger
) {
    public CreateBookingCommand toCommand(CurrentUser user) {
        PassengerRequest resolved = resolvePassenger()
            .getOrElseThrow(InvalidPassengerContractException::new);
        return CreateBookingCommand.from(user, resolved);
    }

    private Either<PassengerContractError, PassengerRequest> resolvePassenger() {
        return PassengerContractResolver.resolve(customer, passenger);
    }
}
```

이 예제의 `Either`는 Request 변환 내부의 검증 값이며 Controller-facing Service 반환형이 아니다. 예외는 `@RestControllerAdvice`가 HTTP 400 `ProblemDetail`로 변환한다.

## API Migrate와 Contract

1. Server가 Old/New Request를 모두 수용한다.
2. Server Response에 New Field를 추가한다.
3. Client를 New Field 읽기와 쓰기로 전환한다.
4. Access Log 또는 Contract Metric으로 Old Field 사용률을 측정한다.
5. 공개된 지원 종료 시점과 Version 정책에 따라 Old Field를 제거한다.

Consumer가 조직 밖에 있다면 “사용률이 0”만으로 제거하면 안 된다. 공지된 Deprecation 기간, API Version과 계약상 지원 기간을 따라야 한다.

---

# Event Schema의 Expand-Contract

Event는 Broker Retention 안에 과거 Message가 남고 Consumer가 독립 배포되므로 HTTP보다 Contract 기간이 길 수 있다.

기존 Event가 다음과 같다고 하자.

```json
{
  "eventType": "BookingCreated",
  "schemaVersion": 1,
  "bookingId": 91201,
  "customerId": 301
}
```

Expand 단계에서는 `passengerId`를 추가하고 `customerId`를 유지한다.

```json
{
  "eventType": "BookingCreated",
  "schemaVersion": 2,
  "bookingId": 91201,
  "customerId": 301,
  "passengerId": 301
}
```

전환 순서는 Consumer First가 안전하다.

1. Consumer가 V1과 V2를 모두 읽도록 배포한다.
2. Producer가 V2를 발행하되 Old Field도 유지한다.
3. Consumer Group별 V2 처리 성공과 Old Field 접근을 관측한다.
4. Retention, Replay, DLT와 장기 보관 Event가 V1을 포함하는지 확인한다.
5. 모든 Consumer 전환 후 새 Major Version 또는 새 Topic에서 Old Field를 제거한다.

Schema Registry의 Compatibility 검사만으로 업무 의미 호환성이 보장되지는 않는다. Field Type이 같아도 단위, Null 의미 또는 식별 대상이 달라지면 Breaking Change다.

---

# 무엇을 관측해야 하는가

Expand-Contract는 “배포 성공”이 아니라 “이관 완료”를 관측해야 한다.

| 영역 | 필수 지표 |
|---|---|
| Schema | Migration 실행 시간, Lock Wait, 실패 ChangeSet |
| Data | 대상 수, 완료 수, 누락 수, 불일치 수, 처리 속도 |
| Database | CPU, IOPS, WAL, Replica Lag, Deadlock, Long Transaction |
| Application | Old/New Read 비율, Fallback 수, Dual-write 불일치 |
| API | Old Field 사용 Client 수, Version별 Error Rate |
| Event | Schema Version별 생산·소비량, Consumer Lag, DLT |

High-cardinality ID를 Metric Tag에 넣지 않는다. 불일치 Sample은 접근이 통제된 Audit Table이나 구조화 Log에 제한적으로 기록한다.

# Rollback과 Roll-forward

단계마다 가능한 복구가 다르다.

| 장애 시점 | 안전한 대응 |
|---|---|
| Expand 직후 | Application Rollback, 추가 Schema는 그대로 유지 |
| Dual-write 중 | 호환 Application으로 Rollback, Backfill 중지·재실행 |
| New-only Read 후 | Fallback Flag를 다시 켜거나 호환 버전으로 Rollback |
| Old Write 중단 후 | Old Data를 다시 채우지 않았다면 구버전 Rollback 금지 |
| Contract 후 | 삭제 Column 복구보다 Forward Fix와 Backup Restore 판단 |

Online Data Migration은 대체로 Roll-forward가 안전하다. Column을 삭제한 뒤 Rollback Code를 배포해도 Data가 자동으로 돌아오지 않는다. Contract 전 Backup과 복구 시간 목표를 확인하고, 파괴적 변경에는 명시적인 승인 Gate를 둔다.

# Test Matrix

호환성은 신버전 Test만 통과한다고 증명되지 않는다.

| Application | Old Schema | Expanded Schema | Contracted Schema |
|---|---:|---:|---:|
| Old Version | 정상 | 반드시 정상 | 실패 예상 |
| Compatible Version | 배포 전에는 사용하지 않음 | 반드시 정상 | 설계에 따라 확인 |
| New-only Version | 실패 가능 | 반드시 정상 | 반드시 정상 |

다음 Test를 자동화한다.

- Expanded Schema에서 구버전 Repository Query 회귀 Test
- Old Row, New Row와 부분 Backfill Row 조회 Test
- 같은 Batch를 두 번 실행하는 멱등성 Test
- Online Write와 Backfill이 동시에 같은 Row를 만나는 경쟁 조건 Test
- Tenant가 다른 Passenger를 참조하지 못하는 무결성 Test
- Feature Flag 전환과 Rollback Test
- Contract Precondition 실패 Test
- Production 규모를 반영한 Lock과 Replica Lag 부하 Test

# 자주 실패하는 방식

## Rename을 한 번에 실행한다

Column Rename은 논리적으로 Add + Copy + Remove가 한 문장에 들어간 Breaking Change다. 모든 Consumer를 동시에 배포할 수 없다면 새 Column을 추가해 점진적으로 옮긴다.

## Nullable Column을 추가하자마자 NOT NULL로 만든다

기존 Row가 채워지지 않았고 Table 전체 검증이 Traffic과 경쟁한다. Nullable로 확장하고 Backfill과 검증 뒤 제약을 강화한다.

## Application Dual-write만 믿는다

Retry, 일부 실패, 운영 Script와 Backfill이 한쪽만 수정할 수 있다. 같은 DB Transaction인지 확인하고 정합성 Query와 Reconciliation을 둔다.

## Backfill에 OFFSET과 거대한 Transaction을 쓴다

처리할수록 느려지고 Lock, WAL과 Replica Lag가 커진다. Keyset, 작은 Batch, Checkpoint와 Rate Limit을 사용한다.

## Feature Flag가 있으니 Old Column을 삭제한다

Flag를 되돌려도 Column과 Data가 사라졌다면 Rollback할 수 없다. Contract는 Flag Rollback 기간이 끝난 뒤 별도 승인으로 실행한다.

## Contract를 영원히 미룬다

두 계약이 영구화되면 어떤 값이 Source of Truth인지 모호해지고 모든 변경 비용이 늘어난다. Migration Owner, 제거 조건과 목표 날짜를 처음부터 정한다.

# 실무 Runbook

## 변경 전

- [ ] 모든 Reader, Writer, Batch, BI와 Event Consumer를 식별했다.
- [ ] Old/New 불변식과 Source of Truth를 정의했다.
- [ ] Migration이 관계형 Column과 Table을 사용하며 불필요한 JSON 저장을 추가하지 않는다.
- [ ] `origin/main` Migration 뒤에 새 ChangeSet을 배치했다.
- [ ] Lock, Table Rewrite, Index 생성과 Replica 영향도를 검토했다.
- [ ] 단계별 Rollback 가능 범위를 기록했다.

## Expand와 Migrate

- [ ] Expanded Schema에서 구버전 Application이 정상이다.
- [ ] 호환 Application이 Old/New Write를 원자적으로 처리한다.
- [ ] Read Fallback과 사용량 Metric이 있다.
- [ ] Backfill은 멱등이고 Checkpoint에서 재시작할 수 있다.
- [ ] Rate Limit과 Kill Switch가 있다.
- [ ] 누락·불일치 Query 결과가 0이다.

## Contract 전

- [ ] 모든 신버전 Pod와 비동기 Worker 배포가 끝났다.
- [ ] Old Read/Write 사용량이 합의한 관측 기간 동안 0이다.
- [ ] Broker Retention, DLT와 Replay Data를 확인했다.
- [ ] Backup과 Restore 절차를 검증했다.
- [ ] 파괴적 Migration Precondition과 승인 Gate가 있다.
- [ ] 호환 Code, Feature Flag와 Metric 제거 작업이 계획돼 있다.

# 언제 사용하지 않는가

- 짧은 점검 시간이 허용되고 이관 위험보다 병렬 계약 운영 비용이 더 큰 내부 시스템
- Consumer를 모두 원자적으로 배포할 수 있는 단일 Process 내부의 비공개 Refactoring
- Data가 없거나 재생성 가능해 Drop/Recreate가 가장 안전한 개발 환경
- 법적·보안상 기존 Data를 즉시 제거해야 하며 별도 승인된 중단 절차가 있는 경우

Expand-Contract는 무조건 무중단을 보장하는 마법이 아니다. 호환 기간, 중복 Code, Backfill과 관측 비용을 지불해 변경 위험을 여러 개의 작고 검증 가능한 단계로 나누는 패턴이다.

# 기억할 점

안전한 Contract는 삭제 명령이 아니라 검증 결과다. 새 구조를 먼저 만들고, 신·구버전이 공존하는 Code를 배포하고, Data와 Consumer를 이동하고, Old 사용량이 0임을 관측한 뒤에만 기존 계약을 제거한다.

# Reference

- [Martin Fowler - Parallel Change](https://martinfowler.com/bliki/ParallelChange.html)
- [Microsoft - Eliminate downtime through versioned service updates](https://learn.microsoft.com/en-us/devops/operate/achieving-no-downtime-versioned-service-updates)
- [Microsoft EF Core - Applying Migrations](https://learn.microsoft.com/en-us/ef/core/managing-schemas/migrations/applying)
- [AWS Prescriptive Guidance - Cut over](https://docs.aws.amazon.com/prescriptive-guidance/latest/strategy-database-migration/cut-over.html)
- [PostgreSQL - ALTER TABLE](https://www.postgresql.org/docs/current/sql-altertable.html)
- [PostgreSQL - CREATE INDEX](https://www.postgresql.org/docs/current/sql-createindex.html)
