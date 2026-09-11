# k8s/ — манифесты одноузлового кластера

Кластер: **k3s v1.36.4** (stable), узел `iamodels` (192.168.1.111), containerd 2.3.
Установлен 2026-09-11 после полной очистки сервера (см. tasks/archive/2026-09-11_llm_stand_done.md).

## Быстрый доступ

```bash
kubectl get nodes                 # kubeconfig: /etc/rancher/k3s/k3s.yaml (644) и ~/.kube/config
k9s                               # TUI-обзор кластера
helm version                      # v3.22.0
```

## GPU (RTX 3060 12 GB)

Работает через связку:
1. **k3s сам добавляет nvidia-runtime в containerd** при наличии `/usr/bin/nvidia-container-runtime`
   (проверено: секция `runtimes.nvidia` генерируется в config.toml автоматически).
   ⚠️ Не создавать `config.toml.tmpl` с тем же блоком — containerd падает с
   `table nvidia already exists`.
2. `runtimeclass.yaml` — RuntimeClass `nvidia` (handler = containerd runtime nvidia).
3. NVIDIA device plugin (daemonset, namespace kube-system) с `runtimeClassName: nvidia`.

Запрос GPU в поде:

```yaml
spec:
  runtimeClassName: nvidia        # обязательно, иначе библиотеки CUDA не попадут в контейнер
  containers:
  - resources:
      limits:
        nvidia.com/gpu: 1
```

Smoke-test: `kubectl apply -f gpu-test-pod.yaml && kubectl logs gpu-test`.

## Состав кластера

- CNI: flannel (дефолт k3s), ingress: Traefik (дефолт), storage: local-path-provisioner.
- Системные поды: coredns, metrics-server, traefik, svclb, local-path-provisioner, nvidia-device-plugin.
- Swap отключён (fstab закомментирован, /etc/fstab.bak — копия).
- Docker engine на хосте оставлен для сборки образов (`docker build` → `docker save`/registry → поды k3s).
