---
id: AWS Terraform 사용법
started: 2025-12-29
tags:
  - ✅DONE
  - Infra
  - AWS
  - Terraform
  - IaC
  - VPN
group:
  - "[[Infra]]"
---
# AWS Terraform 기반 인프라 배포 및 운영 가이드 (Standard SOP)

## 0. 개요 (Executive Summary)

본 문서는 Terraform을 활용하여 AWS 인프라를 프로비저닝하고 운영하기 위한 표준 운영 절차(SOP)를 기술한다. AWS 리소스 생성뿐만 아니라, 보안 연결(Client VPN) 및 인증서(ACM) 연동 등 실제 운영 환경에서 필수적인 설정 단계를 포함하여 엔지니어가 일관된 방식으로 인프라를 관리할 수 있도록 돕는 것을 목적으로 한다.

---

## Ⅰ. 환경 준비 및 변수 설정 (Pre-requisites)

Terraform 실행 전, AWS 인증 정보 및 리소스 식별을 위한 환경변수 설정이 선행되어야 한다.

### 1. 보안 자격 증명 및 키 페어 구성
- **EC2 Key Pair**: 
  - 생성된 `.pem` 키는 반드시 `~/.ssh` 경로에 보관하며, 권한을 `400`으로 제한하여 보안성을 확보해야 한다.
  - 변수명: `TF_VAR_ec2_key_pair_key_name`
- **IAM Access Keys**: 
  - 최소 권한 원칙(Least Privilege)에 따라 필요한 서비스 권한만 부여된 IAM 사용자의 키를 사용한다.
  - 변수명: `TF_VAR_iam_user_access_key_id`, `TF_VAR_iam_user_secret_access_key`

### 2. 환경변수 주입 스크립트 (`export-env.sh`)
- Terraform은 `TF_VAR_` 접두사가 붙은 환경변수를 자동으로 변수로 인식한다.
- **실행 방법**:
  ```bash
  source ./export-env.sh
  ```
  > [!IMPORTANT]
  > 스크립트 실행 시 `.` 또는 `source` 명령어를 사용하여 현재 셸 세션에 변수를 상속시켜야 한다.

---

## Ⅱ. 초기 인프라 프로비저닝 (Stage 1)

### 1. Terraform 초기화 및 글로벌 모듈 배포
- **Backend 초기화**: 
  ```bash
  terraform init
  ```
- **Global 리소스 전역 적용**:
  VPC, Subnet, IAM 등 공통 기반 시설을 먼저 배포한다. 특정 모듈만 우선 배포하기 위해 `-target` 옵션을 활용한다.
  ```bash
  terraform apply -auto-approve -target=module.global
  ```

---

## Ⅲ. Client VPN 및 보안 연결 구성 (Stage 2)

내부망 리소스(Private Subnet)에 접근하기 위해 AWS Client VPN 설정을 완료해야 한다.

### 1. ACM 인증서 Export 및 복호화
- AWS Certificate Manager(ACM)에서 배포된 인증서를 Export하여 로컬에서 사용할 수 있도록 준비한다.
- **키 복호화 절차**:
  1. 인증서 본문과 암호화된 키를 다운로드한다.
  2. OpenSSL을 사용하여 키 파일을 복호화한다.
  ```bash
  # 키 파일 확장자를 .pem으로 변경 후 실행
  openssl pkey -in encrypted_key.pem -out decrypted_key.pem
  ```

### 2. VPN 클라이언트 프로파일 구성 (`.ovpn`)
- 다운로드한 `.ovpn` 파일 내부에 `<cert>`와 `<key>` 태그를 추가하여 인증 정보를 직접 삽입한다.
- **포맷 예시**:
  ```xml
  <cert>
  -----BEGIN CERTIFICATE-----
  ... [인증서 데이터] ...
  -----END CERTIFICATE-----
  </cert>
  <key>
  -----BEGIN PRIVATE KEY-----
  ... [복호화된 키 데이터] ...
  -----END PRIVATE KEY-----
  </key>
  ```

---

## Ⅳ. 전체 인프라 완성 및 서비스 확인 (Stage 3)

보안 연결(VPN)이 확보된 상태에서 실제 서비스 리소스(EKS, RDS 등)를 배포한다.

### 1. 최종 배포 수행
```bash
# VPN 연결 상태를 반드시 확인 후 실행
terraform apply -auto-approve
```

### 2. Internal DNS Resolution 설정 (`/etc/resolver/`)
- AWS 내부 도메인(`.autocrypt.io` 등)을 로컬에서 해석하기 위해 Resolver 설정을 추가한다.
- **경로**: `/etc/resolver/[도메인명]`
- 이 설정이 누락될 경우 VPN 연결 상태에서도 내부 도메인 기반 서비스(ArgoCD, Grafana) 접근이 불가능할 수 있다.

---

## Ⅴ. 리소스 클린업 및 관리 (Maintenance)

### 1. 리소스 전체 삭제
운영 환경이 아닌 개발/테스트 환경의 경우, 비용 절감을 위해 사용하지 않는 리소스는 전량 삭제한다.
```bash
terraform destroy -auto-approve
```

### 2. State 관리 주의사항
- `terraform.tfstate` 파일은 리소스의 현재 상태를 기록하는 유일한 지표이므로, 반드시 원격 백엔드(S3 등)를 사용하여 관리하고 로컬 파일의 유실/오염에 주의한다.

# Reference
- **Official Docs**: [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- **Best Practice**: [AWS Client VPN Authentication and Authorization](https://docs.aws.amazon.com/vpn/latest/clientvpn-admin/client-authentication.html)
- **Technical Standard**: [Terraform State Management Guide](https://developer.hashicorp.com/terraform/language/state)