---
id: STRIDE Threat Modeling
started: 2026-06-05
tags:
  - ✅DONE
  - Security
  - Threat-Modeling
group:
  - "[[Infra]]"
---
# STRIDE Threat Modeling

## 1. 개요

Threat Modeling은 침투 테스트 전에 시스템의 자산, 신뢰 경계와 공격 경로를 설계 단계에서 찾는 활동입니다. STRIDE는 위협을 여섯 범주로 빠짐없이 질문하게 합니다.

---

## 2. STRIDE

| 범주 | 질문 | 대표 통제 |
|---|---|---|
| Spoofing | 다른 신원으로 가장할 수 있는가 | 강한 인증, Workload Identity |
| Tampering | 데이터·Artifact를 바꿀 수 있는가 | 서명, 무결성, 권한 |
| Repudiation | 행위를 부인할 수 있는가 | 감사 Log, 추적 ID |
| Information Disclosure | 비밀·개인정보가 노출되는가 | 암호화, Masking, 최소 수집 |
| Denial of Service | 자원을 고갈시킬 수 있는가 | Rate Limit, Quota, Backpressure |
| Elevation of Privilege | 더 높은 권한을 얻을 수 있는가 | 최소 권한, 경계 검증 |

---

## 3. Data Flow Diagram

먼저 Browser, Gateway, Application, DB, Redis, 외부 Provider, CI/CD와 운영자를 그립니다. Process, Data Store, 외부 Entity와 Data Flow를 표시하고 인증 방식과 Protocol을 적습니다.

신뢰 수준이 바뀌는 곳에 Trust Boundary를 그립니다.

---

## 4. 자산

- 사용자·운전자 개인정보
- 인증 Token과 Service Credential
- 예약·배차·운행 상태
- 관리자 권한
- Container Image와 CI Credential
- Backup, Log, Trace와 오류 Event

자산 가치와 손실 영향이 우선순위를 결정합니다.

---

## 5. 경계별 질문

### Browser→Gateway

Token 탈취, CORS, Replay, Rate Limit, BOLA를 봅니다.

### Gateway→Application

신뢰 Header 위조, JWT 재검증, Route 우회와 관리 Endpoint 노출을 봅니다.

### Application→DB·Redis

Tenant 격리, SQL Injection, Credential, Backup 노출과 Cache Key 충돌을 봅니다.

### CI→Registry→Cluster

Build 변조, Tag 교체, 서명 우회와 과도한 배포 권한을 봅니다.

---

## 6. BOLA와 Multi-tenancy

사용자가 유효한 ID를 바꿔 다른 Tenant Resource에 접근하는 Broken Object Level Authorization을 Test합니다. Repository Query에 Tenant 조건이 항상 포함되고 Cache·Object Storage Key도 Tenant를 구분해야 합니다.

인증 성공은 해당 객체 권한을 뜻하지 않습니다.

---

## 7. 위협 우선순위

Likelihood와 Impact를 평가하되 숫자를 정밀한 과학처럼 사용하지 않습니다. Internet 노출, 공격 난이도, 권한, 탐지 가능성, 데이터 영향을 근거로 P0~P2를 정합니다.

통제 후 남는 Residual Risk와 수용 주체를 기록합니다.

---

## 8. Abuse Case

정상 Use Case의 반대 질문을 만듭니다.

- 예약 생성 API를 무한 호출하면?
- 다른 Tenant ID를 넣으면?
- 같은 Idempotency Key에 다른 Payload를 보내면?
- 만료 직전 Token을 재생하면?
- Image Tag를 Registry에서 바꾸면?

각 Abuse Case를 Test, Policy, Alert 또는 Runbook으로 연결합니다.

---

## 9. 운영과 갱신

새 외부 연동, 인증 변경, Data Store, Public Endpoint, 권한 모델 변경 때 Threat Model을 갱신합니다. Diagram이 실제 Terraform·Route와 달라지지 않도록 Architecture Review에 포함합니다.

---

## 10. 완료 기준

- [ ] 자산과 Trust Boundary가 Diagram에 표시됩니다.
- [ ] 각 Flow에 STRIDE 질문과 통제가 있습니다.
- [ ] Multi-tenant Object Authorization Test가 있습니다.
- [ ] 위협마다 Owner, 우선순위와 Residual Risk가 있습니다.
- [ ] 높은 위험이 Automated Test·Policy·Alert로 연결됩니다.

# Reference

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [OWASP API Security Top 10](https://owasp.org/API-Security/)
- [[Kubernetes Policy as Code]]
- [[SLSA SBOM Cosign 공급망 보안]]
