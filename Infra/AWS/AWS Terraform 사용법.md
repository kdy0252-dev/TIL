---
id: AWS Terraform 사용법
started: 2025-12-29
tags:
  - ⏳DOING
group: []
---
# AWS Terraform 사용법
## Terraform 사용법
### 1. export-env.sh 스크립트 실행
1. 값 세팅
 2. TF_VAR_ec2_key_pair_key_name (한번 생성하고나서는 키 저장 후 기록해두었다가 쓰시면 됩니다.)
  3. AWS 의 **EC2** 에 들어가기
  4. 좌측 메뉴에서 **네트워크 및 보안** -> **키 페어**  들어가기
  5. 키 페어 생성하러 들어가기
  6. 생성된 키는 **~/.ssh** 폴더 안에 다운로드하기
  7. **키 페어 이름** 입력하기 -> 이 값을 저 변수에 입력해줘야 함 (내꺼는 gsnam_key)
 8. TF_VAR_iam_user_access_key_id (한번 생성하고나서는 기록해두었다가 쓰시면 됩니다.)
 9. TF_VAR_iam_user_secret_access_key (한번 생성하고나서는 기록해두었다가 쓰시면 됩니다.)
  10. AWS 의 **IAM** 에 들어가기
  11. 좌측 메뉴에서 **액세스 관리** -> **사용자** 들어가기
  12. **내꺼 계정** 들어가기
  13. **보안 자격 증명** 들어가기
  14. 액세스 키 없으면 만들기
  15. TF_VAR_iam_user_access_key_id : **액세스 키**
  16. TF_VAR_iam_user_secret_access_key : **비밀키**
 17. TF_VAR_db_password (RDS 안하면 굳이 안해도 됩니다.)
  18. **RDS 의 비밀번호** 입니다.
19.  스크립트 실행 (sudo 로 비밀번호 필요)
``` shell
. ./export-env.sh
```

###  2. 첫번째 테라폼 명령어 실행 (*1번 수행 후 진행하시오!*)
#### 처음 할 때는 테라폼 초기화 명령어가 필요할 수 있습니다.
``` shell
terraform init
```
#### 전역 모듈을 적용합니다.
``` shell
terraform apply -auto-approve -target=module.global
```


### 3. AWS 의 vpn 클라이언트 실행 (*2번이 완전히 끝난 다음 진행하시오!*)
1. AWS 의 **VPC** 에 들어가기
2. 좌측 메뉴에서 **가상 사설 네트워크(VPN)** -> **Client VPN 엔드포인트** 들어가기
3. 클라이언트가 없다면? (있으면 이 단계 패스)
 4. **Client downloads** 로 클라이언트 다운받기
5. 생성된 클라이언트 VPN **선택**하고 **클라이언트 구성 다운로드** 하기
6. AWS 의 **Certificate Manager** 에 들어가기
7. 좌측 메뉴에서 **인증서 나열** 들어가기
8. 생성된 도메인의 **인증서 ID** 클릭하여 들어가기
9. **export** 하기
 10. passpharse 에 복호화 시 사용할 값 입력 (나는 gsnam)
  11. 키가 기본적으로 암호화 됩니다. 복호화 할 때 이 값이 사용됩니다.
 12. **cert body** 와 **key** 를 다운로드 하기
 13. 터미널에서 해당 파일들의 디렉터리로 이동
 14. 키 파일의 확장자 변경하기 (txt -> **pem**) -> *주의!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!*
 15. 명령어 입력하여 키 복호화 하기
``` shell
openssl pkey -in {다운받은 파일명} -out {복호화하여 생성되는 파일명}
```
9. **클라이언트 구성** 파일 안에 인증서와 키 세팅하기
 10. vi 로 클라이언트 구성파일 열기
 11. 인증서 안에 데이터 복사 후 cert 태그 생성해서 안에 인증서 데이터 넣기 ( \<cert>{인증서 파일 데이터}\</cert> )
 12. 복호화한 키 안에 데이터 복사 후 key 태그 생성해서 안에 키 데이터 넣기 ( \<key> {키 파일 데이터} \</key> )
 13. 저장
14. VPN 클라이언트 실행
15. command + s 로 프로파일 관리 창 열기
16. 클라이언트 구성 파일 선택해서 프로파일 등록하기
17. vpn 연결하기

### 4. 두번째 테라폼 명령어 실행 (3번으로 vpn 연결해야 가능합니다!)
``` shell
terraform apply -auto-approve
```

### 5. 생성된 것들 확인하기
1. AWS 리소스 확인
 2. AWS 의 EC2 에 들어가기
 3. 좌측 메뉴에서 로드 밸런싱 -> 로드밸런서 들어가기
 4. 생성된 것들 확인 (현재는 argocd, grafana)
5. 서비스 확인
 6. 브라우져 열어서 접근해보기 (현재는 argocd, grafana)
  7. eu 의 prod 라면?
   8. argocd : http://argocd.eu-prod.autocrypt.io
  9. imom 의 qa 라면?
   10. grafana : http://grafana.imom-qa.autocrypt.io


### 6. 테라폼 명령어로 삭제하기
1. 이 명령어 하나로 모든 리소스가 제거됩니다.
``` shell
terraform destroy -auto-approve
```

### 7. 도메인 지정 정보 제거하기
1. /etc/resolver/ 안에 정보 제거하기

# Reference