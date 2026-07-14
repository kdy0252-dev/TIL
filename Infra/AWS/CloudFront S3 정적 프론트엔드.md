---
id: CloudFront S3 정적 프론트엔드
started: 2026-06-22
tags:
  - ✅DONE
  - AWS
  - CloudFront
  - S3
group:
  - "[[Infra AWS]]"
---
# CloudFront S3 정적 프론트엔드

## 1. 개요 (Overview)

정적 프론트엔드는 Build Artifact를 S3에 저장하고 CloudFront가 전 세계 Edge에서 HTTPS로 제공합니다. 이 배포 사례은 Private S3 Bucket, CloudFront Origin Access Control(OAC), ACM Certificate, Route 53을 조합하고 SPA Route를 처리합니다.

```text
Browser
  -> Route 53
  -> CloudFront + ACM
  -> OAC 서명 요청
  -> Private S3 Bucket
```

S3 Website Endpoint를 공개하는 방식과 달리 Bucket은 Public Access를 차단하고 CloudFront Distribution만 Object를 읽도록 제한합니다.

---

## 2. Origin Access Control

OAC는 CloudFront가 SigV4로 S3 요청에 서명하게 합니다. Bucket Policy는 특정 Distribution ARN에서 온 요청만 허용합니다.

```text
Principal = cloudfront.amazonaws.com
Action    = s3:GetObject
Condition = AWS:SourceArn == Distribution ARN
```

CloudFront URL을 안다고 해서 S3에 직접 접근할 수 있는 것은 아닙니다. S3 Block Public Access를 모두 활성화하고 ACL 대신 Bucket Policy와 Object Ownership을 사용합니다.

기존 Origin Access Identity(OAI)보다 OAC가 최신 방식이며, SSE-KMS Object나 동적 요청 Method 지원 범위도 더 넓습니다. KMS를 사용한다면 Key Policy에도 CloudFront 권한이 필요합니다.

---

## 3. SPA Routing

React, Vue 같은 Single Page Application은 `/orders/123`을 브라우저에서 직접 열어도 `index.html`을 반환한 뒤 Client Router가 화면을 결정해야 합니다. S3에는 해당 Key가 없으므로 403 또는 404가 발생합니다.

CloudFront Custom Error Response로 403·404를 `/index.html`과 200으로 바꿀 수 있습니다.

하지만 모든 404를 200으로 바꾸면 존재하지 않는 JS, CSS, Image 요청도 HTML을 받아 원인 파악이 어려워집니다. 선택지는 다음과 같습니다.

- Default Behavior만 SPA Fallback 적용
- CloudFront Function에서 확장자가 없는 경로만 `index.html`로 Rewrite
- 정적 Asset Behavior를 별도 분리하고 Fallback 제외

SEO와 HTTP 의미가 중요한 서비스라면 무조건 200으로 바꾸는 정책을 재검토합니다.

---

## 4. Cache Key 설계

CloudFront Cache Key는 URL Path, 선택한 Query String, Header, Cookie로 구성됩니다. 정적 파일은 가능한 단순한 Key를 사용합니다.

```text
/assets/app.a1b2c3.js  -> 장기 Cache, Immutable
/index.html            -> 짧은 Cache 또는 No-cache
```

Content Hash가 파일명에 포함된 Asset은 변경할 때 새 URL이 되므로 긴 TTL을 안전하게 사용할 수 있습니다. 반면 `index.html`을 오래 Cache하면 새 배포 후에도 이전 Asset을 참조할 수 있습니다.

모든 Query String과 Cookie를 Origin에 전달하면 Cache Hit Ratio가 급격히 낮아집니다. Origin Request Policy와 Cache Policy를 목적별로 분리합니다.

---

## 5. 배포와 Cache Invalidation

권장 순서는 다음과 같습니다.

1. Hash가 붙은 새 Asset을 먼저 Upload합니다.
2. 모든 Asset Upload가 성공한 뒤 새 `index.html`을 Upload합니다.
3. 필요한 경우 `index.html`만 Invalidation합니다.
4. Smoke Test 후 이전 Asset의 보존 정책을 적용합니다.

`/*` 전체 Invalidation은 단순하지만 비용과 Cache Miss를 증가시킵니다. Hash Asset 전략을 사용하면 대부분의 배포는 Entry Document만 무효화하면 됩니다.

Asset보다 `index.html`을 먼저 배포하면 아직 존재하지 않는 파일을 참조하는 짧은 장애가 생깁니다.

---

## 6. 원자적 Release와 Rollback

S3 Prefix를 Release별로 분리하면 Rollback 기준이 명확해집니다.

```text
releases/<commit-sha>/index.html
releases/<commit-sha>/assets/...
```

Distribution Origin Path 또는 Release Manifest를 바꾸어 전환할 수 있습니다. 단순 Root 덮어쓰기보다 구현은 복잡하지만 Artifact 보존과 재현성이 좋아집니다.

Rollback은 이전 Source를 다시 Build하는 것이 아니라 검증된 이전 Artifact를 재승격해야 합니다. Build Tool과 Dependency가 달라지면 같은 Commit도 다른 결과를 만들 수 있기 때문입니다.

---

## 7. TLS, Domain과 DNS

CloudFront Custom Domain Certificate는 `us-east-1`의 ACM에 있어야 합니다. Route 53 Alias Record는 Distribution을 가리킵니다.

Certificate 발급과 DNS Validation은 다음 의존 관계를 가집니다.

```text
Hosted Zone
  -> ACM Validation Record
  -> Certificate Issued
  -> CloudFront Alias 연결
  -> Route 53 Alias Record
```

