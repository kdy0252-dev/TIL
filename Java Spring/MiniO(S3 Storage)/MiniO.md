---
id: MinIO
started: 2025-12-10
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# MinIO (High Performance Object Storage)

## 1. 개요 (Overview)
**MinIO**는 AWS S3 API와 100% 호환되는 고성능 오픈 소스 **객체 스토리지(Object Storage)** 서버입니다.
"Kubernetes-Native"를 표방하며, 특히 프라이빗 클라우드나 온프레미스 환경에서 S3를 대체할 수 있는 가장 강력한 솔루션입니다.
단순히 파일을 저장하는 것을 넘어, 머신러닝 데이터 레이크, 백업 스토리지, 아카이빙 등 엔터프라이즈급 워크로드에 사용됩니다.

---

## 2. 핵심 기술 (Core Technologies)

### 2.1 S3 호환성 (Compatibility)
MinIO는 처음부터 AWS S3 API 표준을 따르도록 설계되었습니다. 따라서 개발자는 `AWS SDK for Java`, `boto3 (Python)` 등 기존 S3 라이브러리를 코드 수정 없이(Endpoint만 변경하여) 그대로 사용할 수 있습니다.

### 2.2 이레이저 코딩 (Erasure Coding)
MinIO는 **RAID** 기술을 사용하지 않습니다. 대신 **Reed-Solomon** 알고리즘 기반의 Erasure Coding을 사용하여 데이터를 보호합니다.
- 데이터 원본을 N개의 데이터 블록과 M개의 패리티(Parity) 블록으로 나누어 여러 디스크에 분산 저장합니다.
- N+M개의 디스크 중 M개까지 디스크가 고장나도 데이터를 복구할 수 있습니다.
- 예: 16개 드라이브로 구성된 경우, 8개(Data) + 8개(Parity)로 설정하면 절반인 8개의 디스크가 동시에 죽어도 데이터가 안전합니다.

### 2.3 Bit Rot Protection
하드디스크 노후화로 인해 비트(Bit)가 조용히 바뀌는 "Bit Rot" 현상을 방지합니다. 파일을 읽을 때마다 체크섬을 검증하여, 손상이 발견되면 패리티 블록을 이용해 즉시 복구합니다.

---

## 3. 배포 아키텍처 (Deployment Architecture)

### 3.1 Single Node Single Drive (Standalone)
- 개발 및 테스트 용도. Docker 컨테이너 하나로 띄우는 방식.
- 데이터 영속성은 보장되지만 고가용성은 없습니다.

### 3.2 Distributed MinIO
- 실제 운영(Production) 환경에서 사용.
- 여러 서버(Node)의 여러 디스크(Drive)를 하나의 거대한 스토리지 풀로 묶습니다.
- **장점**: 고가용성(HA), 데이터 보호(Erasure Coding), 확장성(Scale-out). 서버 한 대가 꺼져도 서비스는 중단되지 않습니다.

---

## 4. 구현 예제 (Java Spring Boot)

### 4.1 Docker Compose (로컬 개발용)
MinIO 서버와 웹 콘솔을 함께 띄웁니다.

```yaml
version: '3.8'
services:
  minio:
    image: minio/minio
    container_name: minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000" # API 포트
      - "9001:9001" # 콘솔(UI) 포트
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password1234
    volumes:
      - ./data:/data
```

### 4.2 Spring Boot Configuration
AWS SDK v2를 사용하여 MinIO에 접속하는 설정입니다.

```java
@Configuration
public class S3Config {

    @Value("${minio.endpoint}")
    private String endpoint; // http://localhost:9000

    @Value("${minio.access-key}")
    private String accessKey;

    @Value("${minio.secret-key}")
    private String secretKey;

    @Bean
    public S3Client s3Client() {
        return S3Client.builder()
                .region(Region.US_EAST_1) // MinIO는 Region이 의미 없으나 SDK 필수값임
                .endpointOverride(URI.create(endpoint))
                .credentialsProvider(StaticCredentialsProvider.create(
                        AwsBasicCredentials.create(accessKey, secretKey)))
                .forcePathStyle(true) // 중요: Virtual Host 방식 대신 Path Style 사용 (필수)
                .build();
    }

    @Bean
    public S3Presigner s3Presigner(S3Client s3Client) {
        return S3Presigner.builder()
                .serviceClient(s3Client)
                .build();
    }
}
```

### 4.3 Service Implementation (Presigned URL)
파일을 바로 업로드/다운로드하지 않고, 클라이언트에게 **임시 서명된 URL(Presigned URL)**을 발급하여 클라이언트가 직접 MinIO와 통신하게 하는 패턴입니다. (서버 부하 감소).

