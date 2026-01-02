---
id: Embabel
started: 2026-01-02
tags:
  - ✅DONE
group:
  - "[[AI]]"
---
# Embabel: JVM 기반 고수준 AI 에이전트 프레임워크
Embabel은 Spring 프레임워크의 창시자인 Rod Johnson이 주도하여 개발 중인 JVM 기반의 차세대 AI 에이전트 프레임워크입니다. LangChain4j나 Spring AI가 모델 연동과 단순 체인 구성에 집중한다면, Embabel은 **"자율적인 에이전트의 행동과 목표 달성(Goal-Oriented)"** 을 자바 개발자에게 익숙한 방식으로 추상화하는 데 집중합니다.
## 1. Embabel의 핵심 차별점
- **GOAP (Goal-Oriented Action Planning)**: 에이전트가 수행할 순서(Workflow)를 개발자가 일일이 코딩하는 대신, 에이전트가 현재 상태와 가용 '행동(Action)'을 분석하여 목표(Goal)를 달성하기 위한 최적의 시퀀스를 스스로 계획합니다.
- **Strongly Typed AI Interop**: 모든 LLM 인터렉션이 자바의 강한 타입 시스템 안에서 관리됩니다. 컴파일 타임 체크와 IDE 지원을 완벽하게 누릴 수 있습니다.
- **Spring AI Integration**: 저수준의 모델 연동은 Spring AI를 기반으로 하되, 에이전트 모델링은 고수준의 Embabel API를 사용합니다.
- **Native Knowledge Context**: 에이전트에게 지식을 주입하는 과정(RAG)이 프레임워크 내부에 통합되어 있어, 별도의 복잡한 파이프라인 구축 없이도 지식 기반 에이전트를 만들 수 있습니다.
---
## 2. 핵심 아키텍처 컴포넌트
### A. Agent
에이전트는 단순히 모델을 호출하는 클라이언트가 아니라, 특정한 '역할'과 '지식'을 가진 실체입니다.
### B. Goal
에이전트가 최종적으로 달성해야 하는 목표 상태를 정의합니다.
### C. Action
에이전트가 목표 달성을 위해 취할 수 있는 구체적인 수단(Java 메서드 수준의 도구)입니다.
### D. Condition
행동이 수행되기 위해 만족해야 하거나, 행동 결과로 변화하는 세계의 상태를 정의합니다.

---
## 3. 예제: 스마트 고객 지원 에이전트
이 예제는 사용자의 문제를 해결하기 위해 주문 정보를 조회하고, 환불 규정을 검토하며, 직접 조치를 취하는 **자율형 서비스 에이전트**를 구현합니다. (예시 수도코드)
### 3.1 프로젝트 설정 (build.gradle)

