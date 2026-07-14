---
id: EKS 네트워크와 접근 경계
started: 2026-06-26
tags:
  - ✅DONE
  - AWS
  - EKS
  - Network
group:
  - "[[Infra AWS]]"
---
# EKS 네트워크와 접근 경계

## 1. 개요 (Overview)

이 사례의 플랫폼은 VPC의 Public·Private Subnet, NAT Gateway, Private EKS 접근, Client VPN과 Bastion을 조합해 외부 Traffic과 운영자 접근 경로를 분리합니다.

```text
Internet User -> Public ALB -> Private EKS Pod

Operator -> Client VPN -> VPC -> Private Endpoint
         -> Bastion/SSM -> EKS API 또는 내부 Resource

Private Workload -> NAT Gateway -> External API
```

목표는 단순히 Private Subnet에 두는 것이 아니라 누가, 어떤 신원으로, 어느 경로와 Port를 통해 접근하는지 추적 가능하게 만드는 것입니다.

---

## 2. Subnet 역할과 주소 계획

Public Subnet은 Internet Gateway로 Route할 수 있고 Public Load Balancer와 NAT Gateway를 배치합니다. Private Subnet은 직접 Public IP를 갖지 않으며 EKS Node, RDS, ElastiCache 같은 내부 Resource를 둡니다.

Subnet Tag는 AWS Load Balancer Controller와 EKS가 용도를 발견하는 데 사용합니다. Tag가 잘못되면 ALB가 생성되지 않거나 의도와 다른 Subnet에 배치될 수 있습니다.

CIDR은 Node와 Pod IP, Load Balancer와 VPC Endpoint ENI, Blue-Green Preview Pod, Karpenter Burst Capacity, 향후 연결 Network까지 포함해 계산합니다. CIDR이 겹치면 Peering, Transit Gateway, Client VPN Route가 복잡해집니다.

---

## 3. Route Table과 Traffic 방향

Private Subnet의 기본 외부 경로는 NAT Gateway를 향하고 Public Subnet의 NAT Gateway는 Internet Gateway를 사용합니다. Inbound Connection은 NAT를 통해 시작할 수 없습니다.

```text
Private Pod -> Private Route Table -> NAT Gateway -> Internet Gateway
```

S3, ECR, STS, CloudWatch 같은 AWS Service는 VPC Endpoint를 사용하면 NAT 의존성과 비용을 줄일 수 있습니다. 다만 Endpoint Policy와 Private DNS가 잘못되면 광범위한 장애가 발생하므로 서비스별로 검증합니다.

Network ACL은 Subnet 수준 Stateless Filter이고 Security Group은 ENI 수준 Stateful Filter입니다. 대부분의 접근 제어는 Security Group으로 표현하고 NACL은 거친 방어선으로 유지합니다.

---

## 4. NAT Gateway 가용성과 비용

단일 NAT Gateway는 비용을 줄이지만 해당 AZ 장애와 Cross-AZ Data 비용의 영향을 받습니다. AZ별 NAT는 가용성을 높이지만 시간당 비용이 증가합니다.

선택 시 외부 API 의존 서비스의 RTO, ECR Image Pull 경로, AZ 장애 허용 범위, NAT 처리 비용, VPC Endpoint로 대체 가능한 Traffic을 봅니다.

NAT Gateway의 Port가 고갈되면 외부 API Timeout이 간헐적으로 발생합니다. `ErrorPortAllocation`, `PacketsDropCount`, Active Connection과 BytesOut을 감시합니다. 외부 호출 Workload는 Connection Pool과 Keep-alive로 Port 소비를 줄입니다.

---

## 5. EKS API Endpoint

EKS API Endpoint는 Public, Private 또는 둘 다 활성화할 수 있습니다. Private 접근은 VPC 내부 또는 연결된 Network에서만 가능해 공격 표면을 줄입니다.

운영자는 Client VPN, SSM Session Manager Bastion, VPC 내부 CI Runner 같은 승인된 경로를 사용합니다. Public Endpoint가 필요하면 허용 CIDR을 제한하고 IAM 인증, EKS Access Entry와 Kubernetes RBAC를 함께 적용합니다.

Network 접근 가능성이 Kubernetes 권한을 뜻하지는 않습니다. IAM Principal이 Cluster에 인증돼도 RBAC가 허용하지 않으면 Resource를 조작할 수 없습니다.

---

## 6. Client VPN

AWS Client VPN은 사용자 Device에서 VPC로 암호화 Tunnel을 제공합니다. Endpoint, Target Network Association, Route, Authorization Rule, 인증서 또는 Identity Provider가 함께 구성됩니다.

```text
VPN Authentication
  -> Authorization Rule
  -> Client Route
  -> Associated Subnet
  -> Security Group
  -> Target Resource
```

연결됐는데 접근할 수 없다면 이 단계를 순서대로 확인합니다. Split Tunnel은 필요한 VPC CIDR만 VPN으로 보내지만 Client의 기존 Network CIDR과 겹치면 접근이 불안정할 수 있습니다.

사용자별 인증과 접속 Log를 남기고 퇴사·권한 변경 시 즉시 회수합니다. 공유 인증서는 피합니다.

---

## 7. Bastion과 SSM

Bastion은 내부 Resource에 접근하는 중계 지점입니다. Public SSH Port를 여는 대신 SSM Session Manager를 사용하면 Inbound Port 없이 IAM으로 Session을 제어하고 Audit할 수 있습니다.

