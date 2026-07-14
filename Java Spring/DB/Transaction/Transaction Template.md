---
id: Transaction Template
started: 2025-03-13
tags:
  - Java
  - Spring
  - DB
  - JPA
  - ✅DONE
group: "[[Java Spring DB]]"
---
# TransactionTemplate로 트랜잭션 경계를 직접 제어하기

Transaction은 여러 Database 작업을 하나의 성공 또는 실패 단위로 묶는다. 주문을 저장했는데 재고 차감에 실패했다면 두 작업을 모두 되돌려야 중간 상태가 남지 않는다. Spring에서는 보통 `@Transactional`로 이 경계를 선언하지만, 실행 중인 Method의 일부 구간만 묶거나 반복마다 새 Transaction을 시작해야 할 때는 Programmatic 방식이 더 명확하다.

`TransactionTemplate`은 Transaction 시작, Commit, Rollback과 Resource 정리를 대신 수행하고, 개발자는 Callback 안에 업무 로직만 작성하게 하는 Spring의 Imperative Transaction API다. Reactive Flow에서는 Blocking 기반의 이 Class가 아니라 `TransactionalOperator`를 사용한다.

## 가장 기본적인 사용법

`PlatformTransactionManager`를 받아 Template을 한 번 구성하고 재사용한다.

```java
@Service
public class UserQueryService {

    private final TransactionTemplate readOnlyTransaction;
    private final UserRepository userRepository;

    public UserQueryService(
            PlatformTransactionManager transactionManager,
            UserRepository userRepository
    ) {
        this.readOnlyTransaction = new TransactionTemplate(transactionManager);
        this.readOnlyTransaction.setReadOnly(true);
        this.userRepository = userRepository;
    }

    public User findById(long id) {
        return readOnlyTransaction.execute(status ->
            userRepository.findById(id)
                .orElseThrow(() -> new UserNotFoundException(id))
        );
    }
}
```

`execute()`가 Callback을 호출하기 전에 Transaction을 시작한다. Callback이 정상 반환하면 Commit하고, 처리되지 않은 Runtime Exception이나 Error가 밖으로 나오면 Rollback한다. 반환값이 없는 작업에는 `executeWithoutResult()`가 읽기 쉽다.

```java
transactionTemplate.executeWithoutResult(status -> {
    orderRepository.save(order);
    inventory.decrease(order.items());
});
```

## @Transactional과 무엇이 다른가?

두 방식은 같은 `PlatformTransactionManager`와 Spring Transaction 추상화를 사용한다. 차이는 경계를 표현하는 위치다.

| 구분 | `@Transactional` | `TransactionTemplate` |
| --- | --- | --- |
| 경계 | Proxy가 Method 호출을 감쌈 | Callback Block이 경계 |
| 코드 결합 | Annotation 중심 | Spring API가 코드에 직접 등장 |
| 가독성 | 일반적인 Service Method에 간결 | 일부 구간·동적 흐름에 명확 |
| Self Invocation | Proxy를 거치지 않으면 새 설정 미적용 | 직접 실행하므로 적용 |
| 반복별 Transaction | 별도 Bean 분리가 흔함 | 반복 안에서 명시 가능 |

일반적인 업무 Method 전체가 하나의 Transaction이면 `@Transactional`이 기본 선택이다. Programmatic 제어가 필요하다는 이유만으로 모든 Service를 Template으로 바꾸면 업무 코드가 Infrastructure API에 더 강하게 결합한다.

## Method의 일부만 Transaction으로 묶기

느린 외부 API 호출을 Transaction 안에 두면 Database Connection과 Lock을 호출 시간만큼 오래 점유할 수 있다. 외부 데이터를 먼저 가져온 뒤 짧은 저장 구간만 묶을 수 있다.

```java
public Receipt synchronizePayment(String paymentId) {
    PaymentResult result = paymentClient.fetch(paymentId);

    return transactionTemplate.execute(status -> {
        Payment payment = paymentRepository.getByPaymentId(paymentId);
        payment.apply(result);
        return receiptRepository.save(Receipt.from(payment));
    });
}
```

하지만 외부 호출을 Transaction 밖으로 옮겼다고 분산 원자성이 생기는 것은 아니다. 호출과 저장 사이에 상태가 바뀔 수 있으므로 Idempotency Key, 상태 전이 검증, Outbox나 Saga 같은 별도 설계가 필요할 수 있다.

## 반복 작업의 Transaction 분리

대량 처리 전체를 하나의 Transaction으로 묶으면 Persistence Context가 커지고 하나의 실패가 전체 Rollback을 만든다. 항목마다 독립 실패가 허용된다면 반복 내부에서 경계를 나눌 수 있다.

```java
for (ImportRow row : rows) {
    try {
        transactionTemplate.executeWithoutResult(status -> importOne(row));
    } catch (DataIntegrityViolationException exception) {
        failureRecorder.record(row, exception);
    }
}
```

