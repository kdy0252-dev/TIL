---
id: OpenSSL
started: 2025-02-28
tags:
  - ✅DONE
  - OpenSSL
group: "[[Linux]]"
---
# OpenSSL로 Key, CSR과 인증서 다루기

TLS 설정에서 자주 혼동하는 세 파일의 역할부터 구분한다.

- **Private Key**는 소유자만 보관하며 서명과 Key Agreement에 사용한다.
- **Public Key**는 공개할 수 있고 Private Key로 만든 서명을 검증한다.
- **Certificate**는 Public Key와 Domain·주체 정보를 CA가 서명한 문서다.
- **CSR**은 CA에 Certificate 발급을 요청하기 위해 Public Key와 주체 정보를 담아 서명한 요청서다.

## Private Key 생성

OpenSSL 3 계열에서는 여러 Algorithm을 일관되게 다루는 `genpkey`를 사용할 수 있다.

```shell
# RSA 3072bit, AES-256으로 암호화된 PEM
openssl genpkey \
  -algorithm RSA \
  -pkeyopt rsa_keygen_bits:3072 \
  -aes-256-cbc \
  -out server.key

# NIST P-256 EC Key
openssl genpkey \
  -algorithm EC \
  -pkeyopt ec_paramgen_curve:P-256 \
  -out server-ec.key

# Ed25519 Key
openssl genpkey -algorithm ED25519 -out signing.key
```

Algorithm은 상대 시스템과 Protocol 지원 범위를 고려해 선택한다. DSA는 새 시스템에서 일반적인 선택이 아니며, 암호화폐에서 쓰이는 `secp256k1`을 일반 TLS Server의 기본값으로 간주하지 않는다.

Private Key 권한을 제한한다.

```shell
chmod 600 server.key
openssl pkey -in server.key -check -noout
```

Key 암호화는 File 유출 시 방어층을 추가하지만 Server가 무인 재시작할 때 Password 주입 문제가 생긴다. Password 제거는 보안 Trade-off를 검토한 뒤 별도 File로 출력하고 원본을 안전하게 처리한다.

```shell
openssl pkey -in encrypted.key -out unencrypted.key
```

## Public Key 추출

```shell
openssl pkey -in server.key -pubout -out server.pub.pem
```

RSA 전용 `openssl rsa`보다 `openssl pkey`가 여러 Key Type에 공통으로 사용할 수 있다.

## CSR 생성

```shell
openssl req -new \
  -key server.key \
  -out server.csr \
  -subj '/CN=api.example.com' \
  -addext 'subjectAltName=DNS:api.example.com,DNS:api.internal.example.com'
```

현대 TLS Client는 Hostname 검증에 Subject Alternative Name을 사용한다. Common Name만 넣은 CSR은 Browser나 Client에서 거부될 수 있다.

```shell
openssl req -in server.csr -text -noout -verify
```

## 개발용 Self-signed Certificate

```shell
openssl req -x509 -new \
  -key server.key \
  -sha256 \
  -days 30 \
  -out server.crt \
  -subj '/CN=localhost' \
  -addext 'subjectAltName=DNS:localhost,IP:127.0.0.1' \
  -addext 'keyUsage=digitalSignature,keyEncipherment' \
  -addext 'extendedKeyUsage=serverAuth'
```

Self-signed Certificate는 암호화는 제공하지만 Client가 미리 신뢰하지 않으면 신원은 보장하지 않는다. 운영에서는 조직 CA나 공인 CA의 발급·갱신 절차를 사용한다.

## 인증서 내용과 만료 확인

```shell
openssl x509 -in server.crt -text -noout
openssl x509 -in server.crt -noout -subject -issuer -dates -fingerprint -sha256
openssl x509 -in server.crt -checkend 2592000 -noout
```

`-checkend 2592000`은 30일 안에 만료되는지 종료 코드로 알려 주므로 Monitoring Script에 사용할 수 있다.

Remote Server가 실제 제공하는 Chain과 SNI 동작은 다음처럼 확인한다.

```shell
openssl s_client \
  -connect api.example.com:443 \
  -servername api.example.com \
  -showcerts </dev/null
```

검증할 때는 Leaf Certificate의 날짜뿐 아니라 SAN, Issuer, Intermediate Chain, Key Usage와 Client Trust Store를 함께 본다. `Verify return code: 0`도 명시한 Trust Store와 Hostname 검증 조건에 따라 해석해야 한다.

# Reference
[OpenSSL - genpkey](https://docs.openssl.org/3.6/man1/openssl-genpkey/)
[OpenSSL - req](https://docs.openssl.org/3.6/man1/openssl-req/)
[OpenSSL - x509](https://docs.openssl.org/3.6/man1/openssl-x509/)
[OpenSSL - s_client](https://docs.openssl.org/3.6/man1/openssl-s_client/)
