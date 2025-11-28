#!/bin/bash
# Скрипт установки Voice Command Server для основного ПК

set -e

echo "=================================="
echo "Voice Command Server - Установка"
echo "=================================="
echo ""

# Проверка прав root
if [ "$EUID" -eq 0 ]; then
    echo "❌ Не запускайте этот скрипт от root!"
    echo "   Используйте обычного пользователя, sudo будет вызван при необходимости"
    exit 1
fi

# Определение ОС
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
else
    OS="Unknown"
fi

echo "Операционная система: $OS"
echo ""

# 1. Проверка Python
echo "🐍 1. Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден!"
    echo "   Установите Python 3.8 или выше:"
    if [ "$OS" = "Linux" ]; then
        echo "   sudo apt install python3 python3-pip python3-venv"
    elif [ "$OS" = "macOS" ]; then
        echo "   brew install python3"
    fi
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION найден"
echo ""

# 2. Создание виртуального окружения
echo "📦 2. Создание виртуального окружения..."
if [ -d "venv" ]; then
    echo "⚠️  venv уже существует, пропуск..."
else
    python3 -m venv venv
    echo "✓ Виртуальное окружение создано"
fi
echo ""

# 3. Установка зависимостей
echo "📚 3. Установка зависимостей Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Зависимости установлены"
echo ""

# 4. Настройка конфигурации
echo "⚙️  4. Настройка конфигурации..."
if [ ! -f "config.yaml" ]; then
    echo "❌ Файл config.yaml не найден!"
    exit 1
fi

echo "   ВАЖНО: Установите надежный API ключ в config.yaml"
echo "   Это предотвратит несанкционированное выполнение кода на вашем ПК!"
echo ""
read -p "   Открыть config.yaml для редактирования? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v nano &> /dev/null; then
        nano config.yaml
    elif command -v vim &> /dev/null; then
        vim config.yaml
    else
        echo "   Редактор не найден. Откройте вручную: nano config.yaml"
    fi
fi
echo ""

# 5. Настройка firewall (только Linux)
if [ "$OS" = "Linux" ]; then
    echo "🔥 5. Настройка firewall..."
    if command -v ufw &> /dev/null; then
        read -p "   Разрешить порт 5000 в firewall? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo ufw allow 5000/tcp
            echo "✓ Порт 5000 разрешен"
        fi
    else
        echo "   ufw не найден, пропуск настройки firewall"
    fi
    echo ""
fi

# 6. Тестовый запуск
echo "🧪 6. Тестовый запуск..."
read -p "   Запустить сервер для проверки? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "   Сервер запускается..."
    echo "   Проверьте в браузере: http://localhost:5000/health"
    echo "   Нажмите Ctrl+C для остановки"
    echo ""
    sleep 2
    python server.py &
    SERVER_PID=$!
    sleep 3

    # Тест здоровья
    if command -v curl &> /dev/null; then
        if curl -s http://localhost:5000/health | grep -q "ok"; then
            echo "   ✓ Сервер работает!"
        else
            echo "   ⚠️  Сервер не отвечает"
        fi
    fi

    echo ""
    read -p "   Нажмите Enter для остановки сервера..."
    kill $SERVER_PID 2>/dev/null || true
fi
echo ""

# 7. Установка systemd сервиса (только Linux)
if [ "$OS" = "Linux" ]; then
    echo "🚀 7. Установка systemd сервиса..."
    read -p "   Установить автозапуск через systemd? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        CURRENT_USER=$(whoami)
        CURRENT_DIR=$(pwd)

        sed "s|User=youruser|User=$CURRENT_USER|g" voice-command-server.service | \
        sed "s|Group=youruser|Group=$CURRENT_USER|g" | \
        sed "s|/home/youruser/MaybeSomeJarvis-/desktop_server|$CURRENT_DIR|g" | \
        sudo tee /etc/systemd/system/voice-command-server.service > /dev/null

        sudo systemctl daemon-reload
        sudo systemctl enable voice-command-server

        echo "✓ Systemd сервис установлен"
        echo ""
        echo "   Команды управления сервисом:"
        echo "   sudo systemctl start voice-command-server    # Запуск"
        echo "   sudo systemctl stop voice-command-server     # Остановка"
        echo "   sudo systemctl status voice-command-server   # Статус"
        echo "   journalctl -u voice-command-server -f        # Логи"
    fi
    echo ""
fi

# Завершение
echo "=================================="
echo "✅ Установка завершена!"
echo "=================================="
echo ""
echo "Следующие шаги:"
echo ""
echo "1. Настройте config.yaml (если еще не сделали):"
echo "   - Установите надежный API ключ"
echo "   - Настройте параметры безопасности"
echo ""
echo "2. Запустите сервер:"
if [ "$OS" = "Linux" ]; then
    echo "   Вариант A (вручную):"
fi
echo "   source venv/bin/activate"
echo "   python server.py"
echo ""
if [ "$OS" = "Linux" ]; then
    echo "   Вариант B (как сервис):"
    echo "   sudo systemctl start voice-command-server"
    echo ""
fi
echo "3. Получите IP адрес этого компьютера:"
if [ "$OS" = "Linux" ]; then
    echo "   ip addr show | grep 'inet '"
elif [ "$OS" = "macOS" ]; then
    echo "   ifconfig | grep 'inet '"
fi
echo ""
echo "4. Настройте клиент на Orange Pi:"
echo "   - Установите server_host в IP адрес этого ПК"
echo "   - Установите тот же API ключ"
echo ""
echo "Документация: README.md"
echo ""
