---
id: K8S-Install.sh
started: 2025-02-26
tags: []
---
# K8S-Install.sh
```shell title="K8S 설치 스크립트"
#!/bin/bash
# Usage: ./setup.sh <hostIp> <cidr> <apiServerIp>
# Example: ./setup.sh 192.168.77.2 172.16.0.0/16 192.168.77.2

# ----------------------------------------------------------------------
# 파라미터 체크: 2개의 인자(hostIp, cidr)가 입력되었는지 확인
# ----------------------------------------------------------------------
if ! ([[ "$#" -eq 2 ]] || [[ "$#" -eq 3 ]]); then
    echo "Usage: $0 <hostIp> <cidr> <apiServerIp>"
    echo "Example: $0 192.168.77.2 172.16.0.0/16 or"
    echo "Example: $0 192.168.77.2 172.16.0.0/16 192.168.77.2"
    exit 1
fi

# ----------------------------------------------------------------------
# 스크립트가 root 권한(또는 sudo)으로 실행되었는지 확인
# ----------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    echo "이 스크립트는 sudo 권한이 필요합니다. sudo로 실행해 주세요."
    exit 1
fi

# ----------------------------------------------------------------------
# 인자 변수에 할당
# ----------------------------------------------------------------------
hostIp="$1"
cidr="$2"
apiServerIp="$3"

# ----------------------------------------------------------------------
# 시스템 업데이트 및 필수 패키지 설치
# ----------------------------------------------------------------------
yum update -y 
yum install -y wget vim

# ----------------------------------------------------------------------
# 시간대 설정 (Asia/Seoul)
# ----------------------------------------------------------------------
timedatectl set-timezone Asia/Seoul

# ----------------------------------------------------------------------
# /etc/hosts에 호스트 정보 추가 (hostIp 사용)
# ----------------------------------------------------------------------
echo "${hostIp} k8s-master" | tee -a /etc/hosts

# ----------------------------------------------------------------------
# 방화벽 정지 및 비활성화
# ----------------------------------------------------------------------
systemctl stop firewalld
systemctl disable firewalld

# ----------------------------------------------------------------------
# swap off (Kubernetes는 swap이 비활성화되어야 합니다)
# ----------------------------------------------------------------------
swapoff -a

# ----------------------------------------------------------------------
# dnf 플러그인 설치 및 Docker CE repo 추가
# ----------------------------------------------------------------------
yum -y install dnf-plugins-core
yum config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# ----------------------------------------------------------------------
# containerd 설치 및 설정
# ----------------------------------------------------------------------
yum -y install --allowerasing containerd.io-1.7.25-3.1.el8
systemctl enable --now containerd

# containerd 기본 설정 파일 생성
containerd config default > /etc/containerd/config.toml

# systemd cgroup 사용으로 변경
sed -i 's/ SystemdCgroup = false/ SystemdCgroup = true/' /etc/containerd/config.toml
systemctl restart containerd

# ----------------------------------------------------------------------
# Kubernetes repo 설정
# ----------------------------------------------------------------------
cat << EOF | sudo tee /etc/yum.repos.d/kubernetes.repo
[kubernetes]
name=Kubernetes
baseurl=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/
enabled=1
gpgcheck=1
gpgkey=https://pkgs.k8s.io/core:/stable:/v1.30/rpm/repodata/repomd.xml.key
exclude=kubelet kubeadm kubectl cri-tools kubernetes-cni
EOF

# ----------------------------------------------------------------------
# kubelet, kubeadm, kubectl 설치
# ----------------------------------------------------------------------
yum install -y kubelet kubeadm kubectl --disableexcludes=kubernetes

systemctl enable --now kubelet

# ----------------------------------------------------------------------
# IP 포워딩 활성화
# ----------------------------------------------------------------------
echo "net.ipv4.ip_forward = 1" | tee -a /etc/sysctl.conf
sysctl -p

# ----------------------------------------------------------------------
# Kubernetes 클러스터 초기화 (pod network CIDR는 파라미터로 받은 값 사용)
# ----------------------------------------------------------------------
if [ -n "$apiServerIp" ]; then
	kubeadm init --pod-network-cidr=${cidr} --apiserver-advertise-address=${apiServerIp}
else 
	kubeadm init --pod-network-cidr=${cidr}
fi

# ----------------------------------------------------------------------
# kubeconfig 설정 (kubectl 사용을 위한 설정 복사)
# ----------------------------------------------------------------------
mkdir -p $HOME/.kube
unalias cp 2>/dev/null
cp -f /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# ----------------------------------------------------------------------
# Calico custom-resources 다운로드
# ----------------------------------------------------------------------
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.29.2/manifests/custom-resources.yaml

# ----------------------------------------------------------------------
# sed에서 사용하기 위해 CIDR 값의 슬래시(/)를 이스케이프 처리
# ----------------------------------------------------------------------
escaped_cidr=$(echo "$cidr" | sed 's/\./\\\./g; s/\//\\\//g')

# ----------------------------------------------------------------------
# 기본 CIDR (192.168.0.0/16)을 파라미터로 받은 CIDR로 대체
# ----------------------------------------------------------------------
sed -i "s/cidr: 192\.168\.0\.0\/16/cidr: ${escaped_cidr}/g" custom-resources.yaml

# ----------------------------------------------------------------------
# Calico custom-resources 적용 (Operator 및 Custom Resources)
# ----------------------------------------------------------------------
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.2/manifests/tigera-operator.yaml
sleep 5
kubectl apply -f custom-resources.yaml

# ----------------------------------------------------------------------
# 마스터 노드의 taint 제거 (마스터 노드에서 파드를 스케줄링 할 수 있도록 함)
# ----------------------------------------------------------------------
kubectl taint nodes k8s-master node-role.kubernetes.io/control-plane:NoSchedule-

# ----------------------------------------------------------------------
# calicoctl 바이너리 다운로드 (amd64)
# ----------------------------------------------------------------------
curl -L https://github.com/projectcalico/calico/releases/download/v3.29.2/calicoctl-linux-amd64 -o kubectl-calico
chmod +x kubectl-calico

# ----------------------------------------------------------------------
# Calico 시스템 네임스페이스의 pod 상태 모니터링
# ----------------------------------------------------------------------
watch kubectl get pods -A
```


```
bond0: flags=5187<UP,BROADCAST,RUNNING,MASTER,MULTICAST>  mtu 1500
        inet 10.19.2.171  netmask 255.255.255.128  broadcast 10.19.2.255
        inet6 fe80::2204:fff:fefa:430c  prefixlen 64  scopeid 0x20<link>
        ether 20:04:0f:fa:43:0c  txqueuelen 1000  (Ethernet)
        RX packets 45407076  bytes 8315313651 (7.7 GiB)
        RX errors 0  dropped 1  overruns 0  frame 0
        TX packets 51937069  bytes 33481483450 (31.1 GiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

kubeadm join 192.168.0.41:6443 --token tngbfc.z4buvnegmwfwzxus --discovery-token-ca-cert-hash sha256:2b487bc1676bfc27d04f2390a5853ac1a9ff9fb979cbb0255d0b0e1b21b2d02e
```
# Reference