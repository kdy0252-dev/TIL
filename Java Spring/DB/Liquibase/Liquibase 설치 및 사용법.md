---
id: Liquibase
started: 2025-04-25
tags:
  - ✅DONE
  - DB
group: "[[Java Spring DB]]"
---
# Liquibase

## Liquibase란?
데이터베이스 스키마 변경 이력을 코드로 관리해 주는 오픈소스 툴이며 아래와 같은 특징이 있다.
즉, DB의 형상을 관리하는 툴이다.

Liquibase가 수행하는 역할은 아래와 같다.

- **버전 관리된 변경 로그**
    - XML, YAML, JSON, 혹은 순수 SQL 형태로 “ChangeSet”을 정의해 두면, Git 등 소스코드 저장소와 함께 데이터베이스 변경 이력을 관리할 수 있다.
    - ChangeSet마다 고유 ID·작성자·파일명을 지정하기 때문에 누가 언제 어떤 변경을 했는지 추적이 쉽다.
- **다양한 DB 벤더 지원**
    - Oracle, MySQL, PostgreSQL, SQL Server, MariaDB, DB2 등 30여 개 이상의 데이터베이스를 지원한다.
    - 같은 ChangeLog를 환경(dev/staging/prod)에 그대로 재사용할 수 있다.
- **자동화된 마이그레이션**
    - `liquibase update` 한 줄로, 로컬·CI/CD 파이프라인·컨테이너 환경 어디서든 현재 버전과 비교해 필요한 스키마 변경만 선별 적용한다.
    - `rollback` 명령으로 되돌리기, 특정 버전 태그 지정(tag) 후 복원도 간편하다.
- **검증·생성 기능**
    - `diff`·`generateChangeLog` 명령으로 두 DB 간 차이를 확인하거나, 기존 스키마를 ChangeLog로 추출해 쉽게 관리할 수 있다.

## 다른 툴은 없는가?
| 툴 이름               | 특징                                                | 장단점 요약                                                               |
| ------------------ | ------------------------------------------------- | -------------------------------------------------------------------- |
| **Flyway**         | SQL 스크립트 기반. Java API 지원. 간단·경량.                  | • 배포 단순  <br>• SQL 우선(Model-agnostic)  <br>• 복잡한 롤백 기능은 직접 SQL 작성 필요 |
| **Sqitch**         | Perl 기반 스크립트 매니저. 의존성(dependency) 정의로 순서 보장.      | • SQL 스크립트만 사용  <br>• DSL 없이 순수 SQL 제어  <br>• 러닝커브 다소 있음             |
| **Dbmate**         | Go 언어로 작성. 마이그레이션 + 시드 데이터 관리.                    | • 이식성 높음  <br>• 외부 의존성 거의 없음  <br>• 기능은 최소화                          |
| **Prisma Migrate** | Node.js·TypeScript 환경에 특화. 스키마 변경 시 자동 마이그레이션 생성. | • 코드 기반 스키마 정의  <br>• ORM과 통합  <br>• SQL 제어 자유도 낮음                   |
| **Alembic**        | Python(Flask/Django 외 SQLAlchemy) 환경 전용.          | • SQLAlchemy 모델 변경 감지  <br>• 파이썬 스크립트로 유연 제어  <br>• 타 언어 지원 불가       |
## 왜 Liquibase인가?
Liquibase와 Flyway는 Java Spring과 쉽게 연동이되며 안정적이다.
그 중 Flyway는 러닝커브는 낮지만 롤백 동작을 수행할 시에는 별도의 스크립트를 작성해 주어야하는 단점이 존재한다.
즉. 아래와 같은 목적으로 사용 할 수 있다.
- **단순 SQL 중심 + 빠른 셋업** → **Flyway**
- **복잡한 마이그레이션 로직·롤백 필요** → **Liquibase**
따라서 러닝커브만 따라갈 수 있다면 Liquibase가 조금 더 나은 대안이라고 판단된다.
### Liquibase의 장단점
- **장점**
    - XML/YAML/JSON/SQL 어젠다 지원
    - `rollback`, `tag` 같은 고급 기능 내장
    - diff/merge 기능으로 스키마 비교·생성 가능
