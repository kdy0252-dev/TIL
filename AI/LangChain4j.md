---
id: LangChain4j
started: 2026-01-02
tags:
  - ✅DONE
group:
  - "[[AI]]"
---
# LangChain4j: Java 개발자를 위한 LLM 오케스트레이션 가이드

LangChain4j는 자바 환경에서 거세언어모델(LLM)을 쉽고 효율적으로 통합할 수 있게 도와주는 프레임워크입니다. Java의 강력한 타입 시스템과 객체지향적 특성을 극대화하여 설계되었습니다.
## 1. LangChain4j의 핵심 철학
- **Java-Centric Implementation**: Java의 관용구와 디자인 패턴을 따릅니다.
- **AiServices**: AI 로직을 자바 인터페이스로 선언하여 선언적으로 사용합니다. 프롬프트 구성부터 응답 파싱까지 자동화합니다.
- **Modularity**: 특정 모델 제조사나 벡터 스토어에 종속되지 않는 유연한 구조를 제공합니다.
---
## 2. 주요 컴포넌트 이해

### A. AiServices
비즈니스 로직과 프롬프트 엔지니어링을 분리하는 핵심 인터페이스입니다.
### B. Language Models
- **ChatLanguageModel**: GPT-4o, Claude 등과의 대화를 처리합니다.
- **EmbeddingModel**: 텍스트를 수치형 벡터로 변환합니다.
### C. Tools (Function Calling)
AI가 외부 시스템(메서드 호출, API 등)과 상호작용하도록 권한을 부여합니다.
### D. Memory
대화의 맥락(Context)을 유지하기 위해 이전 메시지들을 관리합니다.

