---
id: SPIFFE와 SPIRE Workload Identity
started: 2026-06-03
tags:
  - ✅DONE
  - Security
  - SPIFFE
group:
  - "[[Architecture]]"
---
# SPIFFE와 SPIRE Workload Identity

## 1. Workload Identity

IP, Node 또는 장기 Secret 대신 실행 중인 Workload 자체에 검증 가능한 신원을 부여합니다. SPIFFE는 신원 형식과 API를, SPIRE는 이를 발급·회전하는 구현을 제공합니다.

---

## 2. SPIFFE ID

```text
spiffe://example.org/ns/production/sa/core-app
```

Trust Domain과 Path로 Workload를 식별합니다. Path Naming은 Authorization Policy와 장기적으로 결합되므로 안정적으로 설계합니다.

---

## 3. SVID

SPIFFE Verifiable Identity Document는 Workload가 SPIFFE ID를 증명하는 Credential입니다.

- X.509-SVID: mTLS에 사용
- JWT-SVID: HTTP·Token 기반 검증에 사용

짧은 수명과 자동 회전으로 장기 인증서 배포를 줄입니다.

---

## 4. Attestation

SPIRE Server는 Node를, Agent는 Process·Kubernetes ServiceAccount 같은 Selector로 Workload를 Attest합니다. “어디서 실행되는가”와 “어떤 Workload인가”를 연결합니다.

ServiceAccount가 같아도 Namespace·Cluster·Image 등 추가 Selector 정책을 검토합니다.

---

## 5. Workload API

Application 또는 Proxy는 Local Workload API에서 SVID와 Trust Bundle을 받습니다. 파일에 장기 Key를 배포하지 않고 회전 Event를 구독할 수 있습니다.

Private Key가 Workload 경계 밖으로 노출되지 않게 Socket 권한을 보호합니다.

---

## 6. Federation

서로 다른 Trust Domain이 Bundle을 교환하면 Multi-cluster·Multi-cloud Workload가 신뢰할 수 있습니다. Federation은 모든 신원을 허용하는 것이 아니라 어떤 SPIFFE ID를 받아들일지 Authorization이 필요합니다.

---

## 7. Service Mesh와 관계

Istio도 Workload Certificate와 mTLS Identity를 제공합니다. SPIFFE ID 형식을 활용하지만 별도 SPIRE 도입이 항상 필요한 것은 아닙니다.

Mesh 밖 Workload, Multi-platform Federation, 독립 Identity Control Plane 요구가 있을 때 도입 가치를 비교합니다.

---

## 8. 인증과 인가

SVID는 신원을 증명할 뿐 접근 권한을 자동 부여하지 않습니다. Caller SPIFFE ID, 대상 Service, Method와 Environment를 AuthorizationPolicy로 제한합니다.

신원 발급 오류와 정책 오류를 분리해 관측합니다.

---

## 9. 장애와 회전

SPIRE Server·Agent 장애, Trust Bundle 갱신 실패, Clock Drift, 만료 직전 Connection과 Federation 단절을 Test합니다. 짧은 Credential 수명은 보안을 높이지만 발급 Control Plane 가용성 의존성을 만듭니다.

---

## 10. Registration Entry

SPIRE는 Parent ID와 Selector를 기반으로 어떤 Workload에 어떤 SPIFFE ID를 발급할지 정합니다. Kubernetes Namespace와 ServiceAccount만 신뢰할지, Cluster·Node·Pod Label을 추가할지 공격 모델에 따라 선택합니다.

너무 넓은 Selector는 같은 ServiceAccount를 사용하는 예상 밖 Workload에도 신원을 발급할 수 있습니다. Registration Entry 변경을 코드로 관리하고 Audit합니다.

---

## 11. Secret Manager와 차이

Secret Manager는 Password·API Key 같은 값을 보관하고 SPIFFE는 실행 중 Workload 신원을 발급합니다. SPIFFE가 외부 Provider의 고정 API Key를 자동 제거하지는 않습니다. 가능한 통합부터 mTLS·Federated Identity로 전환하고 나머지는 Secret Manager를 사용합니다.

---

## 12. 적용 단계

1. 현재 ServiceAccount·Certificate·Secret 기반 신원을 Inventory화합니다.
2. Trust Domain과 SPIFFE ID Naming을 정합니다.
3. 비운영 Cluster에서 Server·Agent HA를 구성합니다.
4. 한 서비스 간 mTLS부터 SVID 회전을 검증합니다.
5. Authorization을 Caller ID 기반으로 전환합니다.
6. Federation과 Mesh 통합은 필요성이 확인된 뒤 확장합니다.

---

## 13. 완료 기준

- [ ] IP·Node Identity와 Workload Identity 차이를 설명합니다.
- [ ] SPIFFE ID Naming과 Trust Domain이 문서화됩니다.
- [ ] SVID 자동 회전 중 Connection이 유지됩니다.
- [ ] 인증과 Authorization Policy를 별도로 Test합니다.
- [ ] Mesh 기본 Identity와 SPIRE 추가 가치가 비교되어 있습니다.

# Reference

- [SPIFFE Documentation](https://spiffe.io/docs/latest/spiffe-about/overview/)
- [SPIRE Documentation](https://spiffe.io/docs/latest/spire-about/)
- [[Istio Ambient Mesh와 Kiali]]
- [[STRIDE Threat Modeling]]
