# Текущая задача

> Здесь всегда ТОЛЬКО ОДНА активная задача. Новая задача → эта уходит в archive/.

- **Название:** Одноузловой Kubernetes на сервере (замена LLM-стенда, см. archive/2026-09-11_llm_stand_done.md)
- **Цель (1 строка):** Сервер превращён в чистый одноузловой k8s (не кластер) для запуска подов и docker-образов с GPU (RTX 3060 12 GB) и без.

## Железо (обновлено 2026-09-11 после полной очистки)

| Компонент | Значение | Вывод для k8s |
|---|---|---|
| CPU | Ryzen 7 5800X, 8C/8T | ок для одного узла |
| RAM | 62 ГБ | k3s/microk8s съедают ~1–2 ГБ, остаётся ~60 ГБ под поды — с запасом |
| Диск | 1×SSD 200 ГБ, **занято 14 ГБ, свободно 171 ГБ** | достаточно: сам k8s ~неск. ГБ + образы; тяжёлые модели (47 ГБ 72B) влезают, но следить за местом; при нехватке — расширить LVM/диск в Proxmox |
| GPU | RTX 3060 12 GB, драйвер 595.84, nvidia-container-toolkit установлен | ок: NVIDIA device plugin + containerd runtime → GPU в поды |
| OS | Ubuntu 24.04, Docker 29 оставлен (для сборки образов), GPU-драйвер host-уровня | ок |
| Swap | 8 ГБ (swap.img) | для k8s лучше отключить/снизить (kubelet не любит swap) — решить на установке |

## Что сделано 2026-09-11

- [x] Полная очистка сервера: стенд остановлен (`docker compose down -v`), все образы/тома/prune (~126 ГБ освобождено), скачанные safetensors из /tmp удалены; `.env.stand` сохранён в workspace/scratch/env.stand.bak.
- [x] Анализ ресурсов под k8s — см. таблицу выше (диск/RAM/GPU достаточно).
- [x] **Этап 0 — Окружение.** Swap отключён (fstab закомментирован); apt autoremove/clean; k3s v1.36.4 (stable) установлен, узел `iamodels` Ready; kubeconfig доступен (k3s.yaml 644 + ~/.kube/config); инструменты: helm v3.22.0, k9s v0.51.0; Docker оставлен для сборки образов.
- [x] **Этап 1 — GPU.** k3s сам добавил nvidia-runtime в containerd; RuntimeClass `nvidia`; NVIDIA device plugin (daemonset, патч runtimeClassName); узел рекламирует `nvidia.com/gpu: 1`; smoke-тест `nvidia-smi` в поде пройден. Манифесты и инструкции: `k8s/`.
- [ ] **Этап 2 — Перенос LLM-стенда в поды** (ollama, webui, speech, tts-worker, comfyui) — Kompose или вручную; модели — через PV (local-path) или hostPath.
- [ ] **Этап 3 — Ingress/доступ из LAN, update/backup-скрипты, health_check.**

## Решения (зафиксированы в memory/decisions.md)

- Дистрибутив: **k3s** (минимальный оверхед, автодетект GPU-рантайма).
- CNI/ingress: дефолт k3s (flannel + Traefik), storage: local-path-provisioner.
- GPU: RuntimeClass `nvidia` + device plugin; ⚠️ не создавать config.toml.tmpl — k3s сам генерирует nvidia-рантайм (дубль = падение containerd).
- Swap отключён; k3s.yaml открыт на 644 (LAN доверенная сеть, решение 2026-09-10 о firewall действует).
- Docker на хосте оставлен для сборки образов.

- **Статус:** этапы 0–1 выполнены; ждём команды на этап 2 (перенос стенда в поды)
- **Активный запуск:** workspace/runs/ (будет создан при старте переноса)
