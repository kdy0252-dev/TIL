---
id: MCP
started: 2026-01-02
tags:
  - ✅DONE
group:
  - "[[AI]]"
---
# MCP (Model Context Protocol)ㅊ
MCP(Model Context Protocol)는 Anthropic에서 발표한 개방형 표준으로, AI 모델(지능)이 외부의 데이터(리소스)와 도구(기능)에 접근할 수 있도록 돕는 **"AI판 USB 인터페이스"** 와 같습니다. 기존의 파편화된 Tool/Function Calling 방식을 규격화하여, 에이전트가 어떤 환경에서도 쉽고 안전하게 외부 세계와 소통하게 합니다.
## 1. MCP 아키텍처: Client-Server Model
MCP는 고전적인 클라이언트-서버 구조를 따릅니다.
### A. MCP Client (The User of Tools)
- 모델과 직접 통신하며, 모델이 특정 도구가 필요하다고 할 때 MCP Server에 요청을 보냅니다.
- 예: Claude Desktop, LangChain4j 앱, 사내 AI 비서 앱.
### B. MCP Server (The Provider of Tools)
- 실제 데이터베이스, 로컬 파일 시스템, 또는 외부 API(Atlassian, Slack 등)와 직접 연동됩니다.
- 모델에게 가용한 **Tools(함수)**, **Resources(데이터)**, **Prompts(템플릿)** 를 노출합니다.
### C. Transport Layer
- 클라이언트와 서버가 대화하는 통로입니다.
- **Stdio**: 부모/자식 프로세스 간의 표준 입출력 통신 (가장 흔함).
- **HTTP/SSE**: 네트워크를 통한 스트리밍 통신 (원격 서버용).

