---
id: AWS SDK v2 S3
started: 2026-06-21
tags:
  - ✅DONE
  - AWS
  - S3
  - Java
group:
  - "[[Infra AWS]]"
---
# AWS SDK v2를 이용한 S3 처리

## 1. 개요 (Overview)
**AWS SDK for Java v2**는 S3, Cognito 등 AWS Service를 Java에서 호출하는 Client를 제공합니다. S3는 객체 저장소이므로 파일 시스템과 달리 Directory Rename, 부분 덮어쓰기와 POSIX Lock을 기본 제공하지 않습니다.

---

## 2. Client 구성

```java
S3Client client = S3Client.builder()
        .region(Region.AP_NORTHEAST_2)
        .credentialsProvider(DefaultCredentialsProvider.create())
        .build();
```

운영에서는 Access Key를 설정 파일에 넣지 않고 EKS Pod Identity·IRSA·EC2 Instance Profile처럼 Runtime Identity를 사용합니다.

---

## 3. 객체 복사

```java
CopyObjectRequest request = CopyObjectRequest.builder()
        .copySource(sourceBucket + "/" + sourceKey)
        .destinationBucket(targetBucket)
        .destinationKey(targetKey)
        .build();

client.copyObject(request);
```

대용량 객체는 Multipart Upload·Copy를 사용하고, Checksum과 최종 Object Metadata를 검증해야 합니다.

---

## 4. 실무 사례 적용 관점
사례의 Legacy Migration은 과거 이동 경로 파일을 대상 S3 위치로 옮깁니다. Database Row Migration과 Object Copy는 하나의 ACID Transaction으로 묶을 수 없으므로 재실행 가능한 Step으로 설계해야 합니다.

```text
Source Row
  -> 대상 Object Key 결정
  -> 이미 복사됐는지 확인
  -> S3 Copy
  -> Metadata 기록
  -> Smoke Check
```

같은 입력을 다시 실행해도 동일 Key와 결과를 얻도록 만들고, Database 상태와 S3 객체가 어긋난 경우를 Reconciliation할 수 있어야 합니다.

---

## 5. 운영 주의사항
- Object Key에 Tenant와 환경 경계를 명확히 포함합니다.
- Bucket Policy와 IAM은 최소 권한으로 제한합니다.
- SSE-S3 또는 SSE-KMS 암호화를 사용합니다.
- Timeout, Retry, Multipart Threshold를 객체 크기에 맞게 설정합니다.
- `ListObjects` 결과는 Pagination을 처리합니다.
- 삭제는 Migration 검증과 Retention 기간 이후 별도 단계에서 수행합니다.

---

## 6. S3 일관성과 객체 모델
S3는 Object Key 단위 Put·Delete에 강한 Read-after-write Consistency를 제공하지만 여러 Object를 하나의 Transaction으로 묶지는 않습니다. Database Row와 S3 Object를 동시에 변경할 때도 원자성이 없습니다.

```text
DB Commit 성공 + S3 실패
S3 성공 + DB Commit 실패
```

두 경우를 모두 복구할 수 있도록 상태 기록, 재시도와 Reconciliation을 설계합니다.

Directory처럼 보이는 Prefix는 실제 Directory가 아닙니다. Rename은 Copy 후 Delete이며, 큰 Prefix 전체 Rename은 많은 API 호출과 비용을 발생시킵니다.

## 7. Streaming과 Multipart
작은 파일은 `RequestBody.fromInputStream`으로 보낼 수 있지만 Content Length를 알아야 합니다. 대용량이나 길이를 모르는 Stream은 Multipart Upload를 사용합니다.

```text
CreateMultipartUpload
  -> UploadPart 1..N
  -> CompleteMultipartUpload

실패
  -> AbortMultipartUpload
```

미완료 Multipart Upload가 남으면 Storage 비용이 발생하므로 Lifecycle Rule로 정리합니다. 각 Part의 ETag·Checksum과 최종 결과를 기록합니다.

## 8. Retry와 Timeout
AWS SDK의 Retry는 모든 실패를 안전하게 재실행할 수 있다는 뜻이 아닙니다. Put Object는 같은 Key에 덮어쓰므로 업무 의미를 확인하고, 생성 요청에는 결정적인 Key를 사용합니다.

- Connection Timeout: 연결 수립 상한
- Read Timeout: 응답 읽기 상한
- API Call Attempt Timeout: 한 번의 시도 상한
- API Call Timeout: 모든 Retry를 포함한 전체 상한

전체 작업 Deadline보다 SDK Retry 시간이 길어지지 않게 합니다.

## 9. 보안 모델

### Identity Policy
애플리케이션 Role이 어떤 Bucket·Prefix에 어떤 Action을 할 수 있는지 제한합니다.

### Bucket Policy
Bucket 관점에서 허용 Principal, TLS 강제, 특정 VPC Endpoint와 암호화 조건을 설정할 수 있습니다.

### KMS
SSE-KMS를 사용하면 S3 권한뿐 아니라 KMS Key 권한도 필요합니다. Cross-account Copy는 Source Decrypt와 Target Encrypt 권한을 각각 확인합니다.

Pre-signed URL은 임시 권한이므로 만료 시간, Method, Content Type과 노출 범위를 최소화합니다.

## 10. 사례 Migration 실패 시나리오

### Object는 복사됐지만 결과 기록 실패
다음 실행에서 Target Object의 Size·Checksum·Metadata를 확인한 뒤 성공으로 확정합니다. 무조건 다시 복사할 필요는 없습니다.

### 같은 Legacy Row가 다른 Key로 복사됨
Target Key 생성 규칙을 Source ID 기반의 결정적 함수로 만들고 Mapping Table에 Version을 기록합니다.

### 일부 Tenant만 실패
Tenant·Batch별 Checkpoint를 저장하여 전체 Migration을 처음부터 재실행하지 않습니다.

### Source 삭제 시점
복사 성공, DB Reference 전환, Smoke Check, Retention 기간을 모두 통과한 뒤 별도 Cleanup 단계에서 삭제합니다.

## 11. 테스트 전략
- LocalStack 또는 Test Bucket으로 API 통합을 검증합니다.
- 작은 파일, Multipart 경계, 0 Byte, Unicode Key를 테스트합니다.
- Timeout·403·404·Slow Response 오류 변환을 테스트합니다.
- 동일 Migration을 두 번 실행해 결과가 중복되지 않는지 확인합니다.
- Production과 동일 IAM 조건을 별도 환경에서 검증합니다.

---

## 13. 실무 사례 적용 진단과 개선 과제

S3 연동은 AWS SDK v2 기반이지만 업로드 크기별 Multipart 기준, Retry·Timeout, Object Metadata와 Lifecycle이 업무별로 흩어질 수 있습니다. 애플리케이션 설정 파일의 장기 Access Key 사용 가능성도 제거 대상입니다.

EKS에서는 IRSA로 전환하고 Bucket·Prefix·KMS 권한을 최소화합니다. 큰 파일은 Multipart Upload와 중단 Upload 정리 Lifecycle을 적용하며 Content Type·Checksum·최대 크기를 검증합니다. 외부 입력 Key를 그대로 Object Key로 사용하지 않습니다.

완료 기준은 Static Credential 없이 동작하고, Timeout·부분 업로드·중복 요청 Test에서 고아 Object가 남지 않으며, Versioning·Lifecycle·복구 절차가 Bucket별로 정의된 상태입니다.

---

# Reference
- [AWS SDK for Java 2.x](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/home.html)
- [Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html)
- [[멱등성과 Reconciliation]]
