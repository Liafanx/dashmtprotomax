# MTProxyMax Metrics Viewer

> 🌍 **Переводы:** [English](README.md) | [Русский](README_RU.md)

Красивая терминальная панель для мониторинга [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax) Telegram прокси с метриками Prometheus.

[![Версия](https://img.shields.io/badge/версия-1.0-blue.svg)](https://github.com/Liafanx/mtproxymax-metrics)
[![Лицензия](https://img.shields.io/badge/лицензия-MIT-green.svg)](LICENSE)
[![MTProxyMax](https://img.shields.io/badge/MTProxyMax-обязателен-orange.svg)](https://github.com/SamNet-dev/MTProxyMax)

## 📋 Содержание

- [Возможности](#-возможности)
- [Требования](#-требования)
- [Установка](#-установка)
- [Использование](#-использование)
- [Переустановка](#-переустановка)
- [Удаление](#-удаление)
- [Настройка](#-настройка)
- [Решение проблем](#-решение-проблем)
- [Скриншоты](#-скриншоты)
- [Справочник метрик](#-справочник-метрик)
- [Лицензия](#-лицензия)
- [Связанные проекты](#-связанные-проекты)
- [Поддержка](#-поддержка)
- [Важные замечания](#-важные-замечания)
- [История изменений](#-история-изменений)

## ✨ Возможности

- 📊 **Визуализация метрик в реальном времени** - Красивый терминальный интерфейс с цветами и таблицами
- 👥 **Статистика по пользователям** - Мониторинг соединений, трафика и сообщений для каждого пользователя
- 🔼 **Мониторинг Upstream** - Отслеживание успешности соединений и их длительности
- 🔄 **ME статистика** - Метрики производительности Multiplexed Endpoint
- 🎯 **SOCKS KDF Policy** - Мониторинг аутентификации и применения политик
- ⚡ **Live режим** - Автообновление панели каждые 5 секунд
- 🎨 **Rich терминал** - На основе библиотеки Python Rich

## 📦 Требования

> ⚠️ **Важно:** Этот инструмент требует установленный и запущенный [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax) с включёнными метриками Prometheus.

### Системные требования

- **Операционная система:** Ubuntu 22.04/24.04 или Debian 11/12
- **Python:** 3.10 или выше
- **Доступ:** Root/sudo привилегии
- **MTProxyMax:** [Установите MTProxyMax сначала](https://github.com/SamNet-dev/MTProxyMax)

### Проверка доступности метрик MTProxyMax

```bash
curl http://localhost:9090/metrics
```

Если видите вывод метрик, можете устанавливать viewer.

## 🚀 Установка

### Быстрая установка (Автоматическая)

Установка с автоматической переустановкой (рекомендуется):

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)"
```

Или используя wget:

```bash
sudo bash -c "$(wget -qO- https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)"
```

### Интерактивная установка (с подтверждением)

Скачать и запустить установщик с запросами:

```bash
wget https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh
sudo bash install.sh
```

### Установка через Git

```bash
git clone https://github.com/Liafanx/mtproxymax-metrics.git
cd mtproxymax-metrics
sudo bash install.sh
```

## 📖 Использование

### Основные команды

#### Просмотр всех метрик (Статический режим)

```bash
metrics
```

Отображает полный снимок всех метрик, включая:
- Статус системы и время работы
- Статистика соединений
- Производительность Upstream
- ME статистика
- Статистика пользователей
- Управление пулом
- SOCKS KDF политика

#### Live режим с автообновлением

```bash
metrics-live
```

Панель в реальном времени с обновлением каждые 5 секунд. Нажмите `Ctrl+C` для выхода.

### Просмотр конкретных секций

```bash
# Только статус
metrics --section status

# Только статистика пользователей
metrics --section users

# Статистика Upstream соединений
metrics --section upstream

# ME (Multiplexed Endpoint) статистика
metrics --section me

# Управление пулом
metrics --section pool

# SOCKS KDF политика
metrics --section socks

# Таблица системных метрик
metrics --section main
```

### Пользовательский URL метрик

Если метрики MTProxyMax на другом хосте/порту:

```bash
metrics --url http://ваш-сервер:9090/metrics
```

## 🔄 Переустановка

Для переустановки или обновления до последней версии:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/install.sh)"
```

Это автоматически удалит старую установку и установит свежую версию.

## 🗑️ Удаление

### Быстрое удаление

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Liafanx/mtproxymax-metrics/main/uninstall.sh)"
```

### Ручное удаление

```bash
sudo rm -rf /root/Metrics
sudo rm -f /usr/local/bin/metrics
sudo rm -f /usr/local/bin/metrics-live
```

## ⚙️ Настройка

### Изменение URL метрик

Отредактируйте файлы конфигурации:

**Для статического просмотра:**
```bash
sudo nano /root/Metrics/metrics_viewer.py
```

**Для live режима:**
```bash
sudo nano /root/Metrics/metrics_live.py
```

Измените строку 11:
```python
METRICS_URL = "http://localhost:9090/metrics"
```

### Изменение интервала обновления Live режима

Отредактируйте `/root/Metrics/metrics_live.py` строку 12:
```python
REFRESH_INTERVAL = 5  # секунды
```

### Установленные файлы

```
/root/Metrics/
├── venv/                    # Виртуальное окружение Python
├── metrics_viewer.py        # Основной скрипт просмотра
├── metrics_live.py          # Скрипт live режима
├── metrics                  # Wrapper скрипт
└── metrics-live             # Wrapper для live режима

/usr/local/bin/
├── metrics -> /root/Metrics/metrics
└── metrics-live -> /root/Metrics/metrics-live
```

## 🔧 Решение проблем

### Метрики недоступны

**Проблема:** `Error fetching metrics: Connection refused`

**Решение:**

1. Проверьте endpoint метрик:
   ```bash
   curl http://localhost:9090/metrics
   ```

2. Проверьте конфигурацию MTProxyMax на порт метрик

### Ошибка Python зависимостей

**Проблема:** `ModuleNotFoundError: No module named 'rich'`

**Решение:**

Переустановите зависимости:
```bash
cd /root/Metrics
source venv/bin/activate
pip install --upgrade requests rich
deactivate
```

### Команда не найдена

**Проблема:** `bash: metrics: command not found`

**Решение:**

Пересоздайте симлинки:
```bash
sudo ln -sf /root/Metrics/metrics /usr/local/bin/metrics
sudo ln -sf /root/Metrics/metrics-live /usr/local/bin/metrics-live
```

### Ошибка прав доступа

**Проблема:** `Permission denied`

**Решение:**

Убедитесь, что запускаете от root:
```bash
sudo metrics
sudo metrics-live
```

Или исправьте права:
```bash
sudo chmod +x /root/Metrics/metrics*
```

## 📊 Скриншоты

### Панель статуса

```
================================================
  PROMETHEUS METRICS VIEWER
  Панель метрик прокси MTProxyMax
================================================

┌─ Сводка ───────────────────────────────────┐
│ Статус: OK ОТЛИЧНО                         │
│ Uptime: 2д 15ч 42м                         │
│                                            │
│ Соединения:                                │
│   Всего:        45 892                     │
│   Авторизовано: 8 234 (17.9%)              │
│   Отклонено:    37 658 (нет секрета)       │
│                                            │
│ Upstream:                                  │
│   Попыток: 125 678                         │
│   Успешно: 124 890                         │
│   Ошибок:  788                             │
│   Процент: 99.4%                           │
└────────────────────────────────────────────┘

┌─ Статистика пользователей ─────────────────┐
│ Пользователь │ Соединений │ Активно │ RX   │
├──────────────┼────────────┼─────────┼──────┤
│ admin        │ 25 234     │ 15      │45 ГБ │
│ user1        │ 18 456     │ 8       │32 ГБ │
│ user2        │ 12 890     │ 3       │18 ГБ │
└──────────────┴────────────┴─────────┴──────┘
```

### Live режим

Панель в реальном времени с автообновлением и цветовыми индикаторами статуса.

## 📚 Справочник метрик

| Метрика | Описание |
|---------|----------|
| `telemt_uptime_seconds` | Время работы прокси-сервера в секундах |
| `telemt_connections_total` | Общее количество принятых соединений |
| `telemt_connections_bad_total` | Отклонённые соединения без валидного секрета |
| `telemt_upstream_connect_attempt_total` | Всего попыток upstream соединений |
| `telemt_upstream_connect_success_total` | Успешные upstream соединения |
| `telemt_upstream_connect_fail_total` | Неудачные upstream соединения |
| `telemt_me_reconnect_attempts_total` | Попытки ME переподключения |
| `telemt_me_reconnect_success_total` | Успешные ME переподключения |
| `telemt_user_connections_total` | Соединений на пользователя |
| `telemt_user_octets_from_client` | Байт получено от клиента на пользователя |
| `telemt_user_octets_to_client` | Байт отправлено клиенту на пользователя |
| `telemt_user_msgs_from_client` | Сообщений получено на пользователя |
| `telemt_user_msgs_to_client` | Сообщений отправлено на пользователя |

Полную документацию метрик смотрите в [Документации MTProxyMax](https://github.com/SamNet-dev/MTProxyMax).

## 📄 Лицензия

Этот проект распространяется под лицензией MIT - смотрите файл [LICENSE](LICENSE) для подробностей.

## 🔗 Связанные проекты

- **[MTProxyMax](https://github.com/SamNet-dev/MTProxyMax)** - Быстрый и безопасный MTProto прокси (Обязателен)
- **[Prometheus](https://prometheus.io/)** - Инструментарий мониторинга и оповещений

## 💬 Поддержка

- 🐛 **Сообщения об ошибках:** [Создать issue](https://github.com/Liafanx/mtproxymax-metrics/issues)
- 💡 **Запросы функций:** [Создать issue](https://github.com/Liafanx/mtproxymax-metrics/issues)
- 📖 **Документация:** [Wiki](https://github.com/Liafanx/mtproxymax-metrics/wiki)
- ⭐ **Поставьте звезду** если проект полезен!

## ⚠️ Важные замечания

1. **Требуется MTProxyMax:** Этот viewer работает только с [MTProxyMax](https://github.com/SamNet-dev/MTProxyMax). Установите его сначала.
2. **Метрики должны быть включены:** Убедитесь, что метрики Prometheus включены в конфигурации MTProxyMax.
3. **Порт по умолчанию 9090:** Если вы изменили порт метрик, используйте флаг `--url`.
4. **Root доступ:** Установка требует root/sudo привилегий.

## 📝 История изменений

### v1.1.1 (23.03.2026)

- 👥 **Таблица пользователей:** добавлен столбец TCP Limit (загружается из API `/v1/users`)
- 🔗 **Интеграция с API:** флаг `--api` для указания URL Control API
- 🔧 **Fallback:** показывает `-` когда API недоступен

### v1.1.0 (23.03.2026)

#### metrics_viewer.py
- 📊 **Панель статуса:** добавлена разбивка active/ME/direct соединений
- 📈 **Системные метрики:** добавлены relay adaptive, reconnect evict/stale, failfast
- 🆕 **Новая секция: Upstream Attempts** - распределение попыток на запрос
- 🔄 **ME статистика:** добавлены KDF drift, async recovery, writers active/warm, некомпенсированные удаления
- 🆕 **Новая секция: ME Keepalive** - sent/failed/pong/timeout
- 🆕 **Новая секция: Single-Endpoint Outage** - outage enter/exit, ротация теневых writer
- 🎯 **Writer Pick:** добавлен столбец Mode с описаниями результатов
- 🆕 **Новая секция: Adaptive Floor** - CPU ядра, лимиты, целевые writers, блокировки
- 🔧 **Pool Management:** добавлены soft evict, close signal drops, reap progress
- 🆕 **Новая секция: Security/Desync** - padding, desync, suppressed
- 🆕 **Новая секция: Relay Adaptive** - повышения/понижения уровня
- 👥 **Пользователи:** добавлены столбцы IPs и IP Limit
- 🔐 **SOCKS KDF:** добавлены описания для каждой политики
- ⚙️ **Новые опции --section:** `floor`, `outage`, `security`, `relay`

#### metrics_live.py
- 📊 **Заголовок:** добавлено количество активных соединений и writers active/warm
- 🔄 **Системная панель:** активные соединения с разбивкой ME/Direct, счётчик writers, карантин
- 👥 **Панель пользователей:** добавлен столбец уникальных активных IP

#### install.sh
- 🔍 **Проверка версии:** сравнение локальной и удалённой версии перед установкой
- 🔄 **Запрос обновления:** показывает "Доступно обновление: X -> Y"
- ⚡ **Автоматический режим:** флаг `--auto` пропускает все запросы
- 📄 **Файл версии:** сохраняет установленную версию в `/root/Metrics/.version`

### v1.0.0 (20.03.2026)

- ✨ Первый релиз
- 📊 Статический просмотр метрик
- ⚡ Live режим с автообновлением
- 👥 Статистика пользователей
- 🔼 Статистика Upstream соединений
- 🔄 ME статистика
- 🎯 SOCKS KDF политика
- 🔧 Статистика управления пулом

## 👤 Автор

Создано для сообщества MTProxyMax.

## 🌟 Поддержите проект

Если этот проект помог вам, рассмотрите:

- ⭐ **Поставить звезду** этому репозиторию

---

**Сделано с ❤️ для сообщества Telegram MTProxyMax**

🌍 **Доступно на:** [English](README.md) | [Русский](README_RU.md)

[🔝 Вернуться наверх](#mtproxymax-metrics-viewer)
```
