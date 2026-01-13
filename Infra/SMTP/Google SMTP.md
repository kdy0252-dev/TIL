---
id: Google SMTP
started: 2025-08-03
tags:
  - ✅DONE
  - Infra
group:
  - "[[Infra]]"
---
# Google SMTP (Gmail 메일 발송)

## 1. 개요 (Overview)
**Google SMTP**는 Google의 Gmail 인프라를 활용하여 애플리케이션에서 이메일을 발송할 수 있게 해주는 기능입니다.
자체 메일 서버(Postfix, Sendmail 등)를 구축하고 유지보수(스팸 필터링, 평판 관리, 보안)하는 것은 매우 비용이 많이 드는 작업입니다. 따라서 스타트업, 개인 프로젝트, 혹은 테스트 환경에서는 Gmail의 SMTP 서버(`smtp.gmail.com`)를 릴레이(Relay)로 사용하는 것이 일반적입니다.

단, Google은 보안 정책상 일반 계정의 아이디/비밀번호 로그인을 차단하고 있으며, **앱 비밀번호(App Password)** 또는 **OAuth 2.0** 인증 방식을 강제합니다.

---

## 2. SMTP 프로토콜의 이해 (Mechanism)

### 2.1 동작 원리
이메일 전송은 **SMTP (Simple Mail Transfer Protocol)** 라는 표준 프로토콜을 따릅니다.
1. **TCP Connection**: 클라이언트(Spring Boot)가 Gmail SMTP 서버(smtp.gmail.com)의 포트(587 or 465)로 연결을 맺습니다.
2. **EHLO (Handshake)**: 클라이언트가 서버에게 인사를 보내고, 인증 방식 등 기능 협상(Negotiation)을 합니다.
3. **STARTTLS**: 587포트의 경우, 처음에는 평문으로 연결했다가 이 명령어를 통해 **암호화된 채널(TLS)** 로 승격시킵니다. (465포트는 처음부터 SSL 연결)
4. **AUTH LOGIN**: Base64로 인코딩된 계정과 비밀번호를 전송하여 인증합니다.
5. **MAIL FROM / RCPT TO**: 발신자와 수신자를 지정합니다.
6. **DATA**: 메일의 본문(Subject, Body, Attachment)을 전송합니다.
7. **QUIT**: 연결을 종료합니다.

### 2.2 포트(Port)의 차이
- **587 (Submission)**: **STARTTLS** 방식. 연결 후 TLS로 업그레이드. 현대적인 표준. 권장됨.
- **465 (SMTPS)**: **SSL** 방식. 연결 수립 시점부터 암호화. (구형 방식이지만 여전히 많이 쓰임).
- **25**: 전통적인 SMTP 포트이나, 대부분의 클라우드 벤더(AWS EC2, GCP 등)에서 스팸 방지를 위해 아웃바운드를 막아놓았습니다. **사용하지 마세요.**

---

## 3. 사전 준비 (Prerequisites)

### 3.1 Google 계정 설정 (필수)
1. **2단계 인증(2FA) 활성화**: 보안 설정에서 2단계 인증을 반드시 켜야 합니다.
2. **앱 비밀번호 생성**:
    - `Google 계정 관리` -> `보안` -> `2단계 인증` -> `앱 비밀번호` 메뉴 진입.
    - '메일', 'Mac(기기 무관)' 선택 후 생성.
    - 생성된 16자리 문자열(예: `abcd efgh ijkl mnop`)이 실제 비밀번호 대신 쓰입니다.

---

## 4. Spring Boot 구현 (Implementation)

Spring Framework는 `JavaMailSender` 인터페이스를 통해 복잡한 SMTP 명령어를 추상화하여 제공합니다.

### 4.1 의존성 추가 (build.gradle)
```groovy
implementation 'org.springframework.boot:spring-boot-starter-mail'
```

### 4.2 설정 파일 (application.yml)
타임아웃 설정과 디버그 옵션을 포함한 상세 설정입니다.

```yaml
spring:
  mail:
    host: smtp.gmail.com
    port: 587
    username: myaccount@gmail.com
    password: "${GMAIL_APP_PASSWORD}" # 환경변수 처리 권장
    properties:
      mail:
        smtp:
          auth: true
          starttls:
            enable: true
            required: true
          connectiontimeout: 5000 # 연결 타임아웃 5초
          timeout: 5000           # I/O 타임아웃 5초
          writetimeout: 5000      # 쓰기 타임아웃 5초
        debug: true               # 로그에 SMTP 통신 과정 출력 (개발 시 유용)
```

### 4.3 Service 코드 구현
```java
@Service
@RequiredArgsConstructor
@Slf4j
public class EmailService {

    private final JavaMailSender javaMailSender;

    // 1. 단순 텍스트 메일 발송
    public void sendSimpleMessage(String to, String subject, String text) {
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom("myaccount@gmail.com"); // 보내는 사람 (생략 시 설정파일 user)
            message.setTo(to);
            message.setSubject(subject);
            message.setText(text);
            
            javaMailSender.send(message);
            log.info("Email Sent to {}", to);
            
        } catch (MailException e) {
            log.error("Failed to send email", e);
            throw new RuntimeException("메일 발송 실패", e);
        }
    }

    // 2. HTML 및 첨부파일 메일 발송 (MIME)
    public void sendMimeMessage(String to, String subject, String htmlBody) {
        MimeMessage message = javaMailSender.createMimeMessage();
        try {
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(htmlBody, true); // true = HTML
            
            // 첨부파일 예시
            // helper.addAttachment("file.txt", new ClassPathResource("static/file.txt"));

            javaMailSender.send(message);
            
        } catch (MessagingException e) {
            log.error("Failed to make mime message", e);
        }
    }
}
```

---

## 5. 운영 및 트러블슈팅 (Troubleshooting)

### 5.1 발송 한도 (Quota)
- Gmail 일반 계정은 **하루 약 500통**의 발송 제한이 있습니다.
- Google Workspace(유료 기업 계정)는 하루 2,000통까지 가능합니다.
- 이를 초과하면 계정이 일시 정지되거나 발송이 차단됩니다. 대량 메일 발송(마케팅 등)용으로는 적합하지 않습니다. -> **AWS SES, SendGrid, Mailgun** 등을 사용해야 합니다.

### 5.2 AuthenticationFailedException
- **원인 1**: 앱 비밀번호가 틀림 (공백 포함 여부 확인).
- **원인 2**: 2단계 인증이 풀려있거나, 보안 수준이 낮은 앱 액세스가 차단됨.
- **해결**: 앱 비밀번호를 재생성하고, `mail.debug=true` 로그를 확인하여 `535 5.7.8 Username and Password not accepted` 에러인지 확인합니다.

### 5.3 비동기 처리 (Async)
- 메일 발송은 외부 네트워크 통신이므로 수 초(1~3초)가 걸릴 수 있습니다.
- 유저가 "회원가입" 버튼을 눌렀는데 메일 보낸다고 3초간 멈춰있으면 경험이 좋지 않습니다.
- `@Async`를 사용하여 별도 스레드에서 비동기로 발송하세요.

```java
@Async
public void sendMailAsync(String to, String subject, String text) { 
    // ... 
}
```

# Reference
- [Spring Boot Email Guide](https://spring.io/guides/gs/sending-email/)
- [Google SMTP Server Settings](https://support.google.com/mail/answer/7126229?hl=en)