```gradle
dependencies {
    // Embabel Core & Spring Boot Starter
    implementation 'io.embabel:embabel-spring-boot-starter:0.1.0'
    
    // Spring AI Integration
    implementation 'org.springframework.ai:spring-ai-openai-spring-boot-starter'
    
    // Utils & Persistence
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```
### 3.2 에이전트 정의: SupportAgent.java
Embabel의 에이전트는 인터페이스 기반으로 선언됩니다.
```java
package com.example.ai.embabel.agent;

import io.embabel.annotations.*;
import io.embabel.api.Agent;

/**
 * 선언적 에이전트 정의.
 * @Persona를 통해 AI의 역할과 성격을 부여합니다.
 */
@Persona("당신은 고객 지원 전문 AI 에이전트입니다. 정중하고 효율적으로 문제를 해결하세요.")
public interface SupportAgent extends Agent {

    /**
     * 사용자의 질문에 답하거나 문제를 해결하기 위해 자율적으로 계획을 세웁니다.
     */
    @Goal("사용자의 고객 지원 요청에 대해 최적의 해결책을 제시하고 실행하십시오.")
    String resolveSupportRequest(@Input String userQuery);
    
    /**
     * 특정 감정을 표현하며 인사하는 메시지를 생성합니다.
     */
    @Goal("사용자에게 친절한 인사를 건네십시오.")
    String welcomeCustomer(@Input String customerName);
}
```
### 3.3 에이전트 행동 구현: CustomerActions.java
에이전트가 목표를 달성하기 위해 사용할 수 있는 '도구'들입니다.
```java
package com.example.ai.embabel.actions;

import io.embabel.annotations.Action;
import io.embabel.annotations.Description;
import org.springframework.stereotype.Component;
import lombok.extern.slf4j.Slf4j;

/**
 * 에이전트가 실행할 수 있는 행동들을 정의합니다.
 * GOAP 엔진은 이 행동들의 @Description을 보고 적절한 시점에 실행합니다.
 */
@Component
@Slf4j
public class CustomerActions {

    @Action
    @Description("특정 주문 번호에 대한 상세 내역 및 배송 상태를 조회합니다.")
    public String getOrderDetails(String orderId) {
        log.info("주문 조회 액션 실행: ID={}", orderId);
        // 실제 DB 조회 로직 대체
        return String.format("주문번호 %s는 현재 '배송 중'이며, 품목은 'Java 개발자 키트'입니다.", orderId);
    }

    @Action
    @Description("고객의 등급에 따른 비밀 할인 쿠폰을 발행합니다.")
    public String issueDiscountCoupon(String customerId) {
        log.info("쿠폰 발행 액션 실행: Customer={}", customerId);
        return "15% 할인 쿠폰 [JAVA-MASTER-2026]이 발행되었습니다.";
    }

    @Action
    @Description("고객의 불만 사항을 정식 지원 티켓으로 등록합니다.")
    public void createSupportTicket(String customerId, String detail) {
        log.info("티켓 등록 액션 실행: CS-{}", System.currentTimeMillis());
    }
}
```
### 3.4 지식 컨텍스트 구성: PolicyContext.java
에이전트가 참고할 정적 지식(환불 정책 등)을 주입합니다.
```java
package com.example.ai.embabel.context;

import io.embabel.api.KnowledgeContext;
import io.embabel.api.KnowledgeSource;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class KnowledgeBaseConfig {

    /**
     * 에이전트가 상식 외에 알아야 할 특정 지식(환불 규정 등)을 주입합니다.
     */
    @Bean
    public KnowledgeContext supportKnowledgeContext() {
        return KnowledgeContext.builder()
                .name("사내 서비스 규정")
                .addSource(KnowledgeSource.fromText("환불은 구매 후 7일 이내에만 가능하며, 단순 변심의 경우 배송비는 고객 부담입니다."))
                .addSource(KnowledgeSource.fromText("VIP 등급 고객은 모든 배송비가 무료입니다."))
                .build();
    }
}
```
### 3.5 프레임워크 설정: EmbabelConfig.java
Embabel 에이전트와 이벤트를 관리하는 중앙 설정입니다.
```java
package com.example.ai.embabel.config;

import com.example.ai.embabel.agent.SupportAgent;
import io.embabel.api.Embabel;
import io.embabel.api.EmbabelFactory;
import io.embabel.spring.config.EnableEmbabel;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableEmbabel // Embabel의 어노테이션 프로세싱을 활성화합니다.
public class EmbabelAppConfig {

    @Bean
    public Embabel embabel() {
        // 실제 운영 환경에서는 OpenAiChatModel 등을 기반으로 팩토리를 구성합니다.
        return EmbabelFactory.createDefault();
    }

    @Bean
    public SupportAgent supportAgent(Embabel embabel) {
        // Embabel 엔진이 인터페이스의 구현체를 동적으로 생성합니다.
        return embabel.createAgent(SupportAgent.class);
    }
}
```
### 3.6 비즈니스 서비스 통합: SupportService.java
에이전트를 실제 비즈니스 로직에 통합합니다.
```java
package com.example.ai.embabel.service;

import com.example.ai.embabel.agent.SupportAgent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@Slf4j
public class SupportService {

    private final SupportAgent supportAgent;

    public String handleCustomerInquiry(String customerName, String query) {
        log.info("고객 요청 처리 시작: {}", query);
        
        // 1. 단순 인사 (전형적인 답변)
        String welcome = supportAgent.welcomeCustomer(customerName);
        log.info("Agent 인사: {}", welcome);

        // 2. 자율적 문제 해결 (GOAP 작동)
        // 이 메서드가 호출되면 에이전트는 질문을 분석하고, 
        // 필요하다면 CustomerActions의 메서드들을 스스로 호출하여 정보를 수집한 뒤 답합니다.
        String solution = supportAgent.resolveSupportRequest(query);
        
        return welcome + "\n\n[해결책]\n" + solution;
    }
}
```
### 3.7 에이전트 컨트롤러: SupportController.java
```java
package com.example.ai.embabel.controller;

import com.example.ai.embabel.service.SupportService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/support")
@RequiredArgsConstructor
public class SupportController {

    private final SupportService supportService;

    @PostMapping("/chat")
    public String chat(@RequestParam String name, @RequestBody String message) {
        // 예: "내 주문 배송 상태 알려주고, 늦어서 미안하니까 쿠폰 하나만 줘"
        // 에이전트는 getOrderDetails와 issueDiscountCoupon을 순서대로 호출하는 계획을 세웁니다.
        return supportService.handleCustomerInquiry(name, message);
    }
}
```

---
## 4. Embabel 활용 팁
### A. GOAP 기반 설계의 사고방식
전통적인 프로그래밍은 `if-else`나 `switch`로 흐름을 제어하지만, Embabel에서는 **"에이전트에게 어떤 능력을 줄 것인가(Action)"** 와 **"에이전트가 도달해야 할 최종 상태는 무엇인가(Goal)"** 만을 정의합니다. 에이전트가 계획을 세우는 과정을 신뢰하되, 행동의 전후 상태(Condition)를 명확히 정의하는 것이 성공의 핵심입니다.
### B. 타입 안전성과 리팩토링
Embabel을 사용하면 LLM 응답을 파싱하기 위해 JSON 스키마를 직접 다루는 고통에서 벗어날 수 있습니다. 자바의 `Record`나 `DTO`를 반환 타입으로 지정하면 Embabel이 이를 보장하므로, 프레임워크를 믿고 강한 타입 기반의 설계를 하세요.
### C. 에이전트 테스트 전략
Embabel은 에이전트의 '계획 능력'을 테스트하기 위한 전용 도구를 제공합니다. 실제 모델을 호출하는 통합 테스트도 중요하지만, 에이전트에게 가상의 상황을 주고 예상되는 행동 시퀀스(Plan)가 생성되는지 유닛 테스트 수준에서 검증하는 것이 효율적입니다.
### D. LangChain4j와의 하이브리드 운영
단순한 텍스트 변환이나 RAG 검색이 주 목적인 영역은 LangChain4j가 더 가볍고 효율적일 수 있습니다. 반면, 복잡한 비즈니스 규칙과 자율적인 판단이 필요한 영역에만 Embabel 에이전트를 도입하는 하이브리드 전략을 고려할 수 있습니다.

# Reference
- [Embabel 공식 GitHub](https://github.com/embabel/embabel-agent)
- [Spring AI Foundation](https://spring.io/projects/spring-ai)
- [Goal-Oriented Action Planning (GOAP) 기초](https://en.wikipedia.org/wiki/Goal-oriented_action_planning)