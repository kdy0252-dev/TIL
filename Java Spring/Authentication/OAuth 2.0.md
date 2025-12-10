---
id: OAuth 2.0
started: 2025-10-11
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# OAuth 2.0 (Authorization Framework)

## 1. 개요 (Overview)
**OAuth 2.0**은 리소스 소유자(User)가 자신의 비밀번호를 제공하지 않고도, 제3자 애플리케이션(Client)에게 자신의 리소스(예: 구글 캘린더, 카카오톡 친구 목록)에 접근할 수 있는 권한을 위임(Delegation)하는 **인가(Authorization) 프레임워크**입니다.

많은 사람들이 "OAuth 로그인"이라고 부르지만, 엄밀히 말해 OAuth는 **권한 부여(Authorization)** 프로토콜이며, **인증(Authentication)**은 OAuth 2.0 기반 위에 아이덴티티 레이어를 추가한 **OIDC (OpenID Connect)**가 담당합니다.

---

## 2. 주요 구성 요소 (Roles)
1. **Resource Owner (사용자)**: 자원의 소유자이며, 권한을 부여하는 주체입니다.
2. **Client (애플리케이션)**: 자원에 접근하고자 하는 웹/앱 서비스. (예: 내 서비스)
3. **Authorization Server (인증 서버)**: 사용자를 인증하고 Client에게 토큰을 발급하는 서버. (예: Google Auth, Keycloak).
4. **Resource Server (API 서버)**: Access Token을 확인하고 실제 데이터를 제공하는 서버. (예: Google Calendar API).

---

## 3. 권한 부여 방식 (Grant Types)
보안 수준과 클라이언트의 형태에 따라 4가지 방식이 존재합니다.

### 3.1 Authorization Code Grant (권한 부여 코드 승인)
**가장 많이 사용되고 가장 안전한 방식**입니다. 서버 사이드 애플리케이션(Spring Boot, Node.js)에 적합합니다.
- **특징**: `Client Secret`을 서버(백엔드)에 숨길 수 있어 보안성이 높습니다. Access Token이 브라우저에 노출되지 않습니다.
- **Flow**:
    1. **User -> Client**: 로그인 요청.
    2. **Client -> User**: Authorization Server로 리다이렉트 (client_id, redirect_uri 포함).
    3. **User -> Auth Server**: 로그인 및 권한 승인.
    4. **Auth Server -> Client**: 미리 등록된 Redirect URI로 임시 **Code** 전달.
    5. **Client -> Auth Server**: 받은 **Code**와 **Client Secret**을 실어서 토큰 요청(POST).
    6. **Auth Server -> Client**: **Access Token** (+ Refresh Token) 발급.
    7. **Client -> Resource Server**: Token을 Header에 담아 API 호출.

### 3.2 Implicit Grant (암시적 승인) - Deprecated
- SPA(Single Page App) 브라우저에서 바로 토큰을 받는 방식이었으나, 토큰 탈취 위험으로 인해 현재는 **PKCE(Proof Key for Code Exchange)**를 적용한 Authorization Code Grant 권장으로 바뀌었습니다.

### 3.3 Resource Owner Password Credentials Grant - Deprecated
- 사용자가 아이디/비밀번호를 Client에 직접 입력하는 방식입니다. Client를 100% 신뢰할 수 있을 때(같은 회사 앱 등)만 썼으나 보안상 지양됩니다.

### 3.4 Client Credentials Grant (클라이언트 자격증명 승인)
- 사용자(User) 개입 없이, Client(서버)가 자신의 권한으로 API를 호출할 때 사용합니다. (예: 백엔드 간 통신, 배치 작업).

---

## 4. Token의 종류
### Access Token
- 실제 리소스 접근 권한을 가진 열쇠입니다.
- 보안을 위해 만료 시간(TTL)이 30분~1시간 정도로 짧습니다.
- **Stateless (JWT)**: 토큰 자체에 정보를 담아 DB 조회 없이 검증 가능.
- **Stateful (Reference)**: 랜덤 문자열. DB 조회를 통해 검증.