- **단점**
    - 러닝 커브가 다소 높고 설정이 복잡

## Liquibase 사용법

### Spring Boot에 의존성을 추가한다.
```kotlin title="Luquibase 의존성 추가"
// build.gradle.kts (Kotlin DSL)
plugins {
    id("org.springframework.boot") version "3.1.2"
    id("io.spring.dependency-management") version "1.1.0"
    // 필요시 Liquibase Gradle 플러그인
    // id("org.liquibase.gradle") version "2.1.1"
}

dependencies {
    implementation("org.liquibase:liquibase-core")
}
```

### Application Properties 파일에 설정 추가.
```yaml title="Application.yaml"
spring:
  liquibase:
    enabled: true                # 기본값이 true
    change-log: classpath:db/changelog/db.changelog-master.yaml
    contexts: prod               # (선택) profile 별로 적용할 ChangeSet 구분
    default-schema: public       # (선택) 스키마 지정
    drop-first: false            # 애플리케이션 시작 시 테이블을 모두 삭제할지 여부
```

>[!INFO] db.changelog-master.yaml 파일은 무엇인가?
> 해당 yaml파일은 DB의 변경점을 기록하여 형상을 관리하는 파일이다.
> db.changelog-master.yaml 파일을 잘 작성하는 것이 우리가 해야할 역할이다.


### 위에서 설정한 경로에 맞게 파일을 생성한다.
```css title="db.changelog-master.yaml 파일 생성"
src/
  main/
    resources/
      db/
        changelog/
          db.changelog-master.yaml
```

### Master Change Log 파일 작성
```yaml title="db.changelog-master.yaml 파일"
databaseChangeLog:
  - changeSet:
      id: 1
      author: yourname
      changes:
        - createTable:
            tableName: person
            columns:
              - column:
                  name: id
                  type: bigint
                  constraints:
                    primaryKey: true
                    nullable: false
              - column:
                  name: name
                  type: varchar(255)
                  constraints:
                    nullable: false
```
### 아래와 같이 파일을 세분화하여 관리해야 한다.
```yaml title="include sub change log file"
databaseChangeLog:
  - include:
      file: db/changelog/changelog-001-create-person.yaml
  - include:
      file: db/changelog/changelog-002-add-address.yaml
```

>[!INFO] Change Log만 작성하면 마이그레이션을 자동으로 수행 해 준다.
> 빌드(`./gradlew build`)하면 JAR 내부에 ChangeLog가 포함된다.
> 실서버에 JAR을 올리고 `java -jar app.jar`로 실행하면,
> 1. 애플리케이션이 DB에 접속
> 2. `DATABASECHANGELOG` 테이블을 만들고
> 3. ChangeLog 파일과 비교해 신규 ChangeSet만 순서대로 실행한다.

## 초기의 스키마를 자동으로 뽑아낼 수도 있다.
CLI나 Gradle 플러그인을 이용해서 아래 명령을 수행하면 초기의 스키마를 수작업으로 처리하지 않고 자동으로 뽑아낼수도 있다.
```shell title="초기 스키마 추출 커맨드"
liquibase \
  --url=jdbc:postgresql://localhost:5432/yourdb \
  --username=... --password=... \
  generateChangeLog \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml
```

## CI/CD와도 연계할 수 있다.
build.gradle.kt에 아래와 같이 플러그인을 추가한다.
```kotlin title="add liquibase plugin"
plugins {
  id 'org.liquibase.gradle' version '2.1.1'
}
liquibase {
  activities {
    main {
      changeLogFile 'src/main/resources/db/changelog/db.changelog-master.yaml'
      url System.getenv('JDBC_URL')
      username System.getenv('JDBC_USER')
      password System.getenv('JDBC_PASSWORD')
    }
  }
}
```

CI에서 아래와 같이 스크립트를 실행한다.
```shell title="CI Script"
./gradlew update           # DB에 ChangeLog 적용
./gradlew bootJar          # 앱 빌드
docker build -t myapp:latest .
kubectl apply -f deployment.yaml
```

