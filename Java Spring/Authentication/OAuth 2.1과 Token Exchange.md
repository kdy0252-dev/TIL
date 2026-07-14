---
id: OAuth 2.1과 Token Exchange
started: 2026-05-27
tags:
  - ✅DONE
  - OAuth
  - Security
group:
  - "[[Java Spring]]"
---
# OAuth 2.1과 Token Exchange

## 1. OAuth의 역할

OAuth는 비밀번호를 공유하지 않고 Client에 제한된 API 접근 권한을 위임하는 Framework입니다. 인증 자체는 OpenID Connect가 담당합니다.

OAuth 2.1은 현대적인 안전 Practice를 모으고 Authorization Code + PKCE를 기본 흐름으로 강조합니다.

---

## 2. 폐기해야 할 흐름

- Implicit Grant
- Resource Owner Password Credentials
- Redirect URI의 느슨한 Matching
- PKCE 없는 Public Client Authorization Code
- Browser Storage의 장기 Access Token

기존 OAuth 2.0 구현도 이 원칙에 맞게 점검합니다.

---

## 3. PKCE

Client가 임의 `code_verifier`를 만들고 Hash인 `code_challenge`를 Authorization 요청에 보냅니다. Token 교환 때 원래 Verifier를 증명해 탈취된 Authorization Code의 사용을 막습니다.

`S256`을 사용하고 Plain 방식은 피합니다.

---

## 4. Access와 Refresh Token

Access Token은 짧게 유지하고 Audience, Scope, Issuer, Expiry를 검증합니다. Refresh Token은 Rotation과 재사용 탐지를 적용합니다.

JWT라고 철회가 불가능한 문제까지 해결되지는 않습니다. 중요한 권한 변경은 짧은 만료, Introspection 또는 Session 통제를 검토합니다.

---

## 5. Sender Constrained Token

Bearer Token은 가진 사람이 누구든 사용할 수 있습니다. DPoP 또는 mTLS-bound Token은 특정 Key 소유를 요구해 탈취 재사용을 줄입니다.

Key Rotation, Proxy와 Mobile Secure Storage 비용을 함께 고려합니다.

---

## 6. Token Exchange

RFC 8693 Token Exchange는 하나의 Token을 다른 Audience·Scope·Actor Context의 Token으로 교환합니다.

```text
사용자 Token
  -> Token Service
  -> Downstream 전용 짧은 Token
```

Gateway가 받은 넓은 Token을 모든 내부 서비스에 그대로 전달하는 것보다 Audience와 권한을 줄일 수 있습니다.

---

## 7. Delegation과 Impersonation

- Delegation: Service가 사용자를 대신해 행동하며 Actor도 보존
- Impersonation: 교환된 Token Subject 자체가 다른 신원

감사 Log에 Subject, Actor, Audience와 교환 Chain을 남겨 누가 누구를 대신했는지 추적합니다.

---

## 8. BFF Pattern

Browser SPA가 Token을 직접 오래 보관하는 대신 BFF가 OAuth Client가 되어 HttpOnly·Secure·SameSite Cookie로 Session을 관리할 수 있습니다. CSRF, Session Store와 BFF 가용성 책임이 추가됩니다.

---

## 9. 사례 적용

Gateway는 Issuer·Audience·Scope를 검증하고 관리 API와 일반 API를 분리합니다. 내부 호출은 필요할 때 Downstream Audience 전용 Token으로 교환하며 신뢰 Header만 전달하는 방식을 피합니다.

---

## 10. 완료 기준

- [ ] Public Client가 Authorization Code + PKCE를 사용합니다.
- [ ] Issuer, Audience, Scope와 Expiry를 모두 검증합니다.
- [ ] Refresh Token Rotation과 재사용 탐지가 있습니다.
- [ ] Token Exchange가 권한을 확대하지 않습니다.
- [ ] Delegation Chain이 감사 Log에 남습니다.
- [ ] Browser Token 저장과 CSRF 위협을 Test합니다.

# Reference

- [OAuth 2.1 Draft](https://datatracker.ietf.org/doc/draft-ietf-oauth-v2-1/)
- [OAuth 2.0 Token Exchange RFC 8693](https://www.rfc-editor.org/rfc/rfc8693)
- [[OAuth 2.0]]