Certificate 갱신 실패, Domain Ownership 변경, CAA Record 제한을 감시합니다. TLS Policy는 구형 Protocol 지원과 보안 요구의 균형을 정하되 가능하면 최신 최소 Version을 사용합니다.

---

## 8. Security Header와 브라우저 보안

CloudFront Response Headers Policy로 다음 Header를 적용할 수 있습니다.

- Strict-Transport-Security
- Content-Security-Policy
- X-Content-Type-Options
- Referrer-Policy
- Frame Ancestors 또는 X-Frame-Options

CSP는 실제 API, Image, Font, Script Origin을 Allowlist해야 합니다. 처음부터 강제하면 서비스가 깨질 수 있으므로 Report-Only로 위반을 관찰한 뒤 적용합니다.

Frontend Bundle에 API Secret을 넣을 수는 없습니다. Browser에 전달되는 모든 값은 공개 정보로 간주합니다. 환경별 API Base URL은 Configuration이지만 Credential은 아닙니다.

---

## 9. CORS와 API 연결

Frontend Domain과 API Domain이 다르면 API Gateway·ALB·Backend에서 CORS를 처리합니다. S3 CORS 설정은 Browser가 S3 Origin에 직접 접근할 때만 관련됩니다.

허용 Origin을 `*`로 두면서 Credential을 허용할 수 없습니다. 환경별 정확한 Origin, Method, Header를 정의하고 Preflight Cache 시간을 설정합니다.

CloudFront가 API까지 Reverse Proxy한다면 Path Behavior별 Origin, Cache, Header Forwarding을 분리해야 합니다. 인증 응답을 공유 Cache에 저장하지 않도록 주의합니다.

---

## 10. Logging과 관측성

CloudFront Standard Log 또는 Real-time Log로 요청 상태, Edge Location, Cache Result를 분석할 수 있습니다. 다음 지표가 중요합니다.

- 4xx·5xx Error Rate
- Cache Hit Ratio
- Origin Latency
- Data Transfer
- Invalidation 수
- 특정 Release 이후 Asset 404

S3 Access Log만으로는 Edge Cache Hit 요청을 볼 수 없습니다. CloudFront와 Origin 관측 범위를 구분합니다.

개인정보가 포함된 Query String이나 Cookie를 Log에 남기지 않도록 Cache·Log 정책을 함께 설계합니다. Log Bucket의 Retention과 접근 권한도 비용·보안 대상입니다.

---

## 11. 비용과 성능

비용은 Data Transfer, Request, Invalidation, Origin Fetch, Log 저장에서 발생합니다. 압축과 Cache는 성능뿐 아니라 비용에도 영향을 줍니다.

- Brotli·Gzip 압축 활성화
- Image Format과 크기 최적화
- Hash Asset의 긴 TTL
- 불필요한 Cookie·Header 전달 제거
- Price Class와 지리적 사용 범위 검토

Cache Hit Ratio만 높이는 것이 목적은 아닙니다. `index.html`처럼 신선도가 중요한 Object는 의도적으로 짧은 TTL이 맞습니다.

---

## 12. 장애 양상과 검증

| 증상 | 확인 지점 |
|---|---|
| S3 직접 접근은 차단됐지만 CloudFront도 403 | OAC, Bucket Policy, KMS Policy |
| 새 배포 후 Chunk 404 | Upload 순서, 오래된 index Cache, Asset 정리 |
| 새 버전이 보이지 않음 | Cache-Control, Invalidation, Browser Cache |
| 모든 잘못된 Asset이 HTML 반환 | SPA Error Response 범위 |
| Custom Domain TLS 오류 | ACM Region, Certificate 상태, Alias |

### 배포 점검표

- [ ] Bucket Public Access가 완전히 차단되어 있는가
- [ ] OAC가 특정 Distribution으로 제한되는가
- [ ] Hash Asset과 `index.html`의 Cache 정책이 다른가
- [ ] Asset 선배포 후 Entry Document를 교체하는가
- [ ] SPA Fallback이 실제 정적 파일 오류를 숨기지 않는가
- [ ] Security Header와 CORS를 자동 Test하는가
- [ ] 이전 Release Artifact로 Rollback할 수 있는가
- [ ] CloudFront 오류율과 Asset 404를 감시하는가

---

## 13. 배포 사례 적용 진단과 개선 과제

Private S3와 CloudFront OAC 기반은 적절하지만 SPA의 403/404 전체 Fallback은 누락된 JS Chunk도 HTML 200으로 감출 수 있습니다. Cache Policy와 배포 순서가 자동 검증되지 않으면 새 `index.html`이 아직 없는 Asset을 참조할 수 있습니다.

확장자가 없는 Navigation Path만 `index.html`로 Rewrite하고 Asset 404는 그대로 유지합니다. Hash Asset 선배포, Entry Document 후배포, 최소 Invalidation을 Pipeline에 고정하며 Security Header와 Access Log를 활성화합니다.

완료 기준은 S3 직접 접근이 차단되고, 존재하지 않는 Asset은 404, SPA Route는 정상 200이며, 이전 Release Artifact로 즉시 Rollback하고 Asset 404 Alert를 받을 수 있는 상태입니다.

---

# Reference

- [Restricting Access to an Amazon S3 Origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html)
- [CloudFront Cache Behavior](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html)
- [ACM Certificates for CloudFront](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cnames-and-https-requirements.html)
- [Route 53 Alias to CloudFront](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-cloudfront-distribution.html)
- [[Terraform Multi-Stack과 Remote State]]