```java
@Service
@RequiredArgsConstructor
public class StorageService {

    private final S3Presigner s3Presigner;
    private final S3Client s3Client;

    // 업로드용 URL 발급 (PUT) - 10분 유효
    public String createUploadUrl(String bucket, String key, String contentType) {
        PutObjectRequest objectRequest = PutObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .contentType(contentType)
                .build();

        PutObjectPresignRequest presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(10))
                .putObjectRequest(objectRequest)
                .build();

        PresignedPutObjectRequest presignedRequest = s3Presigner.presignPutObject(presignRequest);
        return presignedRequest.url().toString();
    }

    // 다운로드용 URL 발급 (GET) - 10분 유효
    public String createDownloadUrl(String bucket, String key) {
        GetObjectRequest getObjectRequest = GetObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .build();

        GetObjectPresignRequest presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(10))
                .getObjectRequest(getObjectRequest)
                .build();

        PresignedGetObjectRequest presignedRequest = s3Presigner.presignGetObject(presignRequest);
        return presignedRequest.url().toString();
    }

    // 파일 삭제
    public void deleteObject(String bucket, String key) {
        DeleteObjectRequest deleteObjectRequest = DeleteObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .build();
        s3Client.deleteObject(deleteObjectRequest);
    }

    // 버킷 생성 (없으면)
    public void createBucketIfNotExists(String bucketName) {
        try {
            HeadBucketRequest headBucketRequest = HeadBucketRequest.builder()
                    .bucket(bucketName)
                    .build();
            s3Client.headBucket(headBucketRequest);
        } catch (NoSuchBucketException e) {
            CreateBucketRequest createBucketRequest = CreateBucketRequest.builder()
                    .bucket(bucketName)
                    .build();
            s3Client.createBucket(createBucketRequest);
        }
    }

    // Multipart Upload 시작 (대용량 파일 업로드)
    public CreateMultipartUploadResponse initiateMultipartUpload(String bucket, String key, String contentType) {
        CreateMultipartUploadRequest createMultipartUploadRequest = CreateMultipartUploadRequest.builder()
                .bucket(bucket)
                .key(key)
                .contentType(contentType)
                .build();
        return s3Client.createMultipartUpload(createMultipartUploadRequest);
    }

    // Multipart Upload Part 업로드용 URL 발급
    public String createMultipartUploadPartUrl(String bucket, String key, String uploadId, int partNumber) {
        UploadPartRequest uploadPartRequest = UploadPartRequest.builder()
                .bucket(bucket)
                .key(key)
                .uploadId(uploadId)
                .partNumber(partNumber)
                .build();

        UploadPartPresignRequest presignRequest = UploadPartPresignRequest.builder()
                .signatureDuration(Duration.ofMinutes(10))
                .uploadPartRequest(uploadPartRequest)
                .build();

        PresignedUploadPartRequest presignedRequest = s3Presigner.presignUploadPart(presignRequest);
        return presignedRequest.url().toString();
    }

    // Multipart Upload 완료
    public CompleteMultipartUploadResponse completeMultipartUpload(String bucket, String key, String uploadId, List<CompletedPart> completedParts) {
        CompletedMultipartUpload completedMultipartUpload = CompletedMultipartUpload.builder()
                .parts(completedParts)
                .build();

        CompleteMultipartUploadRequest completeMultipartUploadRequest = CompleteMultipartUploadRequest.builder()
                .bucket(bucket)
                .key(key)
                .uploadId(uploadId)
                .multipartUpload(completedMultipartUpload)
                .build();
        return s3Client.completeMultipartUpload(completeMultipartUploadRequest);
    }

    // Multipart Upload 중단
    public void abortMultipartUpload(String bucket, String key, String uploadId) {
        AbortMultipartUploadRequest abortMultipartUploadRequest = AbortMultipartUploadRequest.builder()
                .bucket(bucket)
                .key(key)
                .uploadId(uploadId)
                .build();
        s3Client.abortMultipartUpload(abortMultipartUploadRequest);
    }
}
```

---

## 5. 운영 시 고려사항 (Operational Tips)
1. **버킷(Bucket) 정책**: 기본적으로 프라이빗입니다. 이미지를 웹에 공개하려면 `mc` 커맨드나 콘솔에서 `Public` 정책을 설정해야 합니다.
   - 예시 (mc CLI): `mc policy set public play/mybucket`
2. **TLS/SSL**: 운영 환경에서는 반드시 HTTPS를 적용해야 합니다. Nginx를 앞단에 두거나 MinIO 자체 인증서 기능을 사용합니다.
3. **분산 모드 최소 요건**: 이레이저 코딩을 사용하려면 최소 4개의 드라이브가 필요합니다.
4. **모니터링**: Prometheus와 Grafana를 연동하여 MinIO 서버의 상태, 성능 지표 등을 모니터링하는 것이 중요합니다.
5. **백업 및 복구**: MinIO는 자체적으로 데이터 보호 기능을 제공하지만, 재해 복구를 위해 주기적인 백업 전략을 수립해야 합니다. `mc mirror` 명령어를 활용할 수 있습니다.
6. **버전 관리 (Versioning)**: 중요한 데이터의 경우, 실수로 인한 삭제나 덮어쓰기를 방지하기 위해 버킷에 버전 관리를 활성화할 수 있습니다.

# Reference
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [How Erasure Coding Works](https://min.io/product/erasure-code-protection)
- [AWS SDK for Java 2.x](https://docs.aws.amazon.com/sdk-for-java/latest/developer-guide/home.html)