# Быстрый старт

Это краткое руководство по запуску системы голосового управления. Для полной документации см. [README.md](README.md).

## За 5 минут

### 1. На Orange Pi Zero 2W (клиент)

```bash
cd ~/MaybeSomeJarvis-/voice_command_client
./install.sh
```

Следуйте инструкциям установщика. Он автоматически:
- Установит все зависимости
- Скачает модели Vosk и LLM
- Настроит окружение

После установки:
```bash
# Отредактируйте config.yaml (укажите IP вашего ПК)
nano config.yaml

# Запустите
source venv/bin/activate
python main.py
```

### 2. На основном ПК (сервер)

```bash
cd ~/MaybeSomeJarvis-/desktop_server
./install.sh
```

После установки:
```bash
# Отредактируйте config.yaml (установите API ключ)
nano config.yaml

# Запустите
source venv/bin/activate
python server.py
```

### 3. Использование

Говорите в микрофон:
```
"Джарвис, открой браузер"
"Джарвис, покажи текущее время"
"Джарвис, создай файл hello.txt"
```

## Ручная установка

### Orange Pi (клиент)

```bash
# Установите зависимости
sudo apt install python3 python3-pip python3-venv portaudio19-dev

# Установите Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b

# Скачайте модель Vosk
cd voice_command_client
wget https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip vosk-model-small-ru-0.22.zip
mv vosk-model-small-ru-0.22 model

# Python окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройте config.yaml
nano config.yaml

# Запустите
python main.py
```

### Основной ПК (сервер)

```bash
cd desktop_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройте config.yaml
nano config.yaml

# Запустите
python server.py
```

## Проверка работоспособности

### На клиенте:
```bash
# Список микрофонов
python main.py -m

# Тесты
python main.py -t

# Одноразовое прослушивание
python main.py -o
```

### На сервере:
```bash
# Проверка здоровья
curl http://localhost:5000/health

# Должно вернуть: {"status": "ok"}
```

## Устранение проблем

### Микрофон не работает
```bash
arecord -l  # Список устройств
alsamixer   # Настройка уровня
```

### Сервер недоступен
```bash
# На сервере
sudo ufw allow 5000/tcp

# На клиенте
ping <IP сервера>
curl http://<IP сервера>:5000/health
```

### Ollama не работает
```bash
sudo systemctl status ollama
ollama list
ollama pull llama3.2:3b
```

## Автозапуск

### Клиент:
```bash
sudo systemctl enable voice-command-client
sudo systemctl start voice-command-client
```

### Сервер:
```bash
sudo systemctl enable voice-command-server
sudo systemctl start voice-command-server
```

## Команды для управления

### Клиент (Orange Pi):
```bash
# Логи
journalctl -u voice-command-client -f

# Перезапуск
sudo systemctl restart voice-command-client

# Остановка
sudo systemctl stop voice-command-client
```

### Сервер (основной ПК):
```bash
# Логи
journalctl -u voice-command-server -f

# Перезапуск
sudo systemctl restart voice-command-server

# Остановка
sudo systemctl stop voice-command-server
```

## Примеры команд

- "Джарвис, открой браузер"
- "Джарвис, покажи текущее время"
- "Джарвис, создай файл test.txt с текстом hello world"
- "Джарвис, покажи список файлов"
- "Джарвис, посчитай факториал 10"

## Следующие шаги

- Прочитайте полную документацию в [README.md](README.md)
- Настройте API ключ для безопасности
- Попробуйте различные команды
- Настройте автозапуск

---

Нужна помощь? См. раздел "Устранение неполадок" в README.md