### Refresh Token
- Access Token이 만료되면, 사용자가 다시 로그인을 할 필요 없이 새 Access Token을 발급받기 위해 사용하는 토큰입니다.
- TTL이 2주~한 달로 깁니다. 탈취 시 위험하므로 **RTR (Refresh Token Rotation)** 전략을 사용하여 한 번 쓰면 폐기하고 새로 발급하기도 합니다.

---

## 5. Spring Security OAuth2 Client 구현

Spring Security 5부터는 OAuth2 클라이언트 기능이 일원화되었습니다.

### 5.1 `application.yml` 설정
Google과 Kakao 로그인을 위한 설정입니다. `client-id`와 `client-secret`은 보안 정보이므로 환경변수나 Vault로 관리해야 합니다.

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: profile, email
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
          kakao:
            client-id: ${KAKAO_CLIENT_ID}
            client-authentication-method: POST
            authorization-grant-type: authorization_code
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
            client-name: Kakao
            scope: profile_nickname, account_email
        provider:
          kakao:
            authorization-uri: https://kauth.kakao.com/oauth/authorize
            token-uri: https://kauth.kakao.com/oauth/token
            user-info-uri: https://kapi.kakao.com/v2/user/me
            user-name-attribute: id
```

### 5.2 SecurityConfig 설정
```java
@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final CustomOAuth2UserService customOAuth2UserService;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/", "/login/**", "/css/**").permitAll()
                .anyRequest().authenticated()
            )
            .oauth2Login(oauth2 -> oauth2
                .userInfoEndpoint(userInfo -> userInfo
                    .userService(customOAuth2UserService) // 로그인 성공 후 사용자 정보 처리
                )
                .defaultSuccessUrl("/")
            );
        return http.build();
    }
}
```

### 5.3 CustomOAuth2UserService (후처리 로직)
로그인 성공 후 받아온 사용자 정보(Attributes)를 기반으로 회원가입을 시키거나 정보를 업데이트하는 핵심 로직입니다.

```java
@Service
@RequiredArgsConstructor
@Slf4j
public class CustomOAuth2UserService extends DefaultOAuth2UserService {

    private final UserRepository userRepository;

    @Override
    public OAuth2User loadUser(OAuth2UserRequest userRequest) throws OAuth2AuthenticationException {
        // 1. 기본 기능을 통해 사용자 정보 가져오기
        OAuth2User oAuth2User = super.loadUser(userRequest);
        
        // 2. 어떤 서비스인지 구분 (google, kakao, naver)
        String registrationId = userRequest.getClientRegistration().getRegistrationId();
        
        // 3. 사용자 정보 파싱 (서비스마다 JSON 구조가 다름)
        OAuthAttributes attributes = OAuthAttributes.of(registrationId, oAuth2User.getAttributes());
        
        // 4. DB 저장 또는 업데이트 (Upsert)
        User user = saveOrUpdate(attributes);
        
        // 5. 세션에 저장할 DTO 반환 (또는 JWT 발급 로직 연계)
        return new DefaultOAuth2User(
                Collections.singleton(new SimpleGrantedAuthority(user.getRoleKey())),
                attributes.getAttributes(),
                attributes.getNameAttributeKey());
    }

    private User saveOrUpdate(OAuthAttributes attributes) {
        User user = userRepository.findByEmail(attributes.getEmail())
                .map(entity -> entity.update(attributes.getName(), attributes.getPicture()))
                .orElse(attributes.toEntity());
        return userRepository.save(user);
    }
}
```

# Reference
- [RFC 6749: The OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [Spring Security OAuth2 Reference](https://docs.spring.io/spring-security/reference/servlet/oauth2/index.html)
- [OAuth 2.0 Simplified](https://www.oauth.com/)