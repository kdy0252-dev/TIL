---
id: AWS Terraform (테라폼)
started: 2025-12-10
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# AWS Terraform (테라폼)

## 1. 개요 (Overview)
**Terraform**은 HashiCorp가 개발한 **IaC (Infrastructure as Code)** 도구 중 가장 널리 사용되는 사실상의 표준(De facto standard)입니다.
HCL (HashiCorp Configuration Language)이라는 직관적인 언어를 사용하여 AWS, Azure, GCP, Kubernetes 등 다양한 **Provider**의 리소스를 선언적으로 정의하고 관리할 수 있습니다.

"코드로 인프라를 관리한다"는 것은 인프라의 생성, 수정, 삭제 이력을 Git과 같은 버전 관리 시스템으로 추적할 수 있음을 의미하며, 이는 협업, 리뷰, 롤백을 가능하게 하는 DevOps의 핵심 실천 방법입니다.

---

## 2. 핵심 동작 원리 (Core Mechanism)

### 2.1 State File (`terraform.tfstate`)
Terraform의 심장과도 같은 존재입니다.
- **역할**: 현재 배포된 인프라의 실제 상태와 코드 상의 정의를 맵핑하는 JSON 파일입니다.
- **동작**: `plan`이나 `apply` 실행 시, Terraform은 이 상태 파일을 참조하여 어떤 리소스를 새로 만들어야 하고(Create), 어떤 리소스를 수정(Update)하거나 삭제(Delete)해야 하는지 계산합니다.
- **주의사항**: 이 파일에는 DB 패스워드나 Access Key 같은 민감 정보가 평문으로 저장될 수 있으므로 Git에 올리면 절대 안 됩니다. 보통 S3와 같은 **Remote Backend**에 암호화하여 저장합니다.

### 2.2 Lifecycle (생명주기)
1. **`terraform init`**:
    - 워킹 디렉토리를 초기화합니다.
    - `main.tf`에 정의된 Provider 플러그인(AWS 등)을 다운로드하고, State Backend를 설정합니다.
2. **`terraform plan`**:
    - **Dry Run** 단계입니다.
    - 코드를 분석하여 실제 인프라에 어떤 변경이 가해질지 "실행 계획"을 보여줍니다. (Create: +, Update: ~, Destroy: -)
    - 운영 환경에서는 이 단계의 출력을 반드시 리뷰해야 합니다.
3. **`terraform apply`**:
    - 계획된 변경 사항을 실제 클라우드 API를 호출하여 적용합니다.
    - 완료 후 `terraform.tfstate`를 갱신합니다.
4. **`terraform destroy`**:
    - 관리하던 모든 리소스를 삭제합니다. (주의 필요!)

---

## 3. 주요 구성 요소 (Components)

### 3.1 Provider
Terraform이 어떤 API와 상호작용할지 정의합니다.
```hcl
provider "aws" {
  region = "ap-northeast-2"
}
```

### 3.2 Resource
실제로 생성할 인프라 객체입니다. (EC2, S3, RDS 등)
```hcl
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t2.micro"
}
```

### 3.3 Module
관련된 리소스들을 그룹화하여 재사용 가능한 패키지로 만든 것입니다. 프로그래밍의 함수(Function)나 클래스와 비슷합니다.
예: "VPC + Subnet + Route Table + Gateway"를 묶어서 `network_module`로 정의.

### 3.4 Variable & Output
- **Variable**: 입력 파라미터. (예: `region`, `instance_type` 등을 변수화)
- **Output**: 모듈 실행 후 반환되는 값. (예: 생성된 EC2의 Public IP, RDS Endpoint)

---

## 4. Best Practices (모범 사례)

### 4.1 Remote Backend & State Locking
혼자 할 때는 로컬 파일(`local backend`)로도 충분하지만, 팀 단위 협업 시에는 반드시 **Remote Backend**를 써야 합니다.
- **S3**: State 파일을 안전하게 저장 (Versioning Enable 필수).
- **DynamoDB**: 동시에 여러 명이 `apply`를 날리지 못하도록 **State Locking**을 구현.

```hcl
terraform {
  backend "s3" {
    bucket         = "my-terraform-state-bucket"
    key            = "prod/app.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

### 4.2 디렉토리 구조 (Directory Structure)
환경(Stage)별로 격리하는 것이 중요합니다.
```text
.
├── modules/               # 재사용 가능한 모듈 정의
│   ├── vpc/
│   └── ec2/
├── environments/
│   ├── dev/               # 개발 환경
│   │   ├── main.tf
│   │   └── variables.tf
│   └── prod/              # 운영 환경
│       ├── main.tf
│       └── variables.tf
└── README.md
```

---

## 5. 예제 (Example)

### 5.1 VPC 및 EC2 생성 (Full Example)

**variables.tf**
```hcl
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  default     = "10.0.0.0/16"
}
```

**main.tf**
```hcl
# 1. VPC 생성
resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  tags = { Name = "MainVPC" }
}

# 2. Subnet 생성
resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  map_public_ip_on_launch = true
}

# 3. Security Group (방화벽)
resource "aws_security_group" "allow_ssh" {
  vpc_id = aws_vpc.main.id

  ingress { // 인바운드 규칙
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress { // 아웃바운드 규칙 (전체 허용)
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# 4. EC2 Instance
resource "aws_instance" "web" {
  ami             = "ami-0abcdef1234567890" # Amazon Linux 2
  instance_type   = "t2.micro"
  subnet_id       = aws_subnet.public.id
  security_groups = [aws_security_group.allow_ssh.id]

  # User Data (부팅 시 실행 스크립트)
  user_data = <<-EOF
              #!/bin/bash
              yum update -y
              yum install -y httpd
              systemctl start httpd
              systemctl enable httpd
              echo "Hello Terraform" > /var/www/html/index.html
              EOF

  tags = { Name = "Terraform-Web" }
}
```

**outputs.tf**
```hcl
output "web_public_ip" {
  value = aws_instance.web.public_ip
  description = "The public IP of the web server"
}
```

---

## 6. 운영 시 주의사항 (Operational Tips)

1. **`resource` 이름 변경 주의**:
    - 테라폼 코드 상의 리소스 이름(`aws_instance.web` -> `aws_instance.server`)을 바꾸면, 테라폼은 기존 `web`을 **삭제(Destroy)** 하고 `server`를 **새로 생성(Create)** 하려고 합니다.
    - 이를 막으려면 `terraform state mv` 명령어로 State 파일 내부의 이름을 수동으로 변경해줘야 합니다.
2. **Drift 감지**:
    - 누군가 콘솔(AWS Console)에서 수동으로 Security Group을 열어버렸다면?
    - `terraform plan`을 돌리면 "코드와 실제 상태가 다름"을 감지하고, 다시 코드로 되돌리려고(원상복구) 할 것입니다. 이를 통해 인프라의 일관성을 유지할 수 있습니다.
3. **Sensitive Data**:
    - `output` 값에 DB 비밀번호 등이 포함되면 로그에 찍힙니다. `sensitive = true` 옵션을 사용하세요.

# Reference
- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
- [AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Best Practices](https://www.terraform-best-practices.com/)