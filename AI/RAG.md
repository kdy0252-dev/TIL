---
id: RAG
started: 2026-01-02
tags:
  - ✅DONE
group:
  - "[[AI]]"
---
# RAG (Retrieval-Augmented Generation)
RAG(검색 증강 생성)는 거대언어모델(LLM)이 가진 두 가지 치명적인 한계인 **환각(Hallucination)** 과 **데이터의 시의성(최신 데이터 부재)** 을 해결하기 위한 가장 실질적인 기술입니다. 모델을 재학습(Fine-tuning)시키지 않고도, 외부의 신뢰할 수 있는 데이터를 검색하여 LLM이 답변의 근거로 활용하게 만듭니다.
## 1. RAG 핵심 아키텍처: 3-Step Workflow
RAG 프로세스는 크게 세 단계로 데이터가 흐릅니다.
### A. 인제스션 (Ingestion) - 지식의 파이프라인
데이터를 검색 가능한 벡터 형태로 가공하여 보관하는 정적 프로세스입니다.
1.  **Extract**: PDF, DB, Wiki 등에서 텍스트 추출.
2.  **Chunk**: 텍스트를 의미 있는 작은 단위로 분할.
3.  **Embed**: 분할된 텍스트를 고차원 숫자 벡터로 변환.
4.  **Store**: 벡터 데이터베이스에 저장.
### B. 검색 (Retrieval) - 맥락의 탐색
사용자의 질문과 가장 관련 있는 정보를 찾는 동적 프로세스입니다.
1.  **Vectorize**: 질문을 임베딩 모델을 통해 벡터화.
2.  **Search**: 질문 벡터와 데이터베이스 내 벡터 간의 유사도(Cosine Similarity 등) 계산.
3.  **Filter**: 가장 유사한 상위 K개의 텍스트 조각(Context)을 추출.
### C. 생성 (Generation) - 답변의 완성
추출된 정보를 바탕으로 최종 응답을 생성하는 단계입니다.
1.  **Augment**: 프롬프트 내에 "다음 정보를 참고하여 답하라"는 지시와 함께 검색된 Context 주입.
2.  **Call**: LLM 호출 및 답변 수신.
---
## 2. 실전 구현 전략
### 2.1 청킹 전략 (Chunking Strategies)
단순히 글자 수로 자르는 것이 아니라, 문맥이 보존되도록 자르는 것이 검색 품질을 결정합니다.
-   **Fixed-size Chunking**: 가장 단순하나 문맥이 잘릴 위험이 큼.
-   **Recursive Character Splitting**: 문단, 문장 구분자를 활용하여 의미 단위로 분할 (권장).
-   **Semantic Chunking**: 임베딩 간의 거리 차이를 감지하여 주제가 바뀌는 지점에서 분할.
### 2.2 검색 최적화 (Advanced Retrieval)
단일 벡터 검색만으로는 부족한 경우가 많습니다.
-   **Hybrid Search**: 벡터(시맨틱) 검색과 전통적인 키워드(BM25) 검색을 결합.
-   **Re-ranking**: 상위 20~50개를 먼저 찾고, 더 정교한 모델로 다시 순위를 매겨 최상위 5개만 선별.
-   **Query Expansion**: 질문을 LLM이 다시 쓰게 하여 검색 성공률 극대화.
---
## 3. 예제: 지식 베이스 RAG
이 예제는 자바 환경에서 LangChain4j를 활용하여 기업 내부 문서를 벡터화하고 검색하는 전체 파이프라인을 보여줍니다.
### 3.1 프로젝트 설정 (build.gradle)
```gradle
dependencies {
    // LangChain4j RAG Helpers
    implementation 'dev.langchain4j:langchain4j-spring-boot-starter:0.36.0'
    implementation 'dev.langchain4j:langchain4j-open-ai-spring-boot-starter:0.36.0'
    
    // Vector Store (Qdrant, Pinecone, Redis 등)
    implementation 'dev.langchain4j:langchain4j-qdrant:0.36.0'
    
    // Core & Persistence
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'com.h2database:h2'
    compileOnly 'org.projectlombok:lombok'
    annotationProcessor 'org.projectlombok:lombok'
}
```
### 3.2 도메인 엔티티: KnowledgeDocument.java
원본 데이터를 관리하는 DB 엔티티입니다.
```java
package com.example.ai.rag.domain;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "knowledge_documents")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class KnowledgeDocument {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Column(columnDefinition = "TEXT")
    private String content;

    private String category;

    private LocalDateTime updatedAt;

    public String toFullText() {
        return String.format("[%s] %s\n%s", category, title, content);
    }
}
```
### 3.3 데이터 인제스션 서비스: KnowledgeIngestor.java
데이터를 벡터화하여 저장하는 핵심 서비스입니다.
```java
package com.example.ai.rag.service;

import com.example.ai.rag.domain.KnowledgeDocument;
import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Slf4j
public class KnowledgeIngestor {

    private final EmbeddingStore<dev.langchain4j.data.segment.TextSegment> embeddingStore;
    private final EmbeddingModel embeddingModel;

    /**
     * 리포지토리에서 가져온 문서 리스트를 벡터 저장소에 인제스션합니다.
     */
    public void ingest(List<KnowledgeDocument> dbDocs) {
        log.info("RAG 인제스션 시작: {} 건", dbDocs.size());

        List<Document> documents = dbDocs.stream()
                .map(doc -> Document.from(
                    doc.toFullText(), 
                    Metadata.from("doc_id", doc.getId())
                            .add("category", doc.getCategory())
                ))
                .collect(Collectors.toList());

        // 1. Recursive Splitter: 문맥 보존을 위해 문장/문단 단위 중첩 분할
        // 2. Embedding Model: 텍스트를 벡터로 변환
        // 3. Embedding Store: 결과 저장
        EmbeddingStoreIngestor ingestor = EmbeddingStoreIngestor.builder()
                .documentSplitter(DocumentSplitters.recursive(1000, 100))
                .embeddingModel(embeddingModel)
                .embeddingStore(embeddingStore)
                .build();

        ingestor.ingest(documents);
        log.info("RAG 인제스션 완료");
    }
}
```
### 3.4 AI 인터페이스 정의: KnowledgeAssistant.java
LLM과의 인터랙션을 정의합니다.
```java
package com.example.ai.rag.service;

import dev.langchain4j.service.SystemMessage;

public interface KnowledgeAssistant {

    @SystemMessage({
        "당신은 사내 지식 베이스 도우미입니다.",
        "제공된 맥락(Context) 정보만을 근거로 답변하세요.",
        "만약 맥락 정보에 답이 없으면 '죄송하지만 관련 정보를 사내 지식 베이스에서 찾을 수 없습니다'라고 답하세요.",
        "절대로 지어내지 마십시오."
    })
    String answer(String userQuery);
}
```
### 3.5 검색 및 인프라 설정: RAGConfig.java
RAG의 핵심인 '검색기(Retriever)'를 설정하고 AI 서비스를 조립합니다.
```java
package com.example.ai.rag.config;

import com.example.ai.rag.service.KnowledgeAssistant;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.model.openai.OpenAiEmbeddingModel;
import dev.langchain4j.rag.content.retriever.ContentRetriever;
import dev.langchain4j.rag.content.retriever.EmbeddingStoreContentRetriever;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RAGConfig {

    @Bean
    ChatLanguageModel chatLanguageModel() {
        return OpenAiChatModel.builder()
                .apiKey(System.getenv("OPENAI_API_KEY"))
                .modelName("gpt-4o")
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
        // 인메모리 저장소 (개발/테스트용)
        return new InMemoryEmbeddingStore<>();
    }

    @Bean
    ContentRetriever contentRetriever(EmbeddingStore<TextSegment> embeddingStore, EmbeddingModel embeddingModel) {
        // [핵심] 검색기 설정: 상위 3개의 가장 유사한 결과만 추출
        return EmbeddingStoreContentRetriever.builder()
                .embeddingStore(embeddingStore)
                .embeddingModel(embeddingModel)
                .maxResults(3)
                .minScore(0.7) // 유사도 70% 이상만 컨텍스트로 채택
                .build();
    }

    @Bean
    KnowledgeAssistant knowledgeAssistant(
            ChatLanguageModel chatModel,
            ContentRetriever contentRetriever) {
        
        // 검색 전용 증강 엔진 조립
        return AiServices.builder(KnowledgeAssistant.class)
                .chatLanguageModel(chatModel)
                .contentRetriever(contentRetriever)
                .build();
    }
}
```
### 3.6 통합 서비스 및 엔드포인트: RAGService.java
```java
package com.example.ai.rag.service;

import com.example.ai.rag.repository.KnowledgeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;

@Service
@RestController
@RequestMapping("/api/rag")
@RequiredArgsConstructor
public class RAGService {

    private final KnowledgeAssistant assistant;
    private final KnowledgeIngestor ingestor;
    private final KnowledgeRepository repository;

    /**
     * DB의 모든 지식 데이터를 벡터 스토어로 동기화합니다.
     */
    @PostMapping("/sync")
    public String sync() {
        ingestor.ingest(repository.findAll());
        return "Knowledge sync completed.";
    }

    /**
     * 질문에 대해 RAG 파이프라인을 작동시킵니다.
     */
    @GetMapping("/ask")
    public String ask(@RequestParam String q) {
        // 1. q를 벡터화
        // 2. 벡터 저장소 검색 (Context 추출)
        // 3. LLM에게 Context + q 전달 및 답변 생성
        return assistant.answer(q);
    }
}
```

