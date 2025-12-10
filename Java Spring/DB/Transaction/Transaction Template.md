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
# Transaction Template

## 예시코드
### 가장 기본적인 형태
```Java title="Transaction Template 예시코드"
//transactionTemplate은 Java Spring의 경우에 아래와 같이 Autowired로 받을 수 있다.
//private final TransactionTemplate transactionTemplate

public User findById(int id) {
	transactionTemplate.setReadOnly(true);  
	return transactionTemplate.execute(status ->  
	    repository.findById(id).orElseThrow(() ->
		    new HttpNotFoundException("Error Message!")));
}
```

## Options
- **setPropagationBehavior(int propagationBehavior):**
    - 트랜잭션의 전파 방식을 정의합니다.
    - 예를 들어, `PROPAGATION_REQUIRED`는 현재 트랜잭션이 없으면 새 트랜잭션을 생성하고, 이미 존재하면 기존 트랜잭션에 참여합니다.
    - 다른 전파 옵션으로는 `PROPAGATION_REQUIRES_NEW`, `PROPAGATION_SUPPORTS` 등이 있으며, 비즈니스 로직에 따라 적절한 옵션을 선택해야 합니다.
- **setIsolationLevel(int isolationLevel):**
    - 트랜잭션의 격리 수준을 설정합니다.
    - 격리 수준은 동시에 실행되는 트랜잭션 간의 간섭을 제어하며, `ISOLATION_DEFAULT`, `ISOLATION_READ_COMMITTED`, `ISOLATION_REPEATABLE_READ` 등 다양한 옵션이 제공됩니다.
    - 데이터 일관성과 동시성 제어를 위해 적절한 격리 수준을 선택하는 것이 중요합니다.
- **setTimeout(int timeout):**
    - 트랜잭션이 완료되어야 하는 최대 시간을 초 단위로 설정합니다.
    - 설정한 시간이 초과되면 자동으로 롤백되어, 장시간 실행되어 시스템 리소스를 잠식하는 것을 방지할 수 있습니다.
- **setReadOnly(boolean readOnly):**
    - 트랜잭션을 읽기 전용으로 설정할 수 있습니다.
    - 읽기 전용으로 설정하면 일부 데이터베이스에서 성능 최적화를 기대할 수 있으나, 쓰기 작업이 필요한 경우에는 사용하지 않아야 합니다.
- **setName(String name):**
    - 트랜잭션에 이름을 부여합니다.
    - 디버깅이나 로깅, 모니터링 시 어떤 트랜잭션이 실행되었는지 쉽게 식별할 수 있도록 도와줍니다.
- **execute(TransactionCallback\<T\> action):**
    - 위의 설정들을 적용한 후, 지정한 TransactionCallback 내부의 비즈니스 로직을 실행합니다.
    - 실행 도중 발생하는 예외는 자동으로 롤백 처리되며, 정상 수행 시 결과를 반환합니다.
## Transaction Template을 사용하는 이유
### @Transactional 어노테이션이 아래와 같은 단점이 있어서 사용
- **메서드 레벨에 AOP 가 적용되기 때문에 트랜잭션 단위도 메서드 레벨로 적용(메서드 내에서 지정 불가능)**
- **명시적 제어:**  
    TransactionTemplate은 코드 내에서 트랜잭션의 경계와 속성을 직접 제어할 수 있습니다. 실행 시점에 동적으로 트랜잭션 속성을 설정하거나, 특정 블록 내에서 세밀한 롤백/커밋 제어가 필요한 경우 유용합니다.
- **AOP 한계 극복:**  
    `@Transactional`은 Spring AOP를 기반으로 작동하기 때문에, 같은 클래스 내의 자기 호출(self-invocation) 등 일부 상황에서 의도한 대로 동작하지 않을 수 있습니다. 이러한 경우 TransactionTemplate을 통해 직접 트랜잭션을 관리하면 문제를 피할 수 있습니다.
```Java title="@Transactional이 동작하지 않는 경우 예시"
@Service
public class MyService {

    // methodA는 @Transactional이 적용되어 있지만,
    // 내부에서 호출되는 methodB의 트랜잭션 설정은 무시됩니다.
    @Transactional
    public void methodA() {
        System.out.println("Executing methodA");
        // self-invocation: 같은 클래스 내의 다른 트랜잭셔널 메소드를 호출
        methodB();
    }

    // @Transactional(propagation = Propagation.REQUIRES_NEW)를 적용해도
    // methodA에서 호출될 때는 별도의 트랜잭션으로 실행되지 않습니다.
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void methodB() {
        System.out.println("Executing methodB");
    }
}

```
- **복잡한 트랜잭션 로직 처리:**  
    반복문이나 조건에 따라 트랜잭션 처리를 달리해야 할 때, TransactionTemplate을 사용하면 각 작업마다 트랜잭션 경계를 세밀하게 관리할 수 있습니다.
- **예외 처리의 명시적 관리:**  
    TransactionTemplate은 트랜잭션 내에서 발생한 예외를 직접 캡처하고 처리할 수 있어, 예외 발생 시의 롤백 로직을 보다 명확하게 작성할 수 있습니다.

# Reference
[TransactionTemplate 을 이용한 트랜잭션 제어](https://multifrontgarden.tistory.com/289)