---
id: AWS Cognito
started: 2026-01-02
tags:
  - ✅DONE
group:
  - "[[AWS]]"
  - "[[Security]]"
---
# AWS Cognito
AWS Cognito는 웹 및 모바일 앱을 위한 확장 가능한 인증(Authentication), 권한 부여(Authorization) 및 사용자 관리 기능을 제공합니다. 수백만 명의 사용자로 확장할 수 있으며 Google, Facebook, Amazon과 같은 소셜 IdP 및 Apple, SAML 2.0, OpenID Connect(OIDC)를 통한 엔터프라이즈 IdP와의 연동을 지원합니다.
## 1. 핵심 아키텍처 및 개념
Cognito는 크게 두 가지 핵심 컴포넌트로 구성됩니다.
### A. User Pools (인증의 주체)
- **역할**: 사용자 디렉토리 서비스. 가입(Sign-up) 및 로그인(Sign-in)을 처리합니다.
- **결과물**: 인증 성공 시 JWT(JSON Web Token)를 발급합니다.
- **주요 기능**: 사용자 프로필 관리, MFA(Multi-Factor Authentication), 비밀번호 정책, 메일/메시지 인증.
### B. Identity Pools (권한의 주체)
- **역할**: 사용자에게 AWS 리소스(S3, DynamoDB 등)에 접근할 수 있는 임시 IAM 자격 증명을 부여합니다.
- **연동**: User Pool 뿐만 아니라 다른 IdP 인증 결과를 입력받아 IAM Role로 교환해줍니다.
---
## 2. 인증 토큰 이해 (JWT)
성공적인 인증 후 Cognito는 세 가지 토큰을 발급합니다.
1. **ID Token**: 사용자의 ID 정보(이름, 이메일 등)를 포함. (사용자 식별용)
2. **Access Token**: API 접근 권한 여부를 확인. (인가용)
3. **Refresh Token**: Access/ID 토큰이 만료되었을 때 새로운 토큰을 발급받기 위해 사용.
---
## 3. 예제: Spring Boot + AWS Cognito 통합
이 예제는 Java용 AWS SDK v2를 사용하여 사용자 가입, 로그인, 그리고 Spring Security와 연동한 JWT 검증 전 과정을 다룹니다.
### 3.1 프로젝트 설정 (build.gradle)
```gradle
dependencies {
    // AWS SDK for Cognito
    implementation 'software.amazon.awssdk:cognitoidentityprovider:2.20.0'
    
    // Spring Security & JWT
    implementation 'org.springframework.boot:spring-boot-starter-security'
    implementation 'org.springframework.boot:spring-boot-starter-oauth2-resource-server'
    implementation 'com.auth0:java-jwt:4.4.0'
    implementation 'com.auth0:jwks-rsa:0.22.1'
    
    // Utils
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```
### 3.2 SDK 및 보안 설정 (CognitoConfig.java)
```java
package com.example.infra.config;

import software.amazon.awssdk.auth.credentials.DefaultCredentialsProvider;
import software.amazon.awssdk.regions.Region;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class CognitoConfig {

    private final String region = "ap-northeast-2";

    @Bean
    public CognitoIdentityProviderClient cognitoClient() {
        return CognitoIdentityProviderClient.builder()
                .region(Region.of(region))
                .credentialsProvider(DefaultCredentialsProvider.create())
                .build();
    }
}
```
### 3.3 사용자 관리 서비스 (CognitoService.java)
가입, 확인, 로그인을 처리하는 핵심 로직입니다.
```java
package com.example.infra.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.services.cognitoidentityprovider.CognitoIdentityProviderClient;
import software.amazon.awssdk.services.cognitoidentityprovider.model.*;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class CognitoService {

    private final CognitoIdentityProviderClient cognitoClient;

    @Value("${aws.cognito.user-pool-id}")
    private String userPoolId;

    @Value("${aws.cognito.client-id}")
    private String clientId;

    @Value("${aws.cognito.client-secret}")
    private String clientSecret;

    /**
     * 회원 가입 요청
     */
    public void signUp(String email, String password) {
        String secretHash = calculateSecretHash(clientId, clientSecret, email);
        
        SignUpRequest request = SignUpRequest.builder()
                .clientId(clientId)
                .secretHash(secretHash)
                .username(email)
                .password(password)
                .userAttributes(AttributeType.builder().name("email").value(email).build())
                .build();

        cognitoClient.signUp(request);
        log.info("Sign up successful for user: {}", email);
    }

    /**
     * 회원 가입 확인 (메일 인증 코드 입력)
     */
    public void confirmSignUp(String email, String code) {
        String secretHash = calculateSecretHash(clientId, clientSecret, email);

        ConfirmSignUpRequest request = ConfirmSignUpRequest.builder()
                .clientId(clientId)
                .secretHash(secretHash)
                .username(email)
                .confirmationCode(code)
                .build();

        cognitoClient.confirmSignUp(request);
    }

    /**
     * 사용자 인증 (로그인)
     */
    public AuthenticationResultType login(String email, String password) {
        String secretHash = calculateSecretHash(clientId, clientSecret, email);

        AdminInitiateAuthRequest authRequest = AdminInitiateAuthRequest.builder()
                .userPoolId(userPoolId)
                .clientId(clientId)
                .authFlow(AuthFlowType.ADMIN_NO_SRP_AUTH)
                .authParameters(Map.of(
                        "USERNAME", email,
                        "PASSWORD", password,
                        "SECRET_HASH", secretHash
                ))
                .build();

        AdminInitiateAuthResponse response = cognitoClient.adminInitiateAuth(authRequest);
        return response.authenticationResult();
    }

    /**
     * Cognito Client Secret이 설정된 경우 필요한 HMAC SHA256 해시 계산
     */
    private String calculateSecretHash(String userPoolClientId, String userPoolClientSecret, String userName) {
        final String HMAC_SHA256_ALGORITHM = "HmacSHA256";
        SecretKeySpec signingKey = new SecretKeySpec(userPoolClientSecret.getBytes(StandardCharsets.UTF_8), HMAC_SHA256_ALGORITHM);
        try {
            Mac mac = Mac.getInstance(HMAC_SHA256_ALGORITHM);
            mac.init(signingKey);
            mac.update(userName.getBytes(StandardCharsets.UTF_8));
            byte[] rawHmac = mac.doFinal(userPoolClientId.getBytes(StandardCharsets.UTF_8));
            return Base64.getEncoder().encodeToString(rawHmac);
        } catch (Exception e) {
            throw new RuntimeException("Error calculating secret hash", e);
        }
    }
}
```
### 3.4 JWT 검증 필터 (JwtAuthenticationFilter.java)
발급된 토큰의 위변조 여부를 확인합니다.
```java
package com.example.infra.security;

import com.auth0.jwk.JwkProvider;
import com.auth0.jwk.UrlJwkProvider;
import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.interfaces.DecodedJWT;
import jakarta.servlet.FilterChain;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.net.URL;
import java.security.interfaces.RSAPublicKey;

@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final String jwksUrl = "https://cognito-idp.ap-northeast-2.amazonaws.com/{userPoolId}/.well-known/jwks.json";

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) 
            throws java.io.IOException, jakarta.servlet.ServletException {
        
        String header = request.getHeader("Authorization");

        if (header != null && header.startsWith("Bearer ")) {
            String token = header.substring(7);
            try {
                // 1. JWT 파싱
                DecodedJWT jwt = JWT.decode(token);
                
                // 2. JWKS를 통한 공개키 획득 및 검증
                JwkProvider provider = new UrlJwkProvider(new URL(jwksUrl));
                RSAPublicKey publicKey = (RSAPublicKey) provider.get(jwt.getKeyId()).getPublicKey();
                Algorithm algorithm = Algorithm.RSA256(publicKey, null);
                
                algorithm.verify(jwt); // 서명 검증

                // 3. SecurityContext에 인증 정보 저장
                UsernamePasswordAuthenticationToken auth = new UsernamePasswordAuthenticationToken(
                        jwt.getSubject(), null, java.util.Collections.emptyList());
                SecurityContextHolder.getContext().setAuthentication(auth);
                
            } catch (Exception e) {
                SecurityContextHolder.clearContext();
            }
        }
        filterChain.doFilter(request, response);
    }
}
```
### 3.5 API 컨트롤러 (AuthController.java)
```java
package com.example.infra.controller;

import com.example.infra.service.CognitoService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import software.amazon.awssdk.services.cognitoidentityprovider.model.AuthenticationResultType;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final CognitoService cognitoService;

    @PostMapping("/signup")
    public String signUp(@RequestParam String email, @RequestParam String password) {
        cognitoService.signUp(email, password);
        return "Sign up pending confirmation. Check your email.";
    }

    @PostMapping("/confirm")
    public String confirm(@RequestParam String email, @RequestParam String code) {
        cognitoService.confirmSignUp(email, code);
        return "User confirmed successfully.";
    }

    @PostMapping("/login")
    public AuthenticationResultType login(@RequestParam String email, @RequestParam String password) {
        return cognitoService.login(email, password);
    }
}
```

