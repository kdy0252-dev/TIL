---
id: VPC Endpoint와 PrivateLink
started: 2026-06-28
tags:
  - ✅DONE
  - AWS
  - Network
  - PrivateLink
group:
  - "[[Infra AWS]]"
---
# VPC Endpoint와 PrivateLink

## 1. Private Subnet도 외부 경로에 의존한다

Private EKS Node가 ECR에서 Image를 받고 S3, STS, CloudWatch API를 호출할 때 기본 경로가 NAT Gateway라면 NAT 장애와 비용이 내부 운영에 영향을 준다. VPC Endpoint는 AWS Service 또는 Endpoint Service에 사설 경로로 접근하게 한다.

## 2. Gateway와 Interface Endpoint

| 유형 | 대표 서비스 | 연결 방식 | 비용 특성 |
|---|---|---|---|
| Gateway | S3, DynamoDB | Route Table 대상 | Endpoint 시간 비용 없음 |
| Interface | ECR, STS, Logs 등 | Subnet의 ENI와 Private IP | 시간·처리량 비용 |

Interface Endpoint는 Availability Zone마다 ENI를 두고 Security Group으로 접근을 제한한다. 단일 Subnet만 연결하면 다른 AZ에서 Cross-AZ 경로와 장애 의존성이 생길 수 있다.

## 3. Private DNS

Private DNS를 켜면 일반 AWS Service Domain이 VPC 안에서 Endpoint의 Private IP로 해석된다. Application 설정을 바꾸지 않아도 되지만 DNS Resolution과 Hosted Zone 충돌이 있으면 광범위한 연결 장애가 난다.

```text
service.region.amazonaws.com
  -> VPC Resolver
  -> Interface Endpoint ENI
```

On-premise나 Client VPN에서 같은 이름을 쓸 때 Route 53 Resolver Endpoint와 Forwarding Rule도 고려한다.

## 4. ECR Image Pull에 필요한 경로

ECR Image Pull은 ECR API Endpoint 하나만으로 끝나지 않는다. ECR API, ECR Docker Registry와 Image Layer가 저장된 S3 경로가 함께 필요하다. CloudWatch Log, STS, SSM을 사용하는 Node라면 해당 Endpoint도 검토한다.

Endpoint를 만들었다고 NAT를 바로 제거하지 않는다. 실제 DNS와 Flow Log를 통해 모든 필요한 외부 목적지를 확인한다.

## 5. Endpoint Policy

Endpoint Policy는 해당 경로를 통해 호출할 수 있는 Principal, Action과 Resource를 제한한다. IAM Policy를 대체하지 않고 추가 경계를 만든다.

예를 들어 S3 Endpoint에서 승인된 Bucket만 허용하면 잘못된 Credential이 같은 경로로 임의 Bucket에 Data를 전송하는 위험을 줄일 수 있다. 다만 AWS 관리 동작에 필요한 Bucket을 빠뜨리면 Image Pull이나 Add-on이 실패할 수 있다.

## 6. PrivateLink 서비스 제공

자체 서비스를 Network Load Balancer 뒤 Endpoint Service로 제공하면 VPC Peering 없이 Consumer VPC에 사설 Interface Endpoint를 제공할 수 있다. CIDR 중첩 문제를 줄이고 서비스 단위로 연결하지만 L7 Routing과 Transitive Network를 제공하는 것은 아니다.

## 7. 비용과 가용성

Endpoint가 항상 NAT보다 싸지는 않다. AZ 수와 Endpoint 수가 많으면 Interface Endpoint 고정 비용이 커진다. Traffic이 많은 AWS Service, 장애 시 반드시 필요한 Control Plane 경로, NAT 비용의 큰 비중부터 적용한다.

## 8. Endpoint가 있는데도 NAT로 나가는 이유

가장 먼저 DNS를 확인한다. Private DNS가 꺼져 있거나 VPC DNS 설정이 비활성화되어 있으면 SDK는 Public Endpoint를 해석한다. ECR은 API, Docker Registry와 S3라는 여러 경로를 사용하므로 일부 Endpoint만 만들었을 때 Layer Download가 계속 NAT를 지날 수 있다.

Route Table 연결이 빠진 Gateway Endpoint, 다른 AZ에만 있는 Interface Endpoint, Security Group의 443 Inbound 누락도 흔하다. Flow Log, DNS 조회와 NAT Metric을 함께 보면 “Resource가 존재한다”와 “실제 Traffic이 사용한다”를 구분할 수 있다.

## 9. 비용을 비교하는 방법

Interface Endpoint 비용은 Endpoint 수와 AZ 수에 비례하고 NAT는 Gateway 시간 비용과 처리량 비용, Cross-AZ 전송 비용이 붙는다. 따라서 Endpoint를 많이 만드는 것이 언제나 절약은 아니다.

Boot와 배포에 반드시 필요한 ECR·S3·STS 같은 경로는 비용뿐 아니라 NAT 장애 격리 가치가 크다. Traffic이 거의 없는 서비스는 고정 Endpoint 비용이 더 클 수 있다. 서비스별 Byte, 호출 중요도와 AZ 경로를 기준으로 판단한다.

## 10. 실무에서 빠지기 쉬운 설계

Network Module에 Endpoint가 있어도 서비스 선택 근거, Endpoint Policy와 Private DNS 동작이 설명되지 않으면 운영자가 NAT를 제거하거나 장애를 진단하기 어렵다. 특히 Wide-open Endpoint Policy는 사설 경로를 만들었을 뿐 Data Exfiltration 경계를 강화하지 못한다.

NAT Flow에서 AWS Service Traffic을 분류하고 Boot에 필수인 경로부터 Endpoint로 옮긴다. 이후 실제 Image Pull과 Log 전송을 NAT 차단 상태에서 검증하고, 업무에 필요한 ARN만 Endpoint Policy로 제한한다.

## 11. 기억할 점

VPC Endpoint의 목적은 “Internet을 거치지 않는다”보다 구체적이다. AWS API 경로를 VPC 안으로 가져와 NAT 장애와 비용을 줄이고, Endpoint Policy라는 추가 권한 경계를 만드는 것이다. DNS, Route, Security Group과 Policy가 함께 맞아야 이 효과가 생긴다.

# Reference
- [AWS PrivateLink concepts](https://docs.aws.amazon.com/vpc/latest/privatelink/concepts.html)
- [Gateway endpoints](https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html)
- [Amazon ECR VPC endpoints](https://docs.aws.amazon.com/AmazonECR/latest/userguide/vpc-endpoints.html)