각 항목 Commit은 부분 성공을 허용한다는 업무 결정이다. 모두 성공하거나 모두 실패해야 하는 작업에는 적용하면 안 된다. 대량 처리는 Chunk, 재시작, Skip 정책이 필요한 경우 Spring Batch가 더 적합하다.

## Rollback을 직접 표시하기

Exception을 던지지 않고도 현재 Transaction을 Rollback 전용으로 만들 수 있다.

```java
OperationResult result = transactionTemplate.execute(status -> {
    if (!policy.allows(command)) {
        status.setRollbackOnly();
        return OperationResult.rejected();
    }

    repository.save(command.toEntity());
    return OperationResult.accepted();
});
```

다만 반환값은 성공처럼 보이는데 실제 저장은 Rollback되는 코드가 될 수 있다. 검증 실패가 정상적인 업무 결과인지, Exception이어야 하는지 먼저 정하고 제한적으로 사용한다.

## 주요 설정

### Propagation

Propagation은 이미 Transaction이 있을 때 현재 작업이 어떻게 참여할지를 결정한다.

- `REQUIRED`: 기존 Transaction에 참여하고, 없으면 새로 만든다. 기본값이다.
- `REQUIRES_NEW`: 기존 Transaction을 잠시 중단하고 독립 Transaction을 만든다.
- `SUPPORTS`: 있으면 참여하고, 없어도 Transaction 없이 실행한다.
- `MANDATORY`: 기존 Transaction이 없으면 예외를 던진다.
- `NOT_SUPPORTED`: 기존 Transaction을 중단하고 Transaction 없이 실행한다.
- `NEVER`: Transaction 안에서 호출되면 예외를 던진다.
- `NESTED`: Savepoint 기반 중첩 Transaction을 시도하며 Transaction Manager 지원 여부를 확인해야 한다.

```java
TransactionTemplate requiresNew = new TransactionTemplate(transactionManager);
requiresNew.setPropagationBehavior(TransactionDefinition.PROPAGATION_REQUIRES_NEW);
```

`REQUIRES_NEW`로 Audit Log를 저장하면 바깥 업무가 Rollback되어도 Log가 남을 수 있다. 반대로 별도 Connection이 필요해 Connection Pool 고갈이나 Lock 대기를 만들 수 있다. “무조건 안전한 새 Transaction”이 아니라 독립 Commit이 업무적으로 옳을 때만 사용한다.

### Isolation

Isolation Level은 동시에 실행되는 Transaction이 서로의 변경을 어디까지 볼 수 있는지 정한다. Database 기본값을 따르는 `ISOLATION_DEFAULT`가 보통 출발점이다. 더 강한 Isolation은 이상 현상을 줄이지만 Lock 충돌, 재시도와 처리량 비용이 생길 수 있다.

특정 Level을 설정하기 전에 Dirty Read, Non-repeatable Read, Phantom Read 중 어떤 문제가 실제로 발생하는지와 Database의 MVCC 구현을 확인한다. Isolation만 높이는 대신 Unique Constraint, Atomic Update, Optimistic Lock이 더 직접적인 해법일 수도 있다.

### Timeout과 Read Only

Timeout은 무한한 Lock 대기와 장기 Transaction을 제한하는 방어선이다. 실제 JDBC Driver와 Database가 이를 어떻게 적용하는지 확인해야 하며, 외부 HTTP 호출 Timeout을 대신하지 않는다.

Read Only는 “쓰기 금지 보안 장치”가 아니다. JPA Provider가 Flush 동작을 최적화하거나 Database에 Hint를 전달할 수 있지만, 지원 방식은 조합마다 다르다. 쓰기를 구조적으로 막으려면 권한이 제한된 Read Replica 계정 같은 Database 수준 통제도 필요하다.

## 설정을 실행 중인 공유 Template에서 바꾸지 않기

`TransactionTemplate`의 설정은 Instance에 보관된다. Singleton Bean으로 공유하면서 호출 직전에 `setReadOnly()`나 `setPropagationBehavior()`를 바꾸면 동시 요청이 서로의 설정에 영향을 줄 수 있다. 서로 다른 정책은 시작할 때 별도 Template으로 구성한다.

```java
@Bean
TransactionTemplate readOnlyTransaction(PlatformTransactionManager manager) {
    TransactionTemplate template = new TransactionTemplate(manager);
    template.setReadOnly(true);
    template.setTimeout(3);
    return template;
}
```

## 기억할 점

`TransactionTemplate`의 장점은 Annotation을 피하는 데 있지 않다. **업무 Method와 Transaction 경계가 일치하지 않을 때 그 경계를 코드로 정확히 보이는 것**이 핵심이다. 경계를 짧게 유지하고, 외부 I/O를 신중히 분리하며, Propagation과 부분 Commit이 업무 규칙에 맞는지 Test해야 한다.

# Reference
[Spring Framework - Programmatic Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction/programmatic.html)
[Spring Framework - Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction.html)
[Spring API - TransactionTemplate](https://docs.spring.io/spring-framework/docs/current/javadoc-api/org/springframework/transaction/support/TransactionTemplate.html)