---
## 4. Lambda Trigger 활용 팁
Cognito는 인증 흐름의 특정 시점에 AWS Lambda를 실행할 수 있는 기능을 제공합니다.
- **Pre Sign-up**: 유저가 가입하기 전 특정 도메인의 이메일만 허용하거나 사내 DB에 미리 등록된 유저인지 확인합니다.
- **Post Confirmation**: 가입 완료 후 환영 메일을 보내거나 외부 시스템(CRM 등)에 사용자 정보를 연동합니다.
- **Custom Message**: 인증 코드 메일의 본문 내용을 동적으로 변경합니다.
---
## 5. Cognito 선택 시 고려사항

### A. 테넌시 전략
멀티 테넌트 앱인 경우 각 테넌트마다 User Pool을 생성할지, 아니면 하나의 User Pool 내에서 `Custom Attribute`로 구분할지 설계가 필요합니다.
### B. 비용 관리
MAU(Monthly Active Users) 기반 과금이므로, 대규모 사용자 베이스 서비스에서는 비용 최적화 전략이 필요할 수 있습니다. (휴면 계정 정리 등)
### C. 보안 (Passwordless)
최신 트렌드인 WebAuthn/Passkey 연동을 고려한다면 Cognito의 `Custom Authentication Flow`를 활용하여 구현할 수 있습니다.

# Reference
- [AWS Cognito 공식 개발자 안내서](https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html)
- [Java SDK v2 Cognito API Reference](https://sdk.amazonaws.com/java/api/latest/software/amazon/awssdk/services/cognitoidentityprovider/package-summary.html)
- [Spring Security integration with Cognito](https://spring.io/guides/tutorials/spring-boot-oauth2/)