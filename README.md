# Система голосового управления для Orange Pi Zero 2W

Полнофункциональная система голосового управления, которая:
- Распознает русскую речь на Orange Pi Zero 2W
- Преобразует голосовые команды в Python скрипты с помощью локальной LLM
- Отправляет и выполняет скрипты на основном ПК по сети

## Архитектура

```
┌─────────────────────────────┐         ┌──────────────────────────┐
│     Orange Pi Zero 2W       │         │      Основной ПК         │
│                             │         │                          │
│  🎤 Микрофон                │         │                          │
│   │                         │         │                          │
│   ├─► Vosk (STT)            │         │                          │
│   │                         │         │                          │
│   ├─► Ollama (LLM)          │         │                          │
│   │   llama3.2:3b           │ Network │                          │
│   │                         │◄────────┤  Flask Server            │
│   └─► Python скрипт         │         │                          │
│       │                     │         │  🖥️ Выполнение скриптов  │
│       └─► Отправка ────────►│         │                          │
└─────────────────────────────┘         └──────────────────────────┘
```

## Возможности

- ✅ Офлайн распознавание речи (Vosk)
- ✅ Локальная LLM для генерации кода (Ollama)
- ✅ Безопасное выполнение скриптов на удаленном ПК
- ✅ Слово активации ("Джарвис" по умолчанию)
- ✅ Непрерывное прослушивание
- ✅ API ключ для аутентификации
- ✅ История выполненных команд
- ✅ Автозапуск через systemd

## Требования

### Orange Pi Zero 2W (клиент)
- Orange Pi Zero 2W с 4 ГБ ОЗУ
- Armbian / Ubuntu / Debian
- Python 3.8+
- Микрофон (USB или 3.5mm)
- Доступ к сети
- ~2 ГБ свободного места (для модели LLM)

### Основной ПК (сервер)
- Linux / Windows / macOS
- Python 3.8+
- Доступ к сети (локальная сеть с Orange Pi)

## Установка

### 1. Установка на Orange Pi Zero 2W (клиент)

#### 1.1 Системные зависимости

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей для Python и аудио
sudo apt install -y python3 python3-pip python3-venv \
                     portaudio19-dev python3-pyaudio \
                     libasound2-dev git

# Установка Ollama (для локальной LLM)
curl -fsSL https://ollama.com/install.sh | sh
```

#### 1.2 Настройка проекта

```bash
# Клонирование репозитория
cd ~
git clone <URL репозитория>
cd MaybeSomeJarvis-

# Создание виртуального окружения
cd voice_command_client
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей Python
pip install -r requirements.txt
```

#### 1.3 Скачивание модели Vosk

```bash
# Скачивание русской модели (рекомендуется small версия для ARM)
cd ~/MaybeSomeJarvis-/voice_command_client
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 model
rm vosk-model-small-ru-0.22.zip

# Для английского языка:
# wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
```

#### 1.4 Установка модели LLM (Ollama)

```bash
# Запуск Ollama
sudo systemctl start ollama

# Установка легковесной модели (3B параметров, ~2GB)
ollama pull llama3.2:3b

# Альтернативы:
# ollama pull llama3.2:1b  # Еще легче (~700MB), для совсем ограниченных ресурсов
# ollama pull mistral:7b   # Мощнее, но требует больше RAM
```

#### 1.5 Настройка микрофона

```bash
# Проверка доступных устройств
arecord -l

# Запись тестового аудио (5 секунд)
arecord -d 5 -f cd test.wav

# Воспроизведение для проверки
aplay test.wav

# Если микрофон не работает, настройте в alsamixer:
alsamixer
# Клавиша F4 для выбора устройства захвата
# Стрелками регулируйте уровень
```

#### 1.6 Конфигурация клиента

```bash
# Редактирование config.yaml
nano config.yaml
```

Настройте параметры:

```yaml
speech:
  model_path: "model"  # Путь к модели Vosk
  activation_word: "джарвис"  # Ваше слово активации
  device_index: null  # Используйте python main.py -m для выбора

