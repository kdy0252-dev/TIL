---
id: Strangler Fig Pattern & Feature Toggle
started: 2026-02-06
tags:
  - Architecture
  - Modernization
  - DevOps
  - Deployment-Pattern
group:
  - "[[Design-Pattern]]"
---

# 시스템 현대화와 점진적 배포 가이드 (Strangler Fig & Feature Toggle)

## 1. 개요 (Overview)
대규모 레거시 시스템을 한 번에 새로운 아키텍처(예: MSA)로 교체하는 '빅뱅(Big Bang)' 방식은 매우 높은 리스크를 동반한다. 이를 극복하기 위해 제안된 핵심적인 전략이 **Strangler Fig Pattern**과 **Feature Toggle**이다. 두 패턴은 모두 시스템의 중단 없이 점진적으로 변화를 이끌어내고, 안전하게 기능을 검증하는 데 목적이 있다.

---

## 2. Strangler Fig Pattern
**Strangler Fig Pattern(교살자 무화과 패턴)**은 거대한 나무를 감싸며 자라 결국 원래의 나무를 대체하는 무화과나무의 특징에서 유래했다. 레거시 시스템을 한 번에 바꾸는 대신, 특정 기능을 하나씩 새로운 서비스로 이전하며 점진적으로 레거시를 대체하는 방식이다.

### 2.1 동작 원리
1. **Facade(Proxy) 계층 도입**: 클라이언트와 서버 사이에 요청을 가로챌 수 있는 게이트웨이 또는 프록시를 배치한다.
2. **신규 기능 구현**: 레거시의 특정 기능을 분리하여 새로운 서비스(New System)로 개발하고 배포한다.
3. **트래픽 전환**: Facade 계층에서 특정 경로의 요청을 레거시가 아닌 신규 서비스로 라우팅한다.
4. **반복 및 제거**: 모든 기능이 이전될 때까지 과정을 반복하고, 마지막에 레거시 시스템을 제거한다.

### 2.2 장점
- **리스크 분산**: 작은 단위로 배포하므로 장애 발생 시 영향 범위가 제한적이다.
- **점진적 가치 전달**: 전체 시스템이 완성될 때까지 기다릴 필요 없이, 완성된 기능부터 즉시 비즈니스 가치를 제공한다.
- **아키텍처 유연성**: 레거시와 다른 언어, 프레임워크를 신규 서비스에 적용할 수 있다.

---

## 3. Feature Toggle (Feature Flag)
**Feature Toggle**은 코드의 변경 없이 실행 중에 기능을 동적으로 켜거나 끌 수 있는(On/Off) 기법이다. 이는 '배포(Deployment)'와 '출시(Release)'를 분리할 수 있게 해주는 핵심 도구이다.

### 3.1 주요 카테고리
- **Release Toggles**: 테스트 중인 기능을 운영 환경에 배포하되, 사용자에게는 노출되지 않도록 숨길 때 사용한다.
- **Experiment Toggles**: A/B 테스트와 같이 특정 사용자군에게만 기능을 노출하여 반응을 살필 때 사용한다.
- **Ops Toggles**: 시스템 부하 증가 시 특정 기능을 즉시 차단하는 'Kill Switch' 역할을 한다.
- **Permissioning Toggles**: 프리미엄 사용자나 내부 직원에게만 특정 기능을 활성화할 때 사용한다.

### 3.2 Java 활용 예시 (Spring Boot)
```java
@Service
@RequiredArgsConstructor
public class OrderService {
    private final FeatureManager featureManager; // Togglz, LaunchDarkly 등의 라이브러리 활용

    public void processOrder(Order order) {
        if (featureManager.isActive(Features.NEW_ORDER_LOGIC)) {
            // 신규 로직 처리
            processNewOrder(order);
        } else {
            // 레거시 로직 처리
            processLegacyOrder(order);
        }
    }
}
```

---

## 4. 두 패턴의 결합: 안전한 현대화 전략
Strangler Fig Pattern을 사용할 때, **Feature Toggle**을 함께 활용하면 더욱 강력한 효과를 낼 수 있다.

1. **Canary Release**: 신규 서비스로의 라우팅을 Feature Toggle로 제어하여, 전체 트래픽의 5%만 먼저 신규 시스템으로 보내 검증한다.
2. **Dark Launching**: 신규 시스템을 배포하되 UI에는 노출하지 않고, 백그라운드에서 동일한 데이터를 처리하게 하여 결과값이 레거시와 일치하는지 비교한다.
3. **즉각적인 롤백**: 신규 서비스에서 에러가 감지되면 Facade 설정 변경 없이 Toggle만 Off 하여 즉시 레거시로 복구한다.

---

## 5. 구현 시 주의사항 (Pitfalls)

### 5.1 데이터 동기화 (Data Consistency)
- 레거시와 신규 시스템이 동일한 DB를 공유하거나, 데이터가 실시간으로 동기화되어야 한다. CDC(Change Data Capture)나 이벤트 기반 동기화가 필요할 수 있다.

### 5.2 부채 관리 (Toggle Debt)
- Feature Toggle은 임시적인 코드이다. 기능이 안정화된 후에는 반드시 토글 코드를 제거하여 코드 복잡도를 낮춰야 한다.

### 5.3 서비스 결합도
- Strangler 패턴 적용 중 레거시와 신규 서비스 간의 잦은 통신으로 인해 오버헤드가 발생할 수 있으므로 설계에 유의해야 한다.

---

## 6. 결론
Strangler Fig Pattern은 **전략적 로드맵**을 제공하고, Feature Toggle은 **전술적 안전장치**를 제공한다. 이 두 가지를 적절히 혼합하여 사용하면, 끊임없이 변화하는 비즈니스 요구사항에 대응하면서도 시스템을 안정적으로 현대화할 수 있다.

---

## 7. Reference
- [Martin Fowler: StranglerFigApplication](https://martinfowler.com/bliki/StranglerFigApplication.html)
- [Martin Fowler: Feature Toggles](https://martinfowler.com/articles/feature-toggles.html)
- [Microsoft Azure: Strangler Fig pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig)

---

## Appendix: 주요 도구 및 프레임워크
- **Facade/Routing**: Nginx, Kong, Zuul, AWS CloudFront, Istio
- **Feature Management**: Unleash, Togglz, FF4J (Java), LaunchDarkly (SaaS), Flagsmith (Open Source)