---
## 3. 예제
이 예제는 **사내 도우미 AI** 시나리오를 바탕으로, DB 정보 참고(RAG)와 외부 도구(Tools)를 결합한 구성을 보여줍니다.(예시 수도코드)
### 3.1 프로젝트 설정 (build.gradle)
```gradle
dependencies {
    // Core & OpenAi Integration
    implementation 'dev.langchain4j:langchain4j-spring-boot-starter:0.36.0'
    implementation 'dev.langchain4j:langchain4j-open-ai-spring-boot-starter:0.36.0'
    
    // Persistence & Vector Store
    implementation 'dev.langchain4j:langchain4j-redis:0.36.0'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'com.h2database:h2'
    
    // Utilities
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```
### 3.2 도메인 모델 (PolicyEntity.java)
DB에 저장된 정형 데이터를 AI가 활용할 수 있도록 정의합니다.
```java
package com.example.ai.guide.domain;

import jakarta.persistence.*;
import lombok.*;

/**
 * 사내 정책 정보를 저장하는 엔티티입니다.
 */
@Entity
@Table(name = "company_policies")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class PolicyEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    private String department;

    /**
     * AI가 문맥을 더 잘 파악할 수 있도록 텍스트 형태로 변환합니다.
     */
    public String toDocText() {
        return String.format("[%s 부서 정책] 주제: %s\n내용: %s", 
            department, title, content);
    }
}
```
### 3.3 데이터 접근 계층 (PolicyRepository.java)
```java
package com.example.ai.guide.repository;

import com.example.ai.guide.domain.PolicyEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface PolicyRepository extends JpaRepository<PolicyEntity, Long> {
}
```
### 3.4 AI 에이전트 인터페이스 (CompanyAssistant.java)
AiServices를 통해 생성될 AI 엔진의 청사진입니다.
```java
package com.example.ai.guide.service;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;

/**
 * AI와 통신하기 위한 선언적 인터페이스입니다.
 */
public interface CompanyAssistant {

    @SystemMessage({
        "당신은 사내 도우미 AI입니다.",
        "제공된 정책 정보(RAG)를 바탕으로 정확하게 답변하세요.",
        "직원의 개인 정보가 필요한 경우 할당된 도구(Tools)를 사용하세요.",
        "답변할 수 없는 경우 담당 부서를 안내하세요."
    })
    String answer(String userMessage);

    @UserMessage("안녕하세요 {{name}}님, 무엇을 도와드릴까요?")
    String greet(@V("name") String name);
}
```
### 3.5 외부 도구 연동 (InternalTools.java)
AI가 실시간 데이터를 조회할 수 있도록 허용하는 자바 메서드들입니다.
```java
package com.example.ai.guide.tools;

import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Component
@Slf4j
public class InternalTools {

    @Tool("현재 사용자의 잔여 연차 일수를 확인합니다.")
    public int getVacationBalance(String userName) {
        log.info("DB 조회: {} 님의 연차 잔여량 확인", userName);
        // 실제 인적 자원 관리 시스템 연동 로직
        return 12;
    }

    @Tool("특정 건물의 시설 관리팀 연락처를 조회합니다.")
    public String getFacilityContact(String buildingName) {
        log.info("연락처 조회: {}", buildingName);
        return "02-987-6543 (담당: 김철수)";
    }
}
```
### 3.6 가상 스토어 및 인프라 설정 (LangChain4jConfig.java)
모든 컴포넌트를 조립하여 AI 엔진을 구동 가능한 상태로 만듭니다.
```java
package com.example.ai.guide.config;

import com.example.ai.guide.service.CompanyAssistant;
import com.example.ai.guide.tools.InternalTools;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.model.openai.OpenAiEmbeddingModel;
import dev.langchain4j.rag.DefaultRetrievalAugmentor;
import dev.langchain4j.rag.content.retriever.ContentRetriever;
import dev.langchain4j.rag.content.retriever.EmbeddingStoreContentRetriever;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class LangChain4jConfig {

    @Bean
    ChatLanguageModel chatLanguageModel() {
        return OpenAiChatModel.builder()
                .apiKey(System.getenv("OPENAI_API_KEY"))
                .modelName("gpt-4o")
                .temperature(0.0) // 일관성 있는 정책 답변을 위해 0 설정
                .build();
    }

    @Bean
    EmbeddingModel embeddingModel() {
        return OpenAiEmbeddingModel.builder()
                .apiKey(System.getenv("OPENAI_API_KEY"))
                .modelName("text-embedding-3-small")
                .build();
    }

    @Bean
    EmbeddingStore<TextSegment> embeddingStore() {
        // 인메모리 저장소 사용 (실무에선 Redis나 PGVector 권장)
        return new InMemoryEmbeddingStore<>();
    }

    @Bean
    ContentRetriever contentRetriever(EmbeddingStore<TextSegment> embeddingStore, EmbeddingModel embeddingModel) {
        // 벡터 저장소에서 가장 유사한 정책 3개를 가져오는 설정
        return EmbeddingStoreContentRetriever.builder()
                .embeddingStore(embeddingStore)
                .embeddingModel(embeddingModel)
                .maxResults(3)
                .build();
    }

    @Bean
    CompanyAssistant companyAssistant(
            ChatLanguageModel chatModel,
            ContentRetriever contentRetriever,
            InternalTools tools) {
        
        // 핵심 서비스 조립: 모델 + RAG(Retriever) + 도구(Tools) + 메모리
        return AiServices.builder(CompanyAssistant.class)
                .chatLanguageModel(chatModel)
                .contentRetriever(contentRetriever)
                .tools(tools)
                .chatMemory(MessageWindowChatMemory.withMaxMessages(10))
                .build();
    }
}
```
### 3.7 정책 데이터 관리 서비스 (PolicyService.java)
DB의 데이터를 벡터 저장소로 인제스션(RAG 준비)하는 역할입니다.
```java
package com.example.ai.guide.service;

import com.example.ai.guide.domain.PolicyEntity;
import com.example.ai.guide.repository.PolicyRepository;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class PolicyService {

    private final PolicyRepository policyRepository;
    private final EmbeddingStore<TextSegment> embeddingStore;
    private final EmbeddingModel embeddingModel;

    /**
     * DB 데이터를 벡터 저장소로 동기화합니다.
     */
    @Transactional(readOnly = true)
    public void ingestAllPolicies() {
        List<PolicyEntity> policies = policyRepository.findAll();
        
        List<Document> documents = policies.stream()
                .map(p -> Document.from(p.toDocText(), Metadata.from("id", p.getId())))
                .collect(Collectors.toList());

        EmbeddingStoreIngestor.builder()
                .embeddingModel(embeddingModel)
                .embeddingStore(embeddingStore)
                .build()
                .ingest(documents);
    }
}
```
### 3.8 컨트롤러 (CompanyAiController.java)
사용자 인터페이스(REST API)를 제공합니다.
```java
package com.example.ai.guide.controller;

import com.example.ai.guide.service.CompanyAssistant;
import com.example.ai.guide.service.PolicyService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/ai")
@RequiredArgsConstructor
public class CompanyAiController {

    private final CompanyAssistant assistant;
    private final PolicyService policyService;

    @PostMapping("/sync-policies")
    public String sync() {
        policyService.ingestAllPolicies();
        return "정책 데이터 동기화가 완료되었습니다.";
    }

    @GetMapping("/chat")
    public String chat(@RequestParam String message) {
        // 사용자가 질문하면 RAG와 Tool이 자동 작동
        return assistant.answer(message);
    }

    @GetMapping("/hello/{name}")
    public String hello(@PathVariable String name) {
        return assistant.greet(name);
    }
}
```
## 4. LangChain4j 선택 시 고려사항
### A. 선언적 API 사용
복잡한 프롬프트 구성을 코드에서 직접 하지 말고, `@SystemMessage`와 인터페이스를 활용할 수 있습니다.
### B. 로깅 및 모니터링
`.logRequests(true)`와 `.logResponses(true)`를 활성화하여 AI와의 통신 내역을 투명하게 관리할 수 있습니다.
### C. 에러 핸들링
LLM 서버는 간헐적인 장애가 발생할 수 있으므로, Spring Retry 등을 활용한 재시도 전략이 필수적입니다.

# Reference
- [LangChain4j 공식 문서](https://docs.langchain4j.dev/)
- [LangChain4j GitHub](https://github.com/langchain4j/langchain4j)
- [LangChain4j GitHub Examples](https://github.com/langchain4j/langchain4j-examples)
- [LangChain4j RAG Documentation](https://docs.langchain4j.dev/tutorials/rag)
- [PGVector with LangChain4j](https://docs.langchain4j.dev/integrations/embedding-stores/pgvector)
- [LangChain4j Filter Documentation](https://docs.langchain4j.dev/tutorials/filters)
- [AiServices 활용 팁](https://docs.langchain4j.dev/tutorials/ai-services)