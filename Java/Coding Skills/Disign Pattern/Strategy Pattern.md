---
id: Strategy Pattern
started: 2025-05-15
tags:
  - ✅DONE
group:
  - "[[Design Pattern]]"
---

# Strategy Pattern

Strategy Pattern은 같은 목적의 Algorithm을 공통 계약으로 분리해 실행 시점에 선택하는 패턴이다. 거대한 `if/else`가 Type, Region과 Policy별 계산을 모두 떠안고 있을 때 유용하다.

## 실무 예제: 배차 점수 정책

배차 후보는 거리, 예상 도착 시간과 운전자 상태를 기준으로 점수를 계산한다. Service가 구체 수식을 알지 않고 `DispatchScoringStrategy`에 의존하게 한다.

```java
public interface DispatchScoringStrategy {

    DispatchMode supports();

    ScoredCandidate score(DispatchContext context, DriverCandidate candidate);
}
```

```java
@Component
public class StandardDispatchScoringStrategy implements DispatchScoringStrategy {

    private static final BigDecimal DISTANCE_WEIGHT = new BigDecimal("0.55");
    private static final BigDecimal ETA_WEIGHT = new BigDecimal("0.35");
    private static final BigDecimal IDLE_WEIGHT = new BigDecimal("0.10");

    @Override
    public DispatchMode supports() {
        return DispatchMode.STANDARD;
    }

    @Override
    public ScoredCandidate score(DispatchContext context, DriverCandidate candidate) {
        BigDecimal score = normalizedDistance(context, candidate).multiply(DISTANCE_WEIGHT)
                                                              .add(normalizedEta(context, candidate).multiply(ETA_WEIGHT))
                                                              .subtract(normalizedIdle(candidate).multiply(IDLE_WEIGHT));
        return new ScoredCandidate(candidate.driverId(), score, supports());
    }
}
```

Strategy 선택을 호출자가 `new`와 `if`로 반복하지 않도록 Registry가 담당한다. 중복 등록은 시작 시점에 실패시킨다.

```java
@Component
public class DispatchScoringStrategyRegistry {

    private final Map<DispatchMode, DispatchScoringStrategy> strategies;

    public DispatchScoringStrategyRegistry(List<DispatchScoringStrategy> strategies) {
        this.strategies = strategies.stream()
                                    .collect(Collectors.toUnmodifiableMap(
                                        DispatchScoringStrategy::supports,
                                        Function.identity(),
                                        (first, duplicate) -> {
                                            throw new IllegalStateException(
                                                "Duplicate dispatch strategy: " + first.supports()
                                            );
                                        }
                                    ));
    }

    public Either<DispatchError, DispatchScoringStrategy> find(DispatchMode mode) {
        return Optional.ofNullable(strategies.get(mode))
                       .<Either<DispatchError, DispatchScoringStrategy>>map(Either::right)
                       .orElseGet(() -> Either.left(new DispatchError.UnsupportedMode(mode)));
    }
}
```

Application Service는 후보 조회, Strategy 선택, 점수 계산과 최종 선택이라는 흐름만 보여 준다.

```java
@Service
@RequiredArgsConstructor
public class CreateDispatchPlanService implements CreateDispatchPlanUseCase {

    private final DriverCandidatePort candidatePort;
    private final DispatchScoringStrategyRegistry strategyRegistry;
    private final DispatchExceptionMapper exceptionMapper;

    @Override
    public DispatchPlanResource create(CreateDispatchPlanCommand command) {
        return strategyRegistry.find(command.mode())
                               .flatMap(strategy -> candidatePort.findAvailable(command.area())
                                   .map(candidates -> candidates.stream()
                                                                .map(candidate -> strategy.score(command.context(), candidate))
                                                                .min(ScoredCandidate::compareTo))
                               )
                               .flatMap(optionalCandidate -> optionalCandidate
                                   .<Either<DispatchError, ScoredCandidate>>map(Either::right)
                                   .orElseGet(() -> Either.left(new DispatchError.NoCandidate(command.area()))))
                               .map(DispatchPlanResource::from)
                               .getOrElseThrow(exceptionMapper::toException);
    }
}
```

## Lambda Strategy

Strategy가 상태도 의존성도 없는 단일 함수라면 Class를 만들지 않고 함수형 Interface와 Method Reference를 사용할 수 있다. 반면 Metric, 설정과 외부 Port가 필요하면 이름 있는 Component가 Test와 관측에 유리하다.

```java
Map<DispatchMode, ToDoubleFunction<DriverCandidate>> scorers = Map.of(
    DispatchMode.NEAREST, DriverCandidate::distanceMeters,
    DispatchMode.FASTEST, DriverCandidate::estimatedArrivalSeconds
);
```

## 사용 기준

- 같은 입력·출력 계약을 가진 Algorithm이 둘 이상 존재한다.
- 실행 시점의 Policy나 Type에 따라 선택한다.
- 각 Algorithm을 독립적으로 Test하고 배포해야 한다.
- 새로운 Strategy 추가가 기존 Service의 분기 수정으로 이어지지 않아야 한다.

Algorithm이 하나뿐이거나 단순 상수 차이만 있다면 Strategy 계층은 과하다. Strategy가 서로 다른 전제와 반환 의미를 갖는다면 억지로 같은 Interface에 넣지 않는다.

## 주의사항

- Strategy 선택 실패를 `null`이나 Default로 숨기지 않는다.
- Registry의 중복 Key를 마지막 값으로 덮어쓰지 않는다.
- Strategy 내부에서 Transaction과 I/O를 무분별하게 수행하지 않는다.
- 점수의 단위, 정규화 범위와 Tie-breaker를 계약에 명시한다.
- 상태를 가진 Singleton Strategy는 동시성 안전성을 검토한다.

## 기억할 점

Strategy Pattern의 핵심은 Class 수를 늘리는 것이 아니라 선택과 실행을 분리하는 것이다. Application Service는 업무 흐름만 조율하고, Algorithm은 독립된 불변 입력과 결과로 Test할 수 있어야 한다.

# Reference

- [Refactoring.Guru - Strategy](https://refactoring.guru/design-patterns/strategy)
