---
id: Try 모나드
started: 2025-12-29
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
  - "[[Functional Programming]]"
---

# Try 모나드

`Try<T>`는 예외를 던질 수 있는 연산을 실행해 `Success<T>` 또는 `Failure<T>` 값으로 만든다. Java Lambda에서 다루기 불편한 Checked Exception을 Pipeline 안으로 가져올 때 특히 유용하다.

## Try와 Either의 역할

| 타입 | 실패 표현 | 주 사용 위치 |
|---|---|---|
| `Try<T>` | `Throwable` | 외부 Library가 예외를 던지는 Adapter 경계 |
| `Either<E, T>` | 업무 의미가 있는 `E` | Port와 Use Case의 명시적 계약 |
| `Validation<E, T>` | 여러 검증 Error 누적 | Command·Domain 생성 검증 |
| `Optional<T>` | 값 없음 | 실패 이유가 필요 없는 조회 |

일반적인 흐름은 `예외 발생 API -> Try -> map/mapTry -> toEither -> 업무 Error로 mapLeft`다. `Try`를 Controller까지 그대로 노출하면 호출자는 `Throwable` 종류에 결합된다.

## JSON Adapter의 실무 예제

다음 Adapter는 Object Storage에서 설정 파일을 읽고 JSON을 Domain 설정으로 변환한다. I/O, JSON Parsing과 Schema Validation을 각 단계에서 분리한다.

```java
public sealed interface ConfigurationError {

    record StorageFailure(String objectKey, Throwable cause) implements ConfigurationError {
    }

    record InvalidJson(String objectKey, Throwable cause) implements ConfigurationError {
    }

    record InvalidSchema(String objectKey, List<String> violations) implements ConfigurationError {
    }
}
```

```java
@Component
@RequiredArgsConstructor
public class ConfigurationObjectStorageAdapter implements LoadConfigurationPort {

    private final ObjectStorageClient objectStorageClient;
    private final ObjectMapper objectMapper;
    private final ConfigurationValidator validator;

    @Override
    public Either<ConfigurationError, ServiceConfiguration> load(String objectKey) {
        return readObject(objectKey)
            .flatMap(bytes -> deserialize(objectKey, bytes))
            .flatMap(document -> validate(objectKey, document))
            .map(ConfigurationDocument::toDomain);
    }

    private Either<ConfigurationError, byte[]> readObject(String objectKey) {
        return Try.of(() -> objectStorageClient.getObject(objectKey))
                  .toEither()
                  .mapLeft(cause -> new ConfigurationError.StorageFailure(objectKey, cause));
    }

    private Either<ConfigurationError, ConfigurationDocument> deserialize(
        String objectKey,
        byte[] content
    ) {
        return Try.of(() -> objectMapper.readValue(content, ConfigurationDocument.class))
                  .toEither()
                  .mapLeft(cause -> new ConfigurationError.InvalidJson(objectKey, cause));
    }

    private Either<ConfigurationError, ConfigurationDocument> validate(
        String objectKey,
        ConfigurationDocument document
    ) {
        List<String> violations = validator.validate(document);
        return Either.cond(
            violations.isEmpty(),
            document,
            new ConfigurationError.InvalidSchema(objectKey, List.copyOf(violations))
        );
    }
}
```

`Try.of` 범위를 한 외부 호출로 좁히면 어느 단계에서 실패했는지 정확한 Error로 바꿀 수 있다. 전체 Method를 하나의 `Try.of`로 감싸면 JSON Error와 Storage Error가 섞인다.

## Resource를 안전하게 닫기

Stream, Connection처럼 `AutoCloseable` Resource는 `Try.withResources`를 사용한다. Resource 획득, 본문과 Close 중 발생한 예외가 `Failure`로 보존된다.

