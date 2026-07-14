---
id: Linux 방화벽 설정
started: 2025-02-27
tags:
  - ✅DONE
group: "[[Linux]]"
---
# Linux 방화벽 설정

Linux Firewall 규칙은 단순한 Port 목록이 아니라 Packet이 어느 방향으로 이동하고 어떤 Connection 상태에 속하는지 판단하는 정책이다. Rule을 추가하기 전에 Host가 Server인지 Router인지, Docker·Kubernetes가 별도 Netfilter Rule을 관리하는지 확인한다.

현대 Linux에서는 nftables가 Netfilter의 주된 사용자 Interface이며, 많은 Distribution의 `iptables` 명령도 내부적으로 nftables Backend를 사용할 수 있다. `iptables-legacy`와 `iptables-nft` Rule을 혼용하면 화면에 보이는 정책과 실제 적용 경로를 오해할 수 있다.

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

## Packet이 Chain을 통과하는 순서

- Local Process를 향한 Packet은 주로 `INPUT`을 지난다.
- Local Process가 만든 Packet은 `OUTPUT`을 지난다.
- Host가 Router처럼 중계하는 Packet은 `FORWARD`를 지난다.
- Destination NAT은 Routing 결정 전, Source NAT은 주로 Routing 결정 뒤에 적용된다.

Rule은 위에서 아래로 평가되고 일치한 Target에서 처리가 끝날 수 있다. 따라서 허용 Rule 뒤에 추가한 차단 Rule이 기대대로 동작하지 않을 수 있다.

## Stateful Firewall 기본 예

```shell
# 현재 SSH 연결이 사용하는 Port를 먼저 허용한다.
sudo iptables -A INPUT -p tcp --dport 22 \
  -m conntrack --ctstate NEW -j ACCEPT

# 이미 성립했거나 관련된 응답 Traffic 허용
sudo iptables -A INPUT \
  -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Loopback 허용
sudo iptables -A INPUT -i lo -j ACCEPT
```

기본 정책을 `DROP`으로 바꾸기 전에 SSH, Monitoring, DNS, NTP와 Cluster Control Plane Traffic을 모두 식별한다. 원격 작업에서는 일정 시간 뒤 자동 복구되는 Script나 Console을 준비한다.

## nftables로 같은 의도 표현하기

```nft
table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;

    iifname "lo" accept
    ct state established,related accept
    tcp dport 22 ct state new accept
  }
}
```

`inet` Family는 IPv4와 IPv6 규칙을 함께 관리할 수 있다. IPv4만 막고 IPv6를 열어 두는 실수를 줄여 준다. 실제 적용은 배포판의 `nftables.service`, `firewalld`와 영속 설정 방식을 따른다.

## DROP과 REJECT 선택

`DROP`은 응답 없이 버려 상대가 Timeout까지 기다리게 한다. `REJECT`는 즉시 ICMP 오류나 TCP Reset을 돌려준다. 내부 Network의 명시적 차단은 빠른 실패를 위해 `REJECT`가 진단에 유리할 수 있고, 외부 노출 최소화 정책에서는 `DROP`을 선택할 수 있다.

## 안전한 변경 절차

1. `iptables-save` 또는 `nft list ruleset`으로 현재 정책을 Backup한다.
2. Connection Tracking과 실제 Listening Socket을 `ss -lntup`으로 확인한다.
3. 허용 Rule을 먼저 넣고 별도 Session에서 연결을 검증한다.
4. 마지막에 기본 차단 정책을 적용한다.
5. 재부팅 뒤에도 같은 Rule이 복원되는지 Test한다.

Docker, Kubernetes와 CNI Plugin은 NAT·FORWARD Rule을 자동 생성한다. 운영 중 전체 Rule을 `flush`하면 Container Network가 즉시 끊길 수 있으므로 소유 주체가 다른 Chain을 임의로 삭제하지 않는다.

# Reference
[Netfilter project](https://www.netfilter.org/)
[nftables Wiki](https://wiki.nftables.org/)
[iptables Manual](https://man7.org/linux/man-pages/man8/iptables.8.html)
