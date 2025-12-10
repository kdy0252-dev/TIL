---
id: Long Polling
started: 2025-05-08
tags:
  - ✅DONE
  - Java
  - Spring
group:
  - "[[Java Spring]]"
---
# Long Polling
## Long Polling 이란?
Long Polling은 클라이언트가 서버에 요청을 보내고, 서버가 즉시 응답하지 않고 **새로운 이벤트가 발생할 때까지 연결을 유지하는 방식**이다. 이벤트가 발생하면 서버는 클라이언트에게 응답을 보내고, 클라이언트는 다시 서버에 새로운 요청을 보내는 방식으로 동작한다.
### 동작 방식
1.  클라이언트가 서버에 Long Polling 요청을 보낸다.
2.  서버는 요청을 즉시 처리하지 않고, 이벤트가 발생할 때까지 대기한다.
3.  이벤트가 발생하면 서버는 클라이언트에게 응답을 보낸다.
4.  클라이언트는 응답을 받으면 다시 서버에 새로운 Long Polling 요청을 보낸다.
### 장점
*   서버 자원 효율성: 이벤트가 없을 때는 연결을 유지하면서 대기하므로, 불필요한 트래픽을 줄일 수 있다.
*   비교적 간단한 구현: WebSocket에 비해 구현이 간단하다.
### 단점
*   응답 지연: 이벤트가 발생하기 전까지 응답을 받지 못하므로, 실시간성이 중요한 경우에는 적합하지 않을 수 있다.
*   Connection 제한: 클라이언트 연결 수가 많아질 경우 서버에 부담이 될 수 있다.
## Java Spring Long Polling 구현 예시
### 1. Controller 구현
```java title="EventController.java"
package com.example.chat.controller;

import com.example.chat.model.ChatMessage;
import com.example.chat.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.async.DeferredResult;

@RestController
@RequestMapping("/chat")
@RequiredArgsConstructor
public class ChatController {
    private final ChatService chatService;

    @GetMapping("/receive")
    public DeferredResult<ResponseEntity<ChatMessage>> receive() {
        return chatService.subscribe();
    }

    @PostMapping("/send")
    public ResponseEntity<Void> send(@RequestBody ChatMessage message) {
        chatService.sendMessage(message);
        return ResponseEntity.ok().build();
    }
}
```
### 2. Service 구현
```java title
package com.example.chat.service;

import com.example.chat.model.ChatMessage;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.context.request.async.DeferredResult;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

@Service
public class ChatService {
    private final List<DeferredResult<ResponseEntity<ChatMessage>>> clients = new CopyOnWriteArrayList<>();

    public DeferredResult<ResponseEntity<ChatMessage>> subscribe() {
        DeferredResult<ResponseEntity<ChatMessage>> deferred = new DeferredResult<>(60_000L);
        deferred.onTimeout(() -> deferred.setResult(ResponseEntity.noContent().build()));
        clients.add(deferred);
        return deferred;
    }

    public void sendMessage(ChatMessage msg) {
        for (DeferredResult<ResponseEntity<ChatMessage>> client : clients) {
            client.setResult(ResponseEntity.ok(msg));
        }
        clients.clear();
    }
}
```
### 3. Client 구현
```html title="client.html"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Long-Polling Chat</title>
</head>
<body>
<h1>Chat Room</h1>
<div id="chat" style="border:1px solid #ccc;height:300px;overflow:auto;"></div>
<input id="user" placeholder="Your name" />
<input id="msg" placeholder="Type a message" />
<button onclick="send()">Send</button>

<script>
function append(msg) {
    const div = document.getElementById('chat');
    div.innerHTML += `<p><strong>${msg.from}:</strong> ${msg.text}</p>`;
    div.scrollTop = div.scrollHeight;
}

function longPoll() {
    fetch('/chat/receive')
        .then(res => {
            if (res.status === 204) return null;
            return res.json();
        })
        .then(msg => {
            if (msg) append(msg);
            longPoll();
        })
        .catch(() => setTimeout(longPoll, 1000));
}

function send() {
    const from = document.getElementById('user').value || 'Anonymous';
    const text = document.getElementById('msg').value;
    fetch('/chat/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({from, text})
    });
    document.getElementById('msg').value = '';
}

longPoll();
</script>
</body>
</html>
```
*   **Timeout 처리**: 응답 상태 코드가 204 (No Content)일 경우, Timeout으로 간주하고 다시 Long Polling을 시도한다.
*   **오류 처리**: 네트워크 오류 발생 시 5초 후 재시도한다.
## Long Polling은 언제 사용하면 좋을까?
### 적합한 사용 시점
*   **이벤트 발생 빈도가 낮을 때**: 이벤트가 자주 발생하지 않는 경우, 서버 자원을 효율적으로 사용할 수 있다.
*   **실시간성이 중요하지 않을 때**: 약간의 지연을 감수할 수 있는 경우에 적합하다.
*   **간단한 구현이 필요할 때**: WebSocket과 같은 기술에 비해 구현이 간단하므로, 빠르게 프로토타입을 개발하거나 간단한 기능을 구현할 때 유용하다.
### 부적합한 사용 시점
*   **실시간성이 매우 중요할 때**: 주식 거래, 실시간 게임 등 지연에 민감한 서비스에는 적합하지 않다.
*   **이벤트 발생 빈도가 매우 높을 때**: 서버에 과도한 부하를 줄 수 있으므로, 다른 방법을 고려해야 한다.
*   **양방향 통신이 필요할 때**: 클라이언트에서 서버로 데이터를 실시간으로 전송해야 하는 경우에는 WebSocket이 더 적합하다.
### 다른 방법
*   **WebSocket**: 실시간 양방향 통신에 최적화되어 있으며, 서버와 클라이언트 간에 지속적인 연결을 유지한다.
*   **Server-Sent Events (SSE)**: 서버에서 클라이언트로 단방향 실시간 데이터 스트림을 전송하는 데 사용되며, HTTP 기반이므로 구현이 비교적 간단하다.
*   **Polling**: 클라이언트가 주기적으로 서버에 요청을 보내어 새로운 데이터가 있는지 확인하는 방식이다. Long Polling에 비해 서버 부하가 높을 수 있다.
### 추가 고려 사항
*   **메시지 큐 (Message Queue)**: Kafka, RabbitMQ와 같은 메시지 큐를 사용하여 이벤트 발행 및 구독을 처리하면, 서버의 부담을 줄이고 확장성을 높일 수 있다.
*   **Spring WebFlux**: Spring WebFlux를 사용하면 Non-Blocking I/O를 통해 더 높은 성능을 얻을 수 있다.
*   **보안**: Spring Security 등을 사용하여 Long Polling 엔드포인트에 대한 인증 및 권한 부여를 구현해야 한다.

# Reference
[Polling / Long Polling / SSE / WebSocket](https://velog.io/@dev_jazziron/Polling-Long-Polling-SSE-WebSocket)
[Long Polling](https://velog.io/@bruni_23yong/%EC%9A%B0%EB%A6%AC%EB%8A%94-%EC%B1%84%ED%8C%85%EC%9D%84-%EC%99%9C-Long-Polling%EC%9C%BC%EB%A1%9C-%EA%B0%9C%EB%B0%9C%ED%96%88%EB%8A%94%EA%B0%80)