```java
public Either<ImportError, ImportSummary> importCsv(Path path) {
    return Try.withResources(() -> Files.newBufferedReader(path, StandardCharsets.UTF_8))
              .of(reader -> parseRows(reader.lines()))
              .toEither()
              .mapLeft(cause -> new ImportError.FileReadFailure(path, cause));
}

private ImportSummary parseRows(Stream<String> lines) {
    List<PassengerRow> rows = lines.skip(1)
                                    .map(csvRowParser::parse)
                                    .toList();
    return ImportSummary.from(rows);
}
```

`reader.lines()`는 Reader Lifetime 안에서만 소비해야 한다. Stream을 Method 밖으로 반환하면 Resource가 닫힌 뒤 Lazy Evaluation이 시작될 수 있다.

## 복구는 실패를 숨기지 않게 설계한다

`recover`로 모든 예외를 Default 값으로 바꾸면 장애가 정상 결과처럼 보인다. 복구 가능한 예외만 구체적으로 처리하고 Metric과 Log를 남긴다.

```java
public PricingPolicy loadPolicy(String centerCode) {
    return Try.of(() -> remotePolicyClient.fetch(centerCode))
              .recoverWith(TimeoutException.class, timeout ->
                  Try.of(() -> policyCache.getRequired(centerCode))
                     .onSuccess(policy -> metrics.increment("pricing.policy.cache_fallback"))
              )
              .getOrElseThrow(cause -> new PricingPolicyUnavailableException(centerCode, cause));
}
```

Fallback Data의 신선도와 허용 가능한 업무 범위를 먼저 정의해야 한다. 결제 금액처럼 오래된 값이 더 위험한 업무에서는 실패가 올바른 선택일 수 있다.

## 비동기 작업과 결합하기

`Try`는 동기 실행 결과다. 비동기 완료를 표현하려면 `CompletionStage<T>` 또는 Reactive Type의 Error Channel을 사용하고, 완료 지점에서 Error를 업무 타입으로 변환한다. `Try.of(() -> future)`는 Future 생성 중 예외만 잡고 비동기 실패는 잡지 못한다.

```java
public CompletionStage<Either<NotificationError, DeliveryReceipt>> send(
    NotificationCommand command
) {
    return notificationClient.sendAsync(command)
                             .thenApply(Either::<NotificationError, DeliveryReceipt>right)
                             .exceptionally(cause -> Either.left(
                                 new NotificationError.ProviderFailure(command.messageId(), unwrap(cause))
                             ));
}
```

## Side Effect를 배치하는 위치

`onFailure`, `onSuccess`와 `peek`은 반환값을 바꾸지 않는 관찰용이다. Business State 변경이나 필수 저장을 넣으면 재시도와 Test가 어려워진다.

```java
return Try.of(externalClient::call)
          .onFailure(cause -> log.warn("External call failed. requestId={}", requestId, cause))
          .toEither()
          .mapLeft(cause -> new ExternalCallError(requestId, cause));
```

민감한 Payload, Token과 개인정보를 Exception Message나 Log에 그대로 남기지 않는다.

## 자주 하는 실수

- `Try.of` 안에 여러 외부 호출과 상태 변경을 모두 넣는다.
- `recover`로 모든 실패를 빈 Collection이나 `null`로 바꾼다.
- `get()`을 호출해 결국 예외를 다시 던진다.
- 비동기 Future의 실패까지 `Try.of`가 잡는다고 오해한다.
- Domain 규칙 실패까지 `Throwable`로 표현해 업무 Error 타입을 잃는다.
- Retry해도 안전하지 않은 상태 변경을 무조건 재시도한다.

## 기억할 점

`Try`는 예외를 없애지 않는다. 예외를 함수 합성 가능한 값으로 바꿔 Adapter 경계에서 분류할 시간을 준다. 외부 API 한 단계씩 좁게 감싸고, `Either`의 업무 Error로 변환하며, 복구 정책은 관측성과 멱등성을 함께 설계해야 한다.

# Reference

- [Vavr Try](https://docs.vavr.io/#_try)
