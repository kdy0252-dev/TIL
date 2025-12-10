---
id: Spring Cloud AWS
started: 2025-08-11
tags:
  - ⏳DOING
group:
  - "[[Java Spring Cloud]]"
---
# Spring Cloud AWS

## 1. 개요 (Overview)
**Spring Cloud AWS**는 Spring 개발자들이 Amazon Web Services(AWS)의 다양한 관리형 서비스들을 Spring 프레임워크의 Idiom(관용구)과 패턴(DI, Annotation 기반 설정)으로 쉽고 자연스럽게 사용할 수 있도록 돕는 프로젝트입니다.
AWS SDK를 직접 사용하는 것보다 훨씬 추상화된 레벨에서 서비스를 연동할 수 있으며, 특히 환경 설정(Parameter Store, Secrets Manager)이나 메시징(SQS, SNS) 영역에서 강력한 편의성을 제공합니다.

최근에는 `Spring Cloud AWS 3.0`이 릴리즈되면서 **AWS SDK v2**를 기반으로 완전히 재작성되었습니다. (구버전은 2.x 기반)

---

## 2. 주요 기능 및 모듈 (Key Features)

### 2.1 Parameter Store & Secrets Manager Config
- **역할**: `application.yml`에 민감한 정보를 넣는 대신, AWS Systems Manager(SSM) Parameter Store나 Secrets Manager에 저장된 값을 Spring Boot의 `PropertySource`로 자동으로 로딩합니다.
- **장점**: 설정 변경 시 애플리케이션을 재배포하지 않고 값만 변경할 수 있으며, IAM을 통해 접근 권한을 세밀하게 제어할 수 있습니다.

### 2.2 S3 (Simple Storage Service)
- **ResourceLoadder 통합**: `s3://bucket-name/object-key` 형태의 URL로 S3 객체를 마치 로컬 파일(`classpath:`, `file:`)처럼 쉽게 읽고 쓸 수 있습니다.
- **Template 제공**: `S3Template`을 통해 파일 업로드/다운로드, Presigned URL 생성 등을 간편하게 수행할 수 있습니다.

### 2.3 SQS (Simple Queue Service) & SNS
- **메시지 리스너**: `@SqsListener` 애노테이션 하나로 SQS 메시지를 수신하고 처리할 수 있습니다. (Spring AMQP의 `@RabbitListener`와 유사)
- **Template**: `SqsTemplate`, `SnsTemplate`을 통해 메시지 발행을 추상화합니다.

### 2.4 RDS & IAM Authentication
- JDBC URL에 비밀번호를 박아넣는 대신, IAM 인증 토큰을 사용하여 RDS에 접속하는 기능을 지원합니다. 보안성을 획기적으로 높일 수 있습니다.

---

## 3. 구현 및 사용 예제 (Spring Cloud AWS 3.x)

### 3.1 Parameter Store 설정
`import` 구문을 사용하여 AWS 설정 소스를 가져옵니다.

**application.yml**
```yaml
spring:
  config:
    import: "aws-parameterstore:/config/myservice/"
  cloud:
    aws:
      region:
        static: ap-northeast-2
```
이렇게 하면 AWS Parameter Store의 `/config/myservice/` 경로 하위에 있는 키-값 쌍들이 자동으로 Spring 환경 변수로 주입됩니다.

### 3.2 SQS Listener 구현

**1) 의존성 추가**
```groovy
implementation 'io.awspring.cloud:spring-cloud-aws-starter-sqs'
```

**2) 리스너 코드**
```java
@Service
@Slf4j
public class OrderMessageListener {

    // 큐 이름이나 URL을 지정. 
    // deletionPolicy: 메시지 처리 성공 시 삭제(ON_SUCCESS), 항상 삭제(ALWAYS) 등 설정 가능
    @SqsListener(value = "order-queue", deletionPolicy = SqsMessageDeletionPolicy.ON_SUCCESS)
    public void receiveOrder(@Payload OrderDto order, @Headers Map<String, Object> headers) {
        log.info("Received Order: {}", order);
        processOrder(order);
        // 예외 발생 시 트랜잭션 롤백처럼 동작하여 메시지가 큐에 남거나 DLQ로 이동됨
    }
}
```

### 3.3 S3 파일 업로드 (`S3Template`)

**1) 의존성 추가**
```groovy
implementation 'io.awspring.cloud:spring-cloud-aws-starter-s3'
```

**2) 업로드 서비스**
```java
@Service
@RequiredArgsConstructor
public class FileService {

    private final S3Template s3Template;

    public String uploadFile(String bucketName, String key, MultipartFile file) throws IOException {
        S3Resource resource = s3Template.upload(bucketName, key, file.getInputStream());
        return resource.getURL().toString();
    }
    
    public void downloadFile(String bucketName, String key) {
        S3Resource resource = s3Template.download(bucketName, key);
        // resource.getInputStream() 으로 읽기 가능
    }
}
```

---

## 4. 운영 시 고려사항 (Operational Considerations)

### 4.1 자격 증명 (Credentials) 관리
Spring Cloud AWS는 `DefaultCredentialsProvider` 체인을 따릅니다.
1.  환경 변수 (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2.  Java 시스템 프로퍼티
3.  웹 자격 증명 (Web Identity Token)
4.  설정 파일 프로필 (`~/.aws/credentials`)
5.  **EC2/ECS 인스턴스 프로파일 (Instance Profile)**

운영 환경(EC2, ECS, EKS)에서는 절대로 액세스 키를 파일에 저장하지 말고, 마지막 5번 **IAM Role(인스턴스 프로파일/Task Role)**을 사용하여 키 관리 없이 권한을 부여하는 것이 Best Practice입니다.

### 4.2 로컬 개발 환경
로컬에서는 실제 AWS에 붙기보다는 **LocalStack**을 활용하는 것이 비용 절감 및 속도 면에서 좋습니다. Spring Cloud AWS는 endpoint override 기능을 제공하므로 LocalStack 주소로 쉽게 변경 가능합니다.

```yaml
spring:
  cloud:
    aws:
      endpoint: http://localhost:4566 # LocalStack
```

# Reference
https://spring.io/projects/spring-cloud