---
id: SLO와 Error Budget 운영
started: 2026-06-17
tags:
  - ✅DONE
  - SRE
  - SLO
  - Error-Budget
group:
  - "[[Infra Otel+LGTM]]"
---
# SLO와 Error Budget 운영

## 1. 개요

Service Level Objective(SLO)는 사용자가 기대할 수 있는 신뢰성의 목표입니다. Error Budget은 그 목표 안에서 허용되는 실패량입니다.

```text
SLI = 측정한 사용자 경험
SLO = SLI가 달성해야 할 목표
Error Budget = 1 - SLO
```

99.9% Availability SLO라면 28일 동안 유효 요청의 0.1%를 실패로 허용합니다. Error Budget은 장애를 정당화하는 숫자가 아니라 기능 개발 속도와 안정성 투자의 균형을 결정하는 제어 장치입니다.

---

## 2. SLA, SLO, SLI

| 용어 | 의미 | 대상 |
|---|---|---|
| SLA | 위반 시 계약상 결과가 있는 약속 | 고객·사업 |
| SLO | 내부 운영 목표 | 제품·개발·운영 |
| SLI | 목표를 계산하는 실제 측정값 | Metric·Log·Probe |

SLO는 SLA보다 엄격하게 두어 대응 여유를 확보할 수 있습니다. 모든 Metric을 SLI로 삼지 않고 사용자 경험을 직접 나타내는 소수의 지표를 선택합니다.

---

## 3. 좋은 SLI

### Availability

```text
성공한 유효 요청 / 전체 유효 요청
```

4xx 전체를 실패로 세면 사용자 입력 오류가 서비스 Error Budget을 소모합니다. 인증 서비스 장애로 발생한 401처럼 실제 시스템 책임인 경우는 별도 분류가 필요합니다.

### Latency

평균이 아니라 기준 시간 이내의 Good Event 비율로 계산합니다.

```text
500ms 이내 성공한 요청 / 전체 유효 요청
```

### Correctness와 Freshness

HTTP 200이어도 잘못된 배차 결과를 반환하거나 통계가 하루 늦으면 실패일 수 있습니다. 비동기 Pipeline은 처리 완료율과 Event Freshness를 SLI로 둡니다.

---

## 4. 측정 위치

Server Metric은 내부 원인 분석에 좋지만 사용자 앞의 DNS, CDN, Gateway 장애를 놓칠 수 있습니다. 반대로 Synthetic Check는 실제 Traffic 분포를 대표하지 못합니다.

권장 조합:

- Load Balancer 또는 Gateway의 Request SLI
- Application의 업무 성공 SLI
- 외부 Synthetic Availability
- 비동기 Queue의 Freshness SLI

중복 집계와 Retry 요청을 어떻게 셀지 명시합니다.

---

## 5. Error Budget 계산

```text
Budget Events = Total Valid Events × (1 - SLO)
Consumed      = Bad Events
Remaining     = Budget Events - Consumed
```

Low-traffic 서비스는 Event 비율이 한두 요청에 크게 흔들립니다. 시간 기반 Availability나 Synthetic을 보조로 사용할 수 있지만 Traffic이 없는 시간의 의미를 먼저 정해야 합니다.

---

## 6. Burn Rate

Burn Rate는 허용 속도보다 Error Budget을 몇 배 빠르게 소비하는지 나타냅니다.

```text
Burn Rate = 실제 Error Rate / 허용 Error Rate
```

99.9% SLO에서 실제 Error Rate가 1%면 Burn Rate는 10입니다. 현재 속도가 지속되면 Budget을 예상보다 10배 빨리 소모합니다.

---

## 7. Multi-window Alert

짧은 Window만 보면 Noise가 많고 긴 Window만 보면 탐지가 늦습니다. 빠른 대규모 장애와 느린 지속 열화를 서로 다른 Window로 감지합니다.

```text
Fast burn:  5m와 1h 모두 높은 Burn Rate
Slow burn:  30m와 6h 모두 중간 Burn Rate
```

두 Window 조건을 함께 만족하게 하면 순간 Spike를 줄이면서 지속 장애를 찾을 수 있습니다. 임계치는 SLO Window와 허용 탐지 시간에 맞춰 계산합니다.

---

## 8. Error Budget Policy

정책에는 숫자뿐 아니라 행동을 연결합니다.

- Budget이 충분하면 정상 Release를 진행합니다.
- 일정 비율 이하이면 위험 변경과 대규모 Migration을 제한합니다.
- Budget이 소진되면 보안·복구 변경 외 Release를 중단합니다.
- 단일 Incident가 큰 Budget을 소비하면 Postmortem을 수행합니다.
- 외부 공통 장애와 Load Test Traffic의 처리 기준을 정합니다.

정책은 처벌이 아니라 신뢰성 작업에 집중할 근거입니다.

---

## 9. 사례 시스템에 적용

Critical Journey를 다음처럼 분리할 수 있습니다.

| Journey | SLI 예시 |
|---|---|
| 예약 생성 | 유효 요청 중 정해진 시간 내 성공 비율 |
| 배차 조회 | 500ms 이내 정확한 결과 비율 |
| 운행 상태 변경 | 중복 없이 최종 상태로 수렴한 비율 |
| 알림 발송 | 제한 시간 내 Provider에 수락된 비율 |
| 통계 집계 | 업무 마감 후 목표 시간 내 최신화 비율 |

모든 API를 하나의 SLO로 합치면 중요도가 낮은 빠른 API가 핵심 흐름을 가립니다.

---

## 10. 부족한 점과 해결 방법

현재 Metric·Alert·Synthetic 기반은 있지만 개별 Resource Alert가 사용자 Journey와 Error Budget 정책으로 완전히 연결되지는 않았습니다.

1. 제품 담당자와 Critical Journey를 3~5개 선정합니다.
2. Valid Event와 Good Event를 정확히 정의합니다.
3. Recording Rule로 SLI를 계산합니다.
4. 28일 SLO Dashboard와 Burn-rate Alert를 만듭니다.
5. Alert에 Owner, Runbook과 영향 Journey를 붙입니다.
6. Rollout Promotion과 Error Budget 상태를 연결합니다.

---

## 11. Anti-pattern

- CPU 사용률을 SLO로 부릅니다.
- 근거 없이 모든 서비스에 99.99%를 설정합니다.
- 전체 Endpoint 평균으로 핵심 API를 가립니다.
- Metric 누락을 성공으로 계산합니다.
- SLO를 평가 지표나 처벌 수단으로 사용합니다.
- Budget이 소진돼도 Release 정책이 변하지 않습니다.

---

## 12. 완료 기준

- [ ] Critical Journey마다 Owner와 SLI가 있습니다.
- [ ] Good·Valid·Bad Event 정의가 Query로 재현됩니다.
- [ ] Metric 누락과 낮은 Traffic 처리가 명시돼 있습니다.
- [ ] Fast·Slow Burn Alert가 Test Incident를 탐지합니다.
- [ ] Alert가 Dashboard와 Runbook으로 연결됩니다.
- [ ] Error Budget 상태가 배포와 신뢰성 투자에 영향을 줍니다.
- [ ] 분기마다 SLO의 유용성과 목표를 Review합니다.

---

# Reference

- [Google SRE Workbook - Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Google SRE Workbook - Error Budget Policy](https://sre.google/workbook/error-budget-policy/)
- [[Alertmanager와 Synthetic Monitoring]]
- [[Argo Rollouts Blue-Green 배포]]
- [[k6 부하 테스트와 성능 검증]]
