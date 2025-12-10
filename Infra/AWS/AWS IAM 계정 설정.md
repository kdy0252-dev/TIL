---
id: AWS IAM 계정 설정
started: 2025-04-29
tags:
  - ✅DONE
  - "#AWS"
---
# AWS IAM 계정 설정

## 계정 설정

### 1. IAM 서비스로 이동한다.
![[Pasted image 20250429072224.png]]
다음과 같은 화면이 뜨면
왼쪽 탭에서 사용자를 클릭한다.

### 2. 사용자 탭으로 이동
![[Pasted image 20250429072335.png]]
사용자 테이블에서 자신의 계정을 찾아 클릭한다.

### 3. 보안 자격 증명탭을 클릭한다.
![[Pasted image 20250429072432.png]]

### 4. MFA 디바이스 할당 버튼을 클릭한다
![[Pasted image 20250429072521.png]]

### 5. 아래와 같이 MFA를 생성해준다.
![[Pasted image 20250429072557.png]]
디바이스의 이름을 입력하고 인증 관리자 앱을 선택해준다.

### 6. MFA 디바이스(스마트폰)에서 Google Authenticator을 설치하고 앱에서 QR코드를 인식시킨다.
![[Pasted image 20250429072651.png]]
그러면 Google Authenticator에 OTP가 뜨는데 하단의 MFA 코드 1에 입력하고 30초가 지난 후 OTP 번호가 바뀌면 MFA 코드 2에 입력한다.

### 7. AWS CLI를 설치한다. (설치 되어있으면 생략)
```shell title="aws-cli 설치"
brew install awscli
aws --version
```

### 8. Terminal에서 aws-mfa를 설치한다. (설치 되어있으면 생략)
맥에서는 pip로 전역 모듈을 설치할 수 없으므로 아래와 같은 절차를 따라 설치한다.
```shell title="aws-mfa 설치"
brew install pipx

pipx ensurepath
exec $SHELL

pipx install aws-mfa
```

### 9. 액세스 키를 발급한다.
![[Pasted image 20250429074411.png]]
MFA를 만들던 화면 아래에 있는 액세스 키 만들기 버튼을 클릭한다.

![[Pasted image 20250429074558.png]]
위와 같이 입력하고 다음을 누르고 나온 키와 Key ID를 복사한다. 두번 다시 보지 못하므로 잘 보관한다.

### 10. aws configure 생성한다.
```shell title="aws configure를 생성한다."
aws configure
AWS Access Key ID [None] : {발급받은 IAM의 Access Key ID}
AWS Secret Access Key [None] : {발급받은 IAM의 Secret Access Key}
Default region name [None] : {리전}
Default output format [None] :
```

### 11. ~/.aws 경로의 credentials 파일에 아래 정보를 추가해준다.
![[Pasted image 20250429074705.png]]
```
[default-long-term]
aws_access_key_id = {발급받은 IAM의 Access Key ID}
aws_secret_access_key = {발급받은 IAM의 Secret Access Key}
aws_mfa_device = 위에서 생성한 MFA 주소
```

### 12. 액세스 키가 잘 설정되었는지 확인해준다.
```shell title="S3 목록을 출력해본다."
aws s3 ls
```

### 13.  CLI에서 쿠버네티스를 설치한다.(아래에 brew로 까는거 추천)
```shell title="mac os에서 쿠버네티스 설치"
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io//stable.txt)/bin/darwin/arm64/kubectl"

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/darwin/arm64/kubectl.sha256"

echo "$(cat kubectl.sha256) kubectl" | shasum -a 256 --check

chmod +x ./kubectl

sudo mv ./kubectl /usr/local/bin/kubectl
sudo chown root: /usr/local/bin/kubectl

kubectl version --client

# 또는
brew install kubectl
# 또는
brew install kubernetes-cli
```

### 14. kubectl에 EKS 컨텍스트 설정
```shell title="kubectl context 설정"
aws eks update-kubeconfig --name <클러스터 이름> --region <리전>

kubectl config use-context <EKS 클러스터 주소>

aws sts get-caller-identity --output table`
```

### 15. 만약 다 했는데 안된다면 클러스터 ConfigMap에 등록되지 않아서 그렇다. (관리자에게 문의)
![[Pasted image 20250429090157.png]]
클러스터를 생성한 사람이 `system:masters` 권한을 가지고 있고 `system:masters`권한이 있는 사람이 유저를 ConfigMap에 등록해주어야 한다.

아래는 ConfigMap에 등록하는 예시 명령어이다.
```shell title="ConfigMap에 system:masters 권한 추가"
eksctl create iamidentitymapping \
--cluster prod-cluster \
--region ap-northeast-2 \
--arn arn:aws:iam::297752572146:user/dykim@autocrypt.io \
--username dykim@autocrypt.io \
--group system:masters
```

# Reference
[MAC에서 쿠버네티스 설치](https://kubernetes.io/ko/docs/tasks/tools/install-kubectl-macos/)