llm:
  ollama_url: "http://localhost:11434"
  model: "llama3.2:3b"

network:
  server_host: "192.168.1.100"  # IP вашего основного ПК
  server_port: 5000
  api_key: null  # Установите для безопасности
```

### 2. Установка на основном ПК (сервер)

#### 2.1 Установка зависимостей

**Linux/macOS:**
```bash
cd ~/MaybeSomeJarvis-/desktop_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```cmd
cd C:\MaybeSomeJarvis-\desktop_server
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### 2.2 Конфигурация сервера

```bash
nano config.yaml
```

```yaml
server:
  host: "0.0.0.0"  # Слушать на всех интерфейсах
  port: 5000
  api_key: "your-secret-key-123"  # ВАЖНО: установите надежный ключ!

security:
  timeout: 30  # Максимальное время выполнения скрипта
  max_output_size: 10000
```

**ВАЖНО:** Установите одинаковый API ключ на клиенте и сервере!

#### 2.3 Настройка firewall (Linux)

```bash
# Разрешить порт 5000
sudo ufw allow 5000/tcp
```

## Использование

### Запуск сервера (основной ПК)

```bash
cd ~/MaybeSomeJarvis-/desktop_server
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows
python server.py
```

Сервер будет доступен на `http://0.0.0.0:5000`

### Запуск клиента (Orange Pi)

#### Тестирование компонентов

```bash
cd ~/MaybeSomeJarvis-/voice_command_client
source venv/bin/activate

# Список микрофонов
python main.py -m

# Полный тест всех компонентов
python main.py -t

# Одноразовое прослушивание (для теста)
python main.py -o -d 10
```

#### Непрерывное прослушивание

```bash
python main.py
```

Теперь говорите: **"Джарвис, <ваша команда>"**

Примеры команд:
- "Джарвис, открой браузер"
- "Джарвис, покажи текущее время"
- "Джарвис, создай файл hello.txt с текстом привет мир"
- "Джарвис, покажи список файлов в текущей директории"

## Автозапуск (systemd)

### Клиент (Orange Pi)

```bash
sudo nano /etc/systemd/system/voice-command-client.service
```

```ini
[Unit]
Description=Voice Command Client
After=network.target ollama.service

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/MaybeSomeJarvis-/voice_command_client
Environment="PATH=/home/your-username/MaybeSomeJarvis-/voice_command_client/venv/bin"
ExecStart=/home/your-username/MaybeSomeJarvis-/voice_command_client/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable voice-command-client
sudo systemctl start voice-command-client

# Проверка статуса
sudo systemctl status voice-command-client

# Просмотр логов
journalctl -u voice-command-client -f
```

### Сервер (основной ПК)

```bash
sudo nano /etc/systemd/system/voice-command-server.service
```

```ini
[Unit]
Description=Voice Command Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/MaybeSomeJarvis-/desktop_server
Environment="PATH=/home/your-username/MaybeSomeJarvis-/desktop_server/venv/bin"
ExecStart=/home/your-username/MaybeSomeJarvis-/desktop_server/venv/bin/python server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable voice-command-server
sudo systemctl start voice-command-server
sudo systemctl status voice-command-server
```

## Устранение неполадок

### Микрофон не работает

```bash
# Проверка устройств
arecord -l

# Проверка уровней
alsamixer

# Тест записи
arecord -d 5 -f cd test.wav && aplay test.wav
```

### Vosk не распознает речь

- Проверьте, что модель скачана правильно
- Убедитесь, что используется правильная модель (русская/английская)
- Проверьте уровень громкости микрофона
- Говорите четко и не слишком быстро

### Ollama не отвечает

```bash
# Проверка статуса
systemctl status ollama

# Перезапуск
sudo systemctl restart ollama

# Проверка модели
ollama list
ollama pull llama3.2:3b
```

### Сервер недоступен

```bash
# На сервере: проверка, что сервер запущен
ps aux | grep server.py

# Проверка firewall
sudo ufw status

# Проверка сети с клиента
ping 192.168.1.100
curl http://192.168.1.100:5000/health
```

