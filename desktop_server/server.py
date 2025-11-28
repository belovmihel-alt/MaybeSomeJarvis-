#!/usr/bin/env python3
"""
Сервер для приема и выполнения Python скриптов от Orange Pi
Запускается на основном ПК
"""
import os
import sys
import yaml
import logging
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from functools import wraps

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Глобальная конфигурация
CONFIG = {}

# История выполненных команд
EXECUTION_HISTORY = []


def load_config(config_path='config.yaml'):
    """Загрузка конфигурации сервера"""
    config_file = Path(config_path)

    if not config_file.exists():
        logger.warning(f"Конфигурационный файл не найден: {config_path}")
        return {
            'server': {
                'host': '0.0.0.0',
                'port': 5000,
                'api_key': None
            },
            'security': {
                'allowed_modules': ['os', 'sys', 'datetime', 'time', 'webbrowser', 'random'],
                'timeout': 30,
                'max_output_size': 10000
            }
        }

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            logger.info(f"Конфигурация загружена из {config_path}")
            return config
    except Exception as e:
        logger.error(f"Ошибка при загрузке конфигурации: {e}")
        raise


def require_api_key(f):
    """Декоратор для проверки API ключа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = CONFIG['server'].get('api_key')

        # Если API ключ не настроен, пропускаем проверку
        if not api_key:
            return f(*args, **kwargs)

        # Проверка ключа в заголовке
        provided_key = request.headers.get('X-API-Key')

        if not provided_key or provided_key != api_key:
            logger.warning(f"Неверный API ключ от {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401

        return f(*args, **kwargs)

    return decorated_function


@app.route('/health', methods=['GET'])
def health():
    """Проверка здоровья сервера"""
    return jsonify({'status': 'ok'}), 200


@app.route('/status', methods=['GET'])
def status():
    """Информация о сервере"""
    return jsonify({
        'status': 'running',
        'executed_commands': len(EXECUTION_HISTORY),
        'last_execution': EXECUTION_HISTORY[-1] if EXECUTION_HISTORY else None
    }), 200


@app.route('/execute', methods=['POST'])
@require_api_key
def execute_script():
    """
    Прием и выполнение Python скрипта

    Ожидает JSON:
    {
        "code": "python код",
        "description": "описание команды"
    }
    """
    try:
        data = request.get_json()

        if not data or 'code' not in data:
            return jsonify({'error': 'Missing code parameter'}), 400

        code = data['code']
        description = data.get('description', 'Unnamed command')

        logger.info(f"Получен скрипт от {request.remote_addr}: {description}")
        logger.debug(f"Код:\n{code}")

        # Проверка безопасности
        security_check = check_code_security(code)
        if not security_check['safe']:
            logger.warning(f"Небезопасный код отклонен: {security_check['reason']}")
            return jsonify({
                'success': False,
                'error': f"Код отклонен: {security_check['reason']}"
            }), 400

        # Выполнение кода
        result = execute_python_code(code)

        # Сохранение в историю
        execution_record = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'description': description,
            'client_ip': request.remote_addr,
            'success': result['success'],
            'output': result.get('output', ''),
            'error': result.get('error', '')
        }
        EXECUTION_HISTORY.append(execution_record)

        # Ограничение размера истории
        if len(EXECUTION_HISTORY) > 100:
            EXECUTION_HISTORY.pop(0)

        if result['success']:
            logger.info(f"Скрипт выполнен успешно: {description}")
            return jsonify({
                'success': True,
                'output': result['output'],
                'execution_id': execution_record['id']
            }), 200
        else:
            logger.error(f"Ошибка выполнения скрипта: {result['error']}")
            return jsonify({
                'success': False,
                'error': result['error']
            }), 400

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def check_code_security(code):
    """
    Проверка безопасности кода

    Returns:
        dict: {'safe': bool, 'reason': str}
    """
    # Проверка на очевидно опасные операции
    dangerous_patterns = [
        ('rm -rf', 'Опасная команда удаления файлов'),
        ('__import__("os").system', 'Попытка выполнения системных команд'),
        ('subprocess.Popen', 'Попытка запуска процессов'),
        ('open(', 'Работа с файлами (может быть опасна)'),  # Предупреждение, но не блокировка
    ]

    code_lower = code.lower()

    for pattern, reason in dangerous_patterns:
        if pattern.lower() in code_lower:
            # Для некоторых паттернов только предупреждаем
            if pattern == 'open(':
                logger.warning(f"Код содержит работу с файлами: {reason}")
                continue
            return {'safe': False, 'reason': reason}

    # Проверка синтаксиса
    try:
        compile(code, '<string>', 'exec')
    except SyntaxError as e:
        return {'safe': False, 'reason': f'Синтаксическая ошибка: {e}'}

    return {'safe': True, 'reason': 'OK'}


def execute_python_code(code):
    """
    Выполнение Python кода в безопасном окружении

    Args:
        code: Python код для выполнения

    Returns:
        dict: {'success': bool, 'output': str, 'error': str}
    """
    # Создание временного файла
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(code)
        temp_file = f.name

    try:
        # Выполнение кода в отдельном процессе
        timeout = CONFIG['security'].get('timeout', 30)

        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace'
        )

        # Ограничение размера вывода
        max_output_size = CONFIG['security'].get('max_output_size', 10000)
        stdout = result.stdout[:max_output_size] if result.stdout else ''
        stderr = result.stderr[:max_output_size] if result.stderr else ''

        if result.returncode == 0:
            return {
                'success': True,
                'output': stdout,
                'error': stderr if stderr else None
            }
        else:
            return {
                'success': False,
                'output': stdout,
                'error': stderr or f"Exit code: {result.returncode}"
            }

    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут выполнения кода (>{timeout}s)")
        return {
            'success': False,
            'error': f'Превышен таймаут выполнения ({timeout}s)'
        }
    except Exception as e:
        logger.error(f"Ошибка при выполнении кода: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
    finally:
        # Удаление временного файла
        try:
            os.unlink(temp_file)
        except:
            pass


@app.route('/history', methods=['GET'])
@require_api_key
def get_history():
    """Получение истории выполненных команд"""
    limit = request.args.get('limit', 10, type=int)
    return jsonify({
        'history': EXECUTION_HISTORY[-limit:]
    }), 200


def main():
    """Главная функция"""
    global CONFIG

    import argparse
    parser = argparse.ArgumentParser(description='Сервер для выполнения Python скриптов')
    parser.add_argument('-c', '--config', default='config.yaml', help='Путь к конфигурации')
    args = parser.parse_args()

    try:
        # Загрузка конфигурации
        CONFIG = load_config(args.config)

        server_config = CONFIG['server']
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 5000)
        api_key = server_config.get('api_key')

        logger.info("=" * 50)
        logger.info("Сервер выполнения Python скриптов")
        logger.info("=" * 50)
        logger.info(f"Адрес: {host}:{port}")
        logger.info(f"API ключ: {'настроен' if api_key else 'не настроен (небезопасно!)'}")
        logger.info("=" * 50)

        # Запуск сервера
        app.run(
            host=host,
            port=port,
            debug=False,
            threaded=True
        )

    except KeyboardInterrupt:
        logger.info("\nСервер остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
