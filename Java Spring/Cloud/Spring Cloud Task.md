---
id: Spring Cloud Task
started: 2025-08-28
tags:
  - ✅DONE
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud Task

## 1. 개요 (Overview)
**Spring Cloud Task**는 유한한 시간 동안 실행되고 종료되는 **단기(Short-lived) 마이크로서비스**를 개발하기 위한 프레임워크입니다.
JVM의 시작과 종료를 Task의 생명주기(Lifecycle)로 매핑하고, 실행 이력(시작 시간, 종료 시간, 상태, 에러 메시지)을 데이터베이스에 영구적으로 저장합니다.
주로 **Spring Batch**와 결합하여, 클라우드 환경(Kubernetes Job, Cloud Foundry Task)에서 배치 작업을 모니터링하고 추적하는 데 사용됩니다.

---

## 2. 주요 기능 및 아키텍처

### 2.1 Task Repository
Spring Cloud Task는 실행 상태를 저장하기 위해 RDBMS를 필수로 요구합니다.
`@EnableTask`를 선언하면 자동으로 `DataSource`를 감지하여 다음과 같은 테이블을 관리합니다.
- **TASK_EXECUTION**: 태스크의 메타데이터(ID, Start Time, End Time, Exit Code, Error Message).
- **TASK_EXECUTION_PARAMS**: 태스크 실행 시 전달된 파라미터 (예: `run.date=2025-01-01`).

### 2.2 LifeCycle Integration
Spring Boot의 `ApplicationRunner`나 `CommandLineRunner`가 완료되면 Task도 종료된 것으로 간주합니다.
- **Before Task**: `TaskExecutionListener.onTaskStartup()`
- **After Task**: `TaskExecutionListener.onTaskEnd()`
- **Exception**: 예외 발생 시 `onTaskFailed()`가 호출되고, DB에 에러 스택트레이스가 저장됩니다.

### 2.3 Spring Batch 통합
Spring Batch는 Job Repository에 배치 실행 이력을 남기지만, "어떤 물리적 프로세스(Pod)에서 실행되었는지"는 관리하지 않습니다.
Spring Cloud Task는 **Task Execution ID**와 **Batch Job Execution ID**를 매핑하여, "이 배치가 어느 컨테이너에서 언제 돌았는지"를 추적할 수 있게 해줍니다.

---

## 3. 구현 예제

### 3.1 단순 Task 구현

**의존성 (Gradle)**
```groovy
implementation 'org.springframework.cloud:spring-cloud-starter-task'
runtimeOnly 'com.h2database:h2' // 또는 MySQL, Postgres
```

**Java Code**
```java
@SpringBootApplication
@EnableTask // 필수: TaskRepository 설정 및 리스너 등록
public class SimpleTaskInfoApplication {

    public static void main(String[] args) {
        SpringApplication.run(SimpleTaskInfoApplication.class, args);
    }

    @Bean
    public ApplicationRunner applicationRunner() {
        return args -> {
            System.out.println("### Heavy Processing Start ###");
            Thread.sleep(2000);
            System.out.println("### Heavy Processing End ###");
        };
    }
    
    @Bean
    public SimpleTaskListener taskListener() {
        return new SimpleTaskListener();
    }
}

class SimpleTaskListener implements TaskExecutionListener {
    @Override
    public void onTaskStartup(TaskExecution taskExecution) {
        System.out.println("Task Started: " + taskExecution.getExecutionId());
    }

    @Override
    public void onTaskEnd(TaskExecution taskExecution) {
        System.out.println("Task Finished: " + taskExecution.getExitCode());
    }

    @Override
    public void onTaskFailed(TaskExecution taskExecution, Throwable throwable) {
        System.err.println("Task Failed: " + throwable.getMessage());
    }
}
```

**실행 결과 (DB 확인)**
```sql
SELECT * FROM TASK_EXECUTION;
-- TASK_EXECUTION_ID | START_TIME | END_TIME | EXIT_CODE | EXIT_MESSAGE ...
-- 1                 | ...        | ...      | 0         | null
```

### 3.2 Spring Batch와 함께 사용

Spring Batch Job이 정의되어 있으면, Spring Cloud Task는 자동으로 해당 Job Execution을 Task Execution 감쌉니다.

```java
@EnableTask
@EnableBatchProcessing
@SpringBootApplication
public class BatchTaskApplication {

    @Bean
    public Job myJob(JobBuilderFactory jobs, StepBuilderFactory steps) {
        return jobs.get("myJob")
                .start(steps.get("myStep")
                        .tasklet((contribution, chunkContext) -> {
                            System.out.println("Batch Step Executed!");
                            return RepeatStatus.FINISHED;
                        })
                        .build())
                .build();
    }
}
```
이 경우 `TASK_TASK_BATCH` 테이블에 매핑 정보가 저장됩니다.

---

## 4. 운영 시 고려사항 (Operational Considerations)

### 4.1 Exit Codes 매핑
클라우드 플랫폼(K8s)은 컨테이너의 Exit Code(0: 성공, 그 외: 실패)를 보고 재시작(Restart) 여부를 결정합니다.
Java 예외가 발생하더라도 Spring Boot가 0을 반환하면 K8s는 성공으로 오인할 수 있습니다.
Spring Boot의 `ExitCodeGenerator` 인터페이스를 구현하거나, 예외를 Main 쓰레드 밖으로 던져서 비정상 종료를 유도해야 합니다.

### 4.2 Single Instance Execution
`@EnableTask`에는 동시 실행 방지 기능(`spring.cloud.task.single-instance-enabled=true`)이 있습니다.
같은 이름의 Task가 이미 돌고 있다면, 새로운 인스턴스는 실행되지 않고 바로 종료됩니다. (DB Lock 활용)

### 4.3 리소스 정리
태스크 실행 이력이 계속 쌓이면 DB 용량이 커지므로, 주기적으로 오래된 이력을 삭제하는 작업이 필요합니다 (예: 30일 지난 로그 삭제).

# Reference
- [Spring Cloud Task Reference](https://docs.spring.io/spring-cloud-task/docs/current/reference/html/)
- [Spring Batch Integration](https://docs.spring.io/spring-cloud-task/docs/current/reference/html/#batch-association)
- [Task Samples](https://github.com/spring-cloud/spring-cloud-task/tree/main/spring-cloud-task-samples)