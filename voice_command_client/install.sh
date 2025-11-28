#!/bin/bash
# Скрипт установки Voice Command Client на Orange Pi Zero 2W

set -e

echo "=================================="
echo "Voice Command Client - Установка"
echo "=================================="
echo ""

# Проверка прав root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Не запускайте этот скрипт от root!"
    echo "   Используйте обычного пользователя, sudo будет вызван при необходимости"
    exit 1
fi

# Проверка архитектуры
ARCH=$(uname -m)
echo "Архитектура: $ARCH"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "armv7l" ]]; then
    echo "⚠️  Предупреждение: Orange Pi обычно использует aarch64 или armv7l"
fi
echo ""

# 1. Обновление системы
echo "📦 1. Обновление системы..."
sudo apt update
sudo apt upgrade -y
echo "✓ Система обновлена"
echo ""

# 2. Установка системных зависимостей
echo "📦 2. Установка системных зависимостей..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    python3-pyaudio \
    libasound2-dev \
    git \
    curl \
    wget \
    unzip \
    alsa-utils

echo "✓ Системные зависимости установлены"
echo ""

# 3. Установка Ollama
echo "🤖 3. Установка Ollama..."
if command -v ollama &> /dev/null; then
    echo "✓ Ollama уже установлена"
else
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✓ Ollama установлена"
fi

# Запуск Ollama
sudo systemctl enable ollama
sudo systemctl start ollama
echo "✓ Ollama запущена"
echo ""

# 4. Создание виртуального окружения
echo "🐍 4. Создание виртуального окружения Python..."
if [ -d "venv" ]; then
    echo "⚠️  venv уже существует, пропуск..."
else
    python3 -m venv venv
    echo "✓ Виртуальное окружение создано"
fi
echo ""

# 5. Установка зависимостей Python
echo "📚 5. Установка зависимостей Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Зависимости Python установлены"
echo ""

# 6. Скачивание модели Vosk
echo "🗣️  6. Скачивание модели Vosk..."
if [ -d "model" ]; then
    echo "✓ Модель уже существует"
else
    echo "   Скачивание русской модели (45 MB)..."
    wget -q --show-progress https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
    unzip -q vosk-model-small-ru-0.22.zip
    mv vosk-model-small-ru-0.22 model
    rm vosk-model-small-ru-0.22.zip
    echo "✓ Модель Vosk скачана"
fi
echo ""

# 7. Установка модели LLM
echo "🧠 7. Установка модели LLM (может занять несколько минут)..."
if ollama list | grep -q "llama3.2:3b"; then
    echo "✓ Модель llama3.2:3b уже установлена"
else
    echo "   Скачивание llama3.2:3b (~2 GB)..."
    ollama pull llama3.2:3b
    echo "✓ Модель llama3.2:3b установлена"
fi
echo ""

# 8. Проверка микрофона
echo "🎤 8. Проверка микрофона..."
arecord -l
echo ""
echo "   Если микрофон не виден, подключите его и перезапустите установку"
echo ""

# 9. Настройка конфигурации
echo "⚙️  9. Настройка конфигурации..."
if [ ! -f "config.yaml" ]; then
    echo "❌ Файл config.yaml не найден!"
    exit 1
fi

echo "   Необходимо настроить config.yaml:"
echo "   - server_host: IP адрес вашего основного ПК"
echo "   - api_key: секретный ключ (опционально, но рекомендуется)"
echo ""
read -p "   Открыть config.yaml для редактирования? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    nano config.yaml
fi
echo ""

# 10. Тестирование
echo "🧪 10. Тестирование установки..."
echo ""
read -p "   Запустить тесты? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python main.py -t
fi
echo ""

# 11. Установка systemd сервиса
echo "🚀 11. Установка systemd сервиса..."
read -p "   Установить автозапуск через systemd? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Обновление путей в сервисе
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)

    sed "s|User=orangepi|User=$CURRENT_USER|g" voice-command-client.service | \
    sed "s|Group=orangepi|Group=$CURRENT_USER|g" | \
    sed "s|/home/orangepi/MaybeSomeJarvis-/voice_command_client|$CURRENT_DIR|g" | \
    sudo tee /etc/systemd/system/voice-command-client.service > /dev/null

    sudo systemctl daemon-reload
    sudo systemctl enable voice-command-client

    echo "✓ Systemd сервис установлен"
    echo ""
    echo "   Команды управления сервисом:"
    echo "   sudo systemctl start voice-command-client    # Запуск"
    echo "   sudo systemctl stop voice-command-client     # Остановка"
    echo "   sudo systemctl status voice-command-client   # Статус"
    echo "   journalctl -u voice-command-client -f        # Логи"
fi
echo ""

# Завершение
echo "=================================="
echo "✅ Установка завершена!"
echo "=================================="
echo ""
echo "Следующие шаги:"
echo ""
echo "1. Настройте config.yaml (если еще не сделали):"
echo "   nano config.yaml"
echo ""
echo "2. Запустите клиент:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. Или запустите как сервис:"
echo "   sudo systemctl start voice-command-client"
echo ""
echo "4. Говорите: 'Джарвис, <ваша команда>'"
echo ""
echo "Документация: README.md"
echo ""
