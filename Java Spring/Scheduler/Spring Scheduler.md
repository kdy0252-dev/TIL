---
id: Spring Scheduler
started: 2025-03-21
tags:
  - ✅DONE
group: "[[Java Spring]]"
---

# Spring Scheduler

Spring Scheduler는 Application Process 안에서 정해진 주기로 Method를 호출한다. 간단하지만 실행 상태를 영속화하지 않고 여러 Pod가 모두 같은 Method를 실행한다. 따라서 “호출 시각”과 “업무 실행 보장”을 구분해야 한다.

## fixedRate, fixedDelay, cron

- `fixedRate`: 시작 시각 기준 주기다. 실행이 길면 겹칠 수 있다.
- `fixedDelay`: 이전 실행 완료 후 다음 실행까지의 간격이다.
- `cron`: 달력 시각 기준이다. Timezone을 반드시 명시한다.

## 얇은 Scheduler Adapter

```java
@Component
@RequiredArgsConstructor
public class VehicleStatusReconciliationScheduler {

    private final ReconcileVehicleStatusUseCase useCase;
    private final Clock clock;

    @Scheduled(
        cron = "${application.scheduler.vehicle-reconciliation.cron}",
        zone = "Asia/Seoul"
    )
    public void reconcile() {
        ReconciliationWindow window = ReconciliationWindow.endingAt(clock.instant());

        useCase.reconcile(window)
            .peekLeft(error -> {
                throw new VehicleReconciliationException(error);
            });
    }
}
```

Scheduler는 시간 계산과 Use Case 호출만 한다. 조회 Pagination, 외부 API Retry, 상태 전이와 Transaction은 Application 내부 Service로 위임한다.

## 여러 Pod에서 한 번만 실행하기

`@Scheduled` 자체에는 분산 Lock이 없다. 선택지는 세 가지다.

1. 모든 Pod가 실행해도 되도록 업무를 Idempotent하게 만든다.
2. DB/Redis 기반 Lease를 얻은 Instance만 실행한다.
3. 영속 Schedule이 필요하면 Quartz, Kubernetes CronJob 또는 Workflow Engine을 사용한다.

Lock만 믿지 말고 업무 Key에 Unique Constraint나 처리 완료 상태를 둔다. Lock 만료 직전 긴 작업이 겹칠 수 있기 때문이다.

```java
@Service
@RequiredArgsConstructor
public class VehicleStatusReconciliationService
    implements ReconcileVehicleStatusUseCase {

    private final ReconciliationLeasePort leasePort;
    private final VehicleStatusReconciler reconciler;

    @Override
    public Either<ReconciliationError, ReconciliationSummary> reconcile(
        ReconciliationWindow window
    ) {
        return leasePort.acquire("vehicle-status-reconciliation", Duration.ofMinutes(5))
            .toEither(() -> new ReconciliationError.AlreadyRunning(window))
            .flatMap(lease -> Try.withResources(() -> lease)
                .of(ignored -> reconciler.reconcile(window))
                .toEither()
                .mapLeft(cause -> new ReconciliationError.ExecutionFailure(window, cause)))
            .flatMap(Function.identity());
    }
}
```

Lease는 `AutoCloseable`로 감싸 성공·실패 모두 해제한다. Lease Store 장애 시 실행을 건너뛸지 결정하고 Alert한다.

## Thread Pool

기본 Scheduler Thread 하나에서 느린 Job이 다른 Job을 막을 수 있다.

```java
@Configuration
@EnableScheduling
public class SchedulingConfiguration implements SchedulingConfigurer {

    @Override
    public void configureTasks(ScheduledTaskRegistrar registrar) {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(4);
        scheduler.setThreadNamePrefix("application-scheduler-");
        scheduler.setWaitForTasksToCompleteOnShutdown(true);
        scheduler.setAwaitTerminationSeconds(30);
        scheduler.initialize();
        registrar.setTaskScheduler(scheduler);
    }
}
```

Pool을 키운다고 동일 Job의 중복 실행 문제가 해결되지는 않는다. DB Connection과 외부 API 허용량에 맞춰 크기를 정한다.

## 운영과 Test

- 마지막 시작·성공 시각, 실행 시간, 처리 수, 실패 원인을 Metric으로 남긴다.
- Clock을 주입해 날짜 경계와 DST를 Test한다.
- 외부 호출에는 Timeout을 둔다.
- 실패를 `log.info`만 하고 삼키지 말고 Alert 가능한 Error로 만든다.
- 배포 종료 시 새 작업을 받지 않고 진행 중 작업을 Drain한다.
- Scheduler Adapter 단위 Test와 실제 Scheduling을 확인하는 얇은 통합 Test를 분리한다.

## 기억할 점

`@Scheduled`는 Method를 호출할 뿐이다. 중복 방지, 재시도, 실행 이력과 복구가 필요하면 Application 설계나 더 적합한 Scheduler가 책임져야 한다.

# Reference

- [Spring Task Execution and Scheduling](https://docs.spring.io/spring-framework/reference/integration/scheduling.html)
