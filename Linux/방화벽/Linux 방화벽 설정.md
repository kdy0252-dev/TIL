---
id: Linux 방화벽 설정
started: 2025-02-27
tags:
  - ✅DONE
group: "[[Linux]]"
---
# Linux 방화벽 설정
## IP Tables
### IP Tables 상세 정보
```shell title="iptables 기본 커맨드"
iptables [-t table] [action] [chain] [matches] [-j target]
```
#### table
- filter, nat, mangle, raw가있으며 주로 사용하는 필터링 규칙에는 filter테이블을 사용한다.
- 생략하게 되면 자동으로 filter로 적용된다.
#### action - 정책을 어떻게 할지 정하는 것 , 정책 추가, 삭제, 변경 등
- -A(—append) : 새로운 정책 추가
- -I(—insert) : 위치를 선택하여 정책을 삽입
- -D(—delete) : 정책을 삭제합니다.
- -R(—replace) : 정책을 교체합니다.
- -F(—flush) : 체인으로부터 모든 정책 삭제합니다.
- -P(—policy) : 기본 정책을 설정합니다.
- -L(—list) : 정책 목록을 확인합니다.
#### chain - 체인이란 패킷에 대한 정보를 라우팅을 해주는 방법을 정하는 것
- INPUT : 호스트(서버) 컴퓨터를 향한 모든 패킷(서버로 들어오는 패킷은 Input Chain을 통과)
- OUTPUT : 호스트(서버) 컴퓨터에서 발생하는 모든 패킷(서버에서 나가는 패킷을 output chain을 통과)
- FORWARD : 호스트(서버) 컴퓨터가 목적지가 아닌 모든 패킷, 즉 라우터로 사용되는 호스트 컴퓨터를 통과하는 패킷
#### matches - 출발지와 목적지를 매칭해주는 방법을 정하는 것
- -s(—source, —src) : 출발지 매칭, 도메인, IP 주소, 넷마스크 값을 이용하여 표기
- -d(—destination, —dst) : 목적지 매칭, 도메인, IP주소, 넷마스크 값을 이용하여 표기
- -p : 프로토콜과 매칭, TCP, UDP, ICMP와 같은 이름을 사용하고 대소문자는 구분하지 않음
- -i(—in-interface) : 입력 인터페이스와 매칭
- -o(—out-interface) : 출력 인터페이스와 매칭
- -j(—jump) : 매치되는 패킷을 어떻게 처리할지 지정
- -f(—fragment) : 분절된 패킷
- —sport : 송신지 포트와 매칭
- —dport : 수신지 포트와 매칭
#### -j target - 패킷이 규칙과 일치하르 대 취하는 동작을 지정합니다.
ACCEPT : 패킷을 허용합니다.
DROP : 패킷을 버립니다.
REJECT : 패킷을 버리고 이와 동시에 적절한 응답 패킷을 전송합니다.
LOG : 패킷을 syslog에 기록합니다.
RETURN : 호출 체인 내에서 패킷 처리를 계속한다.

# Reference