---
## 2. MCP의 핵심 추상화들
1.  **Resources**: 모델이 '읽을' 수 있는 정적/동적 데이터. (고객 정보 조회 등)
2.  **Tools**: 모델이 '실행'할 수 있는 함수. (PR 생성, 메시지 전송 등)
3.  **Prompts**: 모델에게 구체적인 미션을 부여하는 재사용 가능한 템플릿.
---
## 3. 실전 예제: 자율 장애 복구 에이전트
이 시나리오는 **"운영 서버 장애 감지 -> 로그 분석 -> Atlassian(Bitbucket) HotFix PR 생성 -> MS Teams 통지"** 로 이어지는 전 과정을 MCP 서버와 클라이언트로 구현합니다. (예시 수도 코드)
### 3.1 프로젝트 설정 (build.gradle)
```gradle
dependencies {
    // Spring AI MCP SDK (Spring AI 1.0.0-M5+ 기반)
    implementation 'org.springframework.ai:spring-ai-mcp-spring-boot-starter'
    
    // Remote API Clients
    implementation 'com.atlassian.bitbucket:bitbucket-rest:x.x.x'
    implementation 'com.microsoft.graph:microsoft-graph:x.x.x'
    
    // LangChain4j (Client Orchestration)
    implementation 'dev.langchain4j:langchain4j-spring-boot-starter:0.36.0'
}
```
### 3.2 MCP Server: 장애 대응 도구 제공 (IncidentMcpServer.java)
서버는 AI가 사용할 수 있는 '능력'들을 정의하고 노출합니다.
```java
package com.example.ai.mcp.server;

import io.modelcontextprotocol.annotations.McpTool;
import io.modelcontextprotocol.annotations.McpResource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * AI 모델에게 노출될 MCP 서버 도구들입니다.
 */
@Service
@Slf4j
public class IncidentMcpServer {

    /**
     * AI가 원격 서버의 로그를 읽을 수 있게 리소스로 제공합니다.
     */
    @McpResource("resource://monitoring/server-logs")
    public String getServerLogs() {
        return "[ERROR] 13:45:01 NullPointerException at PaymentService.java:125\n" +
               "Cause: Request parameter 'orderId' is missing.";
    }

    /**
     * AI가 Bitbucket에 HotFix PR을 생성하게 합니다.
     */
    @McpTool(description = "Bitbucket 저장소에 HotFix PR을 생성합니다.")
    public String createHotFixPR(String repo, String branch, String commitMsg) {
        log.info("Bitbucket PR 생성 요청: repo={}, msg={}", repo, commitMsg);
        // Bitbucket API 연동 로직
        String prUrl = "https://bitbucket.org/myorg/" + repo + "/pull-requests/101";
        return "PR 생성 완료: " + prUrl;
    }

    /**
     * AI가 MS Teams로 긴급 상황을 전송하게 합니다.
     */
    @McpTool(description = "MS Teams 특정 채널로 긴급 시스템 알림을 전송합니다.")
    public void sendTeamsAlert(String message, String urgency) {
        log.info("Teams 알림 전송 (Ugency: {}): {}", urgency, message);
        // MS Graph API 연동 로직
    }
}
```
### 3.3 MCP Client: AI 서비스 정의 (IncidentResponseAgent.java)
클라이언트는 모델을 조립하고 MCP 서버를 호출할 수 있는 능력을 부여합니다.
```java
package com.example.ai.mcp.client;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;

/**
 * 장애 대응을 전담하는 지능형 클라이언트 인터페이스입니다.
 */
public interface IncidentResponseAgent {

    @SystemMessage({
        "당신은 사내 SRE(Site Reliability Engineering) 담당 AI입니다.",
        "서버 로그를 분석하여 수정 코드를 제안하고, 승인 없이 PR을 생성할 수 있습니다.",
        "작업 완료 후에는 반드시 팀즈 채널에 상세 내용을 공유하세요."
    })
    String handleIncident(String errorReport);
}
```
### 3.4 MCP 클라이언트 엔진 설정 (McpConfig.java)
MCP 서버와 클라이언트를 통신 가능하게 연결하는 핵심 설정입니다.
```java
package com.example.ai.mcp.client.config;

import com.example.ai.mcp.client.IncidentResponseAgent;
import dev.langchain4j.model.chat.ChatLanguageModel;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.service.AiServices;
import org.springframework.ai.mcp.client.McpClient;
import org.springframework.ai.mcp.client.stdio.StdioMcpClient;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class McpConfig {

    @Bean
    ChatLanguageModel chatModel() {
        return OpenAiChatModel.withApiKey(System.getenv("OPENAI_API_KEY"));
    }

    /**
     * MCP 서버를 프로세스 내부 혹은 외부(Stdio)에서 실행하여 클라이언트에 연결합니다.
     */
    @Bean
    McpClient mcpClient() {
        // 여기서는 예시를 위해 자식 프로세스로 MCP 서버를 실행한다고 가정합니다.
        return StdioMcpClient.builder()
                .command(List.of("java", "-jar", "mcp-server.jar"))
                .build();
    }

    @Bean
    IncidentResponseAgent agent(ChatLanguageModel chatModel, McpClient mcpClient) {
        // [핵심] MCP 클라이언트가 제공하는 도구들을 AI 서비스와 연결
        return AiServices.builder(IncidentResponseAgent.class)
                .chatLanguageModel(chatModel)
                .contentRetriever(mcpClient) // MCP 리소스 처리
                .tools(mcpClient.getTools())  // MCP 도구 처리
                .build();
    }
}
```
### 3.5 자동화 로직 통합 (IncidentManager.java)
장애 이벤트를 수신하여 AI 에이전트의 워크플로우를 가동합니다.
```java
package com.example.ai.mcp.orchestration;

import com.example.ai.mcp.client.IncidentResponseAgent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
@Slf4j
public class IncidentManager {

    private final IncidentResponseAgent agent;

    /**
     * 외부 모니터링 시스템(Prometheus 등)으로부터 장애를 감지했다고 치고 호출되는 시뮬레이션
     */
    public void onServerDown() {
        log.error("장애 감지! AI 에이전트 분석 시작...");
        
        // AI 에이전트에게 전체 프로세스를 맡깁니다.
        // 에이전트는 [로그 조회] -> [원인 파악] -> [PR 생성] -> [Teams 통지] 순서로 스스로 판단하여 행동합니다.
        String report = agent.handleIncident("운영 서버의 결제 모듈에서 다수의 500 에러가 발생 중임.");
        
        log.info("AI 장애 복구 보고서: \n{}", report);
    }
}
```

---
## 4. MCP 활용 시 고려사항 (Best Practices)
### A. 최소 권한 원칙 (Least Privilege)
AI 에이전트에게 주는 MCP 도구는 반드시 필요한 역할로 한정해야 합니다.
- `createHotFixPR`은 허용하되, `forcePush`나 `deleteRepo` 같은 파괴적인 기능은 포함하지 마세요.
### B. 인간의 승인 (Human-in-the-Loop)
자동화가 편리하지만, 운영 서버에 영향을 주는 행위는 AI가 PR을 생성한 후 **"PR URL을 팀즈로 보내고 사람이 승인할 때까지 대기"** 하도록 에이전트 워크플로우를 구성하는 것이 안전합니다.
### C. 에러 복원력 (Error Resilience)
MCP 통신(특히 Stdio 방식)은 자식 프로세스가 죽거나 통신 지연이 발생할 수 있습니다. 클라이언트 설정 시 타임아웃 처리와 재시연(Retry) 로직을 반드시 포함하세요.
### D. 보안 및 인증
MCP 서버 내에서 외부 API(Bitbucket, Teams)를 호출할 때 사용하는 API Key나 토큰은 절대로 모델에게 직접 노출되지 않도록 서버 내부에서 은닉 처리하십시오.

# Reference
- [MCP 공식 웹사이트 (modelcontextprotocol.io)](https://modelcontextprotocol.io/)
- [Anthropic MCP GitHub Specs](https://github.com/modelcontextprotocol/specification)
- [Spring AI MCP Integration](https://docs.spring.io/spring-ai/reference/mcp.html)