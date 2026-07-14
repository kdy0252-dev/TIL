---
id: Quartz
started: 2025-05-02
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---

# Quartz

Quartz는 Job 실행 시각과 상태를 DB에 영속화하고 여러 Application Instance가 같은 Schedule을 공유할 수 있는 Scheduler다. 단순 주기 호출은 Spring `@Scheduled`로 충분하지만, 실행 시각을 동적으로 바꾸거나 Misfire·Cluster 조정이 필요하면 Quartz가 적합하다.

## 핵심 개념

- `Job`: 실행할 얇은 Adapter다.
- `JobDetail`: Job Class와 입력 Data를 식별한다.
- `Trigger`: 언제 실행할지 정의한다.
- `JobStore`: Job과 Trigger 상태를 보존한다.
- Misfire: 예정 시각에 실행하지 못했을 때의 처리 규칙이다.

Quartz Job에 긴 업무 로직을 넣지 않고 Application Service를 호출한다.

## Production Job

```java
@DisallowConcurrentExecution
@PersistJobDataAfterExecution
@RequiredArgsConstructor
public class SettlementClosingJob implements Job {

    private final CloseDailySettlementUseCase useCase;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        LocalDate businessDate = LocalDate.parse(
            context.getMergedJobDataMap().getString("businessDate")
        );

        useCase.close(new CloseDailySettlementCommand(businessDate))
            .getOrElseThrow(error -> retryable(error)
                ? refireImmediately(error)
                : doNotRetry(error));
    }

    private JobExecutionException refireImmediately(SettlementError error) {
        JobExecutionException exception = new JobExecutionException(error.message());
        exception.setRefireImmediately(true);
        return exception;
    }

    private JobExecutionException doNotRetry(SettlementError error) {
        return new JobExecutionException(error.message(), false);
    }
}
```

Command에는 Idempotency 기준이 있어야 한다. Cluster Failover나 운영자 재실행 때문에 같은 Job이 다시 호출될 수 있다.

## Job과 Trigger 등록

```java
@Configuration
public class SettlementQuartzConfiguration {

    @Bean
    JobDetail settlementClosingJobDetail(Clock clock) {
        String businessDate = LocalDate.now(clock).minusDays(1).toString();

        return JobBuilder.newJob(SettlementClosingJob.class)
            .withIdentity("daily-settlement-closing")
            .usingJobData("businessDate", businessDate)
            .storeDurably()
            .requestRecovery()
            .build();
    }

    @Bean
    Trigger settlementClosingTrigger(JobDetail settlementClosingJobDetail) {
        CronScheduleBuilder schedule = CronScheduleBuilder
            .cronSchedule("0 10 2 * * ?")
            .inTimeZone(TimeZone.getTimeZone("Asia/Seoul"))
            .withMisfireHandlingInstructionDoNothing();

        return TriggerBuilder.newTrigger()
            .withIdentity("daily-settlement-closing-trigger")
            .forJob(settlementClosingJobDetail)
            .withSchedule(schedule)
            .build();
    }
}
```

Timezone을 명시한다. `DoNothing`은 늦은 정산을 자동 실행하지 않고 별도 복구 흐름에서 결정한다는 정책이다. 업무에 따라 `FireAndProceed`가 맞을 수도 있다.

## Cluster 설정

```yaml
spring:
  quartz:
    job-store-type: jdbc
    properties:
      org.quartz.jobStore.isClustered: true
      org.quartz.jobStore.clusterCheckinInterval: 10000
      org.quartz.threadPool.threadCount: 10
```

모든 Instance는 같은 Quartz Table과 동일한 Clock 기준을 사용해야 한다. Quartz Cluster는 한 Trigger의 중복 실행 가능성을 낮추지만 Business Exactly-Once를 보장하지 않는다.

## 운영 점검표

- Job 입력은 작은 ID·날짜만 저장하고 큰 Object를 직렬화하지 않는다.
- 외부 호출 Timeout과 Retry 상한을 Job 실행 시간보다 짧게 둔다.
- Trigger 지연, 실행 시간, 성공·실패·Refire·Misfire를 측정한다.
- 장기 Job이 Scheduler Thread를 고갈시키지 않게 별도 Worker 구조를 고려한다.
- 운영자 재실행 API에는 권한, Audit와 Idempotency를 둔다.
- DB Migration으로 Quartz Schema Version을 관리한다.

## Test

Application Service는 Quartz 없이 단위 Test하고, Job Adapter는 `JobExecutionContext`의 입력 변환과 Error 정책을 Test한다. Testcontainer DB를 사용해 두 Scheduler Instance가 같은 Trigger를 동시에 실행하지 않는지 통합 Test한다.

# Reference

- [Quartz Scheduler](https://www.quartz-scheduler.org/documentation/)
- [Spring Boot Quartz](https://docs.spring.io/spring-boot/reference/io/quartz.html)