---
## 4. RAG 활용 팁
### A. 가비지 인, 가비지 아웃 (GIGO)
아무리 고성능 모델을 써도 인제스션된 텍스트가 지저분하면 답변 품질이 떨어집니다. HTML 태그, 불필요한 특수문자 등을 사전에 정제하는 **전처리 과정**에 리소스의 50%를 투자하세요.
### B. 메타데이터 필터링
사용자별 권한(예: 부서별 문서 접근 제한)이 필요한 경우, 검색 단계에서 `Metadata Filter`를 사용하여 권한이 없는 데이터가 LLM에게 전달되지 않도록 차단해야 합니다.
### C. 결과 평가 (Evaluation)
RAG 시스템은 '검색이 잘 되었는가'와 '생성이 잘 되었는가'를 별도로 평가해야 합니다. **RAGAS**와 같은 프레임워크를 활용하여 Faithfulness(성실성), Relevancy(관련성) 지표를 측정하는 것이 좋습니다.

# Reference
- [LangChain4j RAG 가이드](https://docs.langchain4j.dev/tutorials/rag)
- [Vector DB 비교 (Qdrant vs Pinecone vs Milvus)](https://qdrant.tech/benchmarks/)
- [Chunking 전략 심화 가이드](https://www.pinecone.io/learn/chunking-strategies/)