## 배포 시 고려사항
- **프로파일 분리**
    - `application-prod.yml` 에서만 Liquibase 활성화하거나,
    - `spring.liquibase.contexts` 로 dev/staging/prod ChangeSet을 분리 관리
- **롤백 전략**
    - `liquibase rollback` 명령 혹은 tag 기반 롤백 스크립트를 CI에 포함
- **모니터링·검증**
    - `liquibase status` 로 적용 대기중인 ChangeSet 확인
    - `liquibase history` 로 과거 실행 내역 조회

## DB 스키마 롤백
### 1. 태그(Tag) 기반 롤백
1. **태그 달기**  
    원하는 시점(버전)에 태그를 붙여 놓으면, 나중에 이 태그까지 되돌릴 수 있습니다.
```shell title="add tag"
liquibase \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml \
  tag v1.0
```
2. **롤백 실행**
    이 명령을 실행하면 데이터베이스가 태그를 찍은 시점(여기서는 v1.0)으로 완전 복원됩니다.
```shell title="rollback using tag option"
liquibase \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml \
  rollback v1.0
```

### 2. 변경셋 개수(Rollback Count) 기반
- **rollbackCount N**  
    마지막으로 실행된 N개의 ChangeSet을 역순으로 하나씩 롤백합니다.
```shell title="rollback using rollbackCount option"
liquibase \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml \
  rollbackCount 2
```
위 예시는 가장 최근 실행된 2개의 ChangeSet을 차례로 되돌립니다.

### 3. 날짜(Rollback To Date) 기반
- **rollbackToDate yyyy-MM-dd**  
    특정 날짜 이전까지 실행된 ChangeSet만 롤백합니다.
```shell title="rollback using date option"
liquibase \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml \
  rollbackToDate 2025-04-24
```
지정 날짜 이전의 모든 ChangeSet이 취소됩니다.
### 4. SQL 스크립트 생성 (Rollback SQL)
- **rollbackSQL**  
    실제로 DB에 변경을 적용하지 않고, 롤백을 수행할 SQL 문만 파일로 생성할 때 사용합니다.
```rollback using rollbackSQL option
liquibase \
  --changeLogFile=src/main/resources/db/changelog/db.changelog-master.yaml \
  rollbackCount 1 \
  rollbackSQL \
  > rollback-1.sql
```
생성된 `rollback-1.sql`을 검토한 뒤 직접 DB에 적용할 수 있습니다.

### 5. Maven/Gradle 플러그인에서 롤백
```shell title="rollback using gradle plugin option"
./gradlew rollback -PliquibaseCommandValue=v1.0
```

### 6. ChangeSet에 명시적 Rollback 정의
기본적으로 Liquibase는 대부분의 Change 타입(createTable, addColumn 등)에 대해 자동으로 역(逆)연산을 제공한다.  
다만, 복잡한 SQL을 쓰거나 기본 롤백이 부적합한 경우에는 ChangeSet 내에 `<rollback>` 블록을 작성해 줘야 한다.
```yaml title="rollback using changeSet option"
databaseChangeLog:
  - changeSet:
      id: 5
      author: you
      changes:
        - sql: |
            INSERT INTO user(id, name) VALUES (100, 'Alice');
      rollback:
        - sql: |
            DELETE FROM user WHERE id = 100;
```
이렇게 정의해 두면 `rollbackCount 1` 등으로 이 ChangeSet을 롤백할 때, 지정된 SQL이 실행됩니다.

- **간단히 이전 버전으로** → 태그(tag)/count/date 기반 롤백
- **롤백 SQL만 생성** → `rollbackSQL`
- **앱 내 자동 롤백** → 보통은 프로덕션에서 자동 롤백은 권장되지 않으나, Spring API를 통해 `SpringLiquibase` 빈을 직접 호출해 롤백할 수도 있습니다.
- **커스텀 롤백** → ChangeSet 안에 `<rollback>` 블록을 반드시 정의

> [!INFO] 롤백 작업량이 매우 많다면 Batch 서버와도 연계 할 수 있다.

# Reference
[Liquibase 공식 홈페이지](https://www.liquibase.com/)