### Ошибки выполнения скриптов

- Проверьте логи сервера: `tail -f desktop_server/server.log`
- Проверьте логи клиента: `tail -f /tmp/voice_command_client.log`
- Убедитесь, что API ключи совпадают

## Безопасность

1. **Обязательно установите API ключ** - без него любой в сети может выполнять код на вашем ПК
2. **Используйте firewall** - разрешите доступ только с IP Orange Pi
3. **Не открывайте порт в интернет** - система предназначена только для локальной сети
4. Регулярно проверяйте логи на подозрительную активность
5. Ограничьте возможности выполняемого кода через настройки безопасности

## Производительность

### Orange Pi Zero 2W (4GB RAM)
- Vosk (распознавание): ~10-20% CPU
- Ollama (llama3.2:3b): ~50-70% CPU, ~2GB RAM при генерации
- Общее потребление RAM: ~2.5-3GB

### Оптимизация
- Используйте `llama3.2:1b` для более быстрой генерации (менее точная)
- Закройте неиспользуемые приложения на Orange Pi
- Используйте легковесную модель Vosk (small версию)

## Расширение возможностей

### Добавление новых команд

LLM автоматически понимает широкий спектр команд. Примеры:

- Работа с файлами: "создай файл", "удали файл", "покажи содержимое"
- Системные операции: "покажи использование процессора", "покажи дату"
- Работа с браузером: "открой сайт example.com"
- Вычисления: "посчитай сумму от 1 до 100"

### Интеграция с умным домом

Добавьте команды для управления устройствами:

```python
# Пример: управление лампой через API
import requests
requests.post('http://smart-lamp/api/toggle')
```

### Работа с базами данных

```python
# Пример: сохранение данных
import sqlite3
conn = sqlite3.connect('data.db')
# ... ваш код
```

## Структура проекта

```
MaybeSomeJarvis-/
├── voice_command_client/          # Клиент для Orange Pi
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── speech_recognition.py  # Модуль распознавания речи (Vosk)
│   │   ├── command_processor.py   # Обработка команд (Ollama)
│   │   └── network_client.py      # Сетевой клиент
│   ├── main.py                    # Главный файл клиента
│   ├── config.yaml                # Конфигурация клиента
│   └── requirements.txt           # Зависимости Python
├── desktop_server/                # Сервер для основного ПК
│   ├── server.py                  # Главный файл сервера
│   ├── config.yaml                # Конфигурация сервера
│   └── requirements.txt           # Зависимости Python
└── README.md                      # Эта документация
```

## API сервера

### Endpoints

#### `GET /health`
Проверка здоровья сервера.

**Ответ:**
```json
{"status": "ok"}
```

#### `GET /status`
Информация о сервере.

**Ответ:**
```json
{
  "status": "running",
  "executed_commands": 42,
  "last_execution": {...}
}
```

#### `POST /execute`
Выполнение Python скрипта.

**Заголовки:**
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Тело запроса:**
```json
{
  "code": "print('Hello, World!')",
  "description": "Test command"
}
```

**Ответ (успех):**
```json
{
  "success": true,
  "output": "Hello, World!\n",
  "execution_id": "uuid-here"
}
```

**Ответ (ошибка):**
```json
{
  "success": false,
  "error": "Error message"
}
```

#### `GET /history?limit=10`
История выполненных команд (требует API ключ).

## Лицензия

MIT License

## Автор

Создано с помощью Claude AI

## Поддержка

При возникновении проблем:
1. Проверьте логи клиента и сервера
2. Убедитесь, что все зависимости установлены
3. Проверьте сетевое соединение
4. Создайте issue в репозитории с описанием проблемы

## TODO

- [ ] Добавить поддержку контекста диалога
- [ ] Реализовать голосовые ответы (TTS)
- [ ] Добавить веб-интерфейс для управления
- [ ] Поддержка множественных клиентов
- [ ] Мониторинг производительности
- [ ] Docker контейнеры для упрощенной установки
