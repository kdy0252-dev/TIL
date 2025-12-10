---
id: OpenSSL
started: 2025-02-28
tags:
  - ✅DONE
  - OpenSSL
group: "[[Linux]]"
---
# OpenSSL
## Key 생성
```shell title="Gen Key using Open SSL"
# RSA (2048비트) 생성
openssl genrsa -out test.key 2048

# 1. DSA 파라미터 생성 (2048비트)
openssl dsaparam -out dsaparam.pem 2048

# 2. 파라미터를 이용하여 DSA 개인 키 생성
openssl gendsa -out test_dsa.key dsaparam.pem

# prime256v1 (NIST P-256) 커브를 사용한 예시
openssl ecparam -name prime256v1 -genkey -noout -out test_ec.key

# secp256k1 커브 사용 예시
openssl ecparam -name secp256k1 -genkey -noout -out test_ec.key

# Ed25519 키 생성
openssl genpkey -algorithm ed25519 -out test_ed.key
```

## Key에 Password 생성
```shell title="password 옵션"
# -aes256 옵션을 주면 된다.
openssl genrsa -aes256 -out test.key 2048

# 아래와 같이 Password를 제거 할 수 있다.
openssl rsa -in 키파일 -out 키파일
```


## Extract Public Key
```shell title="Private Key에서 Public Key 추출"
openssl rsa -in 개인키 -pubout -out 공개키
```

## CSR 생성
```shell title="CSR 생성 스크립트"
openssl req -new -key <사용할 key 파일명> -out <생성할 csr 파일명>
```

## Cert 생성
```shell title="인증서 생성"
openssl x509 -req -days <유효기간> -in <csr파일> -signkey <key파일> -out <crt파일명>
```

## 인증서 확인
```
openssl openssl x509 -in <cert file 경로> -text -noout
```

# Reference