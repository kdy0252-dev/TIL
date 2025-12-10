---
id: WebSocket Reverse Proxy Setting
started: 2025-05-28
tags:
  - ✅DONE
group:
  - "[[Java Spring]]"
---
# WebSocket Reverse Proxy 설정
## WebSocket Reverse Proxy란?
WebSocket Reverse Proxy는 클라이언트의 WebSocket 연결 요청을 받아 실제 WebSocket 서버로 전달하고, 서버의 응답을 클라이언트에게 전달하는 서버이다. 이를 통해 실제 서버의 정보를 숨기고, 로드 밸런싱, SSL 암호화 등의 기능을 제공하여 WebSocket 서비스의 보안, 성능, 확장성을 향상시킬 수 있다.
### WebSocket Reverse Proxy는 왜 사용할까?
*   **보안**: 실제 WebSocket 서버의 IP 주소, 포트 번호, 서버 종류 등의 정보를 숨겨 외부 공격으로부터 보호한다.
*   **로드 밸런싱**: 여러 대의 WebSocket 서버에 트래픽을 분산시켜 서버의 부하를 줄인다.
*   **SSL 암호화**: SSL 암호화를 Reverse Proxy에서 처리하여 서버의 부하를 줄인다.
*   **캐싱**: 정적 콘텐츠를 캐싱하여 서버의 응답 시간을 줄인다.
*   **CORS (Cross-Origin Resource Sharing)**: 서로 다른 도메인에서 WebSocket 연결을 허용하도록 설정한다.
### WebSocket Reverse Proxy의 장점과 단점
**장점:**
*   **보안 강화**: 실제 서버 정보를 숨겨 외부 공격으로부터 보호한다.
*   **로드 밸런싱**: 여러 대의 서버에 트래픽을 분산시켜 서버 부하를 줄인다.
*   **SSL 암호화**: SSL 암호화를 Reverse Proxy에서 처리하여 서버 부하를 줄인다.
*   **CORS 지원**: 서로 다른 도메인에서 WebSocket 연결을 허용한다.
*   **유연한 구성**: 다양한 Reverse Proxy 서버 (Nginx, Apache, HAProxy 등)를 사용할 수 있다.
**단점:**
*   **추가 설정**: Reverse Proxy 서버를 설정하고 관리해야 한다.
*   **성능**: Reverse Proxy 서버를 거치면서 약간의 성능 저하가 발생할 수 있다.
*   **복잡성**: Reverse Proxy 서버를 설정하고 관리하는 과정이 복잡할 수 있다.
## WebSocket Reverse Proxy 설정 예시 (Nginx)
### 1. Nginx 설치
Nginx를 설치한다.
```bash
sudo apt update
sudo apt install nginx
```
### 2. Nginx 설정 파일 수정
Nginx 설정 파일 (`/etc/nginx/nginx.conf` 또는 `/etc/nginx/conf.d/websocket.conf`)을 수정한다.
```nginx title="nginx.conf"
http {
    upstream websocket_servers {
        server backend1.example.com:8080;
        server backend2.example.com:8080;
    }

    server {
        listen 443 ssl;
        server_name example.com;

        ssl_certificate /etc/nginx/ssl/example.com.crt;
        ssl_certificate_key /etc/nginx/ssl/example.com.key;

        location /ws {
            proxy_pass http://websocket_servers;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
        }
    }
}
```
*   `upstream` 블록을 사용하여 WebSocket 서버를 정의한다.
    *   `backend1.example.com:8080`, `backend2.example.com:8080`: 실제 WebSocket 서버의 주소와 포트 번호를 설정한다.
*   `server` 블록을 사용하여 Reverse Proxy 서버를 설정한다.
    *   `listen 443 ssl`: HTTPS 프로토콜을 사용하고 443 포트를 Listen한다.
    *   `server_name example.com`: Reverse Proxy 서버의 도메인 이름을 설정한다.
    *   `ssl_certificate`, `ssl_certificate_key`: SSL 인증서 파일 경로를 설정한다.
*   `location /ws` 블록을 사용하여 `/ws` URL로 들어오는 요청을 WebSocket 서버로 프록시한다.
    *   `proxy_pass http://websocket_servers`: WebSocket 서버로 요청을 전달한다.
    *   `proxy_http_version 1.1`: HTTP 1.1 프로토콜을 사용한다.
    *   `proxy_set_header Upgrade $http_upgrade`: `Upgrade` 헤더를 설정하여 WebSocket 연결을 업그레이드한다.
    *   `proxy_set_header Connection "upgrade"`: `Connection` 헤더를 설정하여 연결을 유지한다.
    *   `proxy_set_header Host $host`: `Host` 헤더를 설정한다.
### 3. Nginx 재시작
Nginx를 재시작하여 변경된 설정을 적용한다.
```bash
sudo systemctl restart nginx
```
### 4. 클라이언트 설정
클라이언트에서 WebSocket 연결 URL을 Reverse Proxy 서버의 주소로 변경한다.
```javascript
const socket = new WebSocket("wss://example.com/ws");
```
### 사용 시 주의사항
*   **Reverse Proxy 서버 설정**: Reverse Proxy 서버의 설정을 정확하게 해야 한다.
*   **SSL 인증서**: SSL 인증서를 안전하게 관리해야 한다.
*   **WebSocket 서버 방화벽**: WebSocket 서버의 방화벽 설정을 확인하여 Reverse Proxy 서버의 접근을 허용해야 한다.
*   **세션 유지**: 필요한 경우 세션 유지 기능을 설정해야 한다.

WebSocket Reverse Proxy는 WebSocket 서비스의 보안, 성능, 확장성을 향상시키는 데 유용한 기술이다. Nginx, Apache, HAProxy 등 다양한 Reverse Proxy 서버를 사용하여 WebSocket Reverse Proxy를 구성할 수 있다.

# Reference
[Nginx WebSocket Proxy](https://www.nginx.com/blog/websocket-nginx/)
[WebSocket과 ReverseProxy](https://katastrophe.tistory.com/185)