- Instance Profile은 필요한 SSM·조회 권한만 가집니다.
- EKS Access Entry와 Kubernetes RBAC를 운영 역할별로 분리합니다.
- 개인 SSH Key와 장기 AWS Credential을 저장하지 않습니다.
- Session Log와 명령 이력을 중앙 저장합니다.
- 정기 Patch와 Immutable 교체를 적용합니다.

Bastion이 단일 관리 경로라면 장애 시 복구 수단도 문서화합니다. Break-glass 권한은 평소 비활성화하고 사용 시 감사와 만료 시간을 둡니다.

---

## 8. Security Group 참조

CIDR보다 Security Group 간 참조를 사용하면 Resource IP가 바뀌어도 신뢰 관계를 유지할 수 있습니다.

```text
ALB SG -> Application SG : Service Port
Application SG -> RDS SG : PostgreSQL Port
Application SG -> Redis SG: Redis Port
Bastion SG -> Internal SG : 관리 Port
```

`0.0.0.0/0` Inbound는 Public Load Balancer의 필요한 Port 외에는 피합니다. Security Group Rule 설명에 Source와 목적을 기록하면 검토와 정리가 쉬워집니다.

---

## 9. DNS 경계

Route 53 Public Hosted Zone은 외부 Domain을, Private Hosted Zone은 VPC 내부 이름을 해석합니다. 같은 Domain의 Split-horizon DNS는 위치에 따라 다른 결과를 내므로 장애 진단이 복잡합니다.

Client VPN이 VPC Resolver를 사용하지 않으면 Private Domain을 해석하지 못할 수 있습니다. DNS Resolution, Route, Security Group을 별도로 검사합니다.

external-dns가 Record를 관리할 때 Hosted Zone과 Owner ID를 제한해 다른 환경 Record를 덮어쓰지 않게 합니다.

---

## 10. Kubernetes Network 경계

VPC Security Group만으로 Namespace 내부 East-West Traffic을 세밀하게 통제하기 어렵습니다. NetworkPolicy 또는 Service Mesh AuthorizationPolicy로 Workload 신원 기반 접근을 제한합니다.

```text
Internet Boundary : WAF / ALB / Security Group
VPC Boundary      : Subnet / Route / Security Group
Cluster Boundary  : NetworkPolicy / Istio Policy
Application       : Authentication / Authorization
```

각 계층은 서로 대체하지 않습니다. Network가 허용해도 Application 권한 검사가 필요하고, Application 인증이 있어도 불필요한 Network 경로를 열어둘 이유는 없습니다.

---

## 11. 관측성과 장애 진단

VPC Flow Logs는 허용·거부된 Flow를 보여주지만 Application Error 원인까지 설명하지는 않습니다. ALB Access Log, NAT Metric, DNS, Kubernetes Event와 함께 봅니다.

1. DNS가 기대 IP를 반환하는가
2. Route가 올바른 Gateway나 Association을 향하는가
3. Source·Target Security Group이 Port를 허용하는가
4. NACL의 왕복 Ephemeral Port가 열려 있는가
5. Load Balancer Target이 Healthy한가
6. NetworkPolicy·Mesh Policy가 허용하는가
7. Application이 연결을 수락하는가

Timeout은 경로 또는 Filter 문제인 경우가 많고 Connection Refused는 대상이 Port를 Listen하지 않는 경우가 많지만, 단정하지 말고 Packet 경로를 확인합니다.

---

## 12. 운영 점검표

- [ ] Public·Private Subnet 역할과 Tag가 명확한가
- [ ] Subnet IP가 Blue-Green과 Scale-out 여유를 포함하는가
- [ ] 단일 NAT 장애 위험과 비용을 의식적으로 선택했는가
- [ ] AWS Service Traffic에 VPC Endpoint 적용을 검토했는가
- [ ] EKS API 접근 경로와 RBAC가 분리되어 있는가
- [ ] VPN 사용자 인증·접속 Log·회수 절차가 있는가
- [ ] Bastion은 Inbound SSH 없이 SSM으로 관리되는가
- [ ] Flow Log와 NAT·ALB Metric으로 경로 장애를 진단할 수 있는가

---

## 13. 배포 사례 적용 진단과 개선 과제

현재 Networking Module은 NAT Gateway를 활성화하면서 `single_nat_gateway = true`로 구성합니다. 비용에는 유리하지만 NAT가 위치한 AZ 장애와 Cross-AZ Egress에 영향을 받으며, Private EKS 접근은 Client VPN·Bastion 가용성에도 의존합니다.

먼저 NAT Flow·Port·비용과 외부 의존 서비스의 RTO를 측정합니다. Prod SLO가 단일 NAT 장애를 허용하지 않으면 AZ별 NAT로 전환하고 S3/ECR/STS 등은 VPC Endpoint로 우회합니다. VPN·Bastion 접근은 개인 신원·만료 권한·Session Audit로 통합합니다.

완료 기준은 한 AZ와 NAT 경로를 차단한 Game Day에서 핵심 서비스가 정책대로 유지 또는 빠르게 복구되고, EKS API와 데이터 계층에 Public 우회 경로가 없으며, 운영 접근이 사용자별로 감사되는 상태입니다.

---

# Reference

- [Amazon VPC User Guide](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html)
- [AWS Client VPN](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/what-is.html)
- [EKS Cluster Endpoint Access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
- [AWS Systems Manager Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [[EKS Cluster Add-on 아키텍처]]
- [[Istio Ambient Mesh와 Kiali]]
