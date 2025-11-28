#!/usr/bin/env python3
"""
Главный модуль системы голосового управления для Orange Pi Zero 2W

Алгоритм работы:
1. Прослушивание микрофона
2. Распознавание речи (Vosk)
3. Обработка команды через LLM (Ollama)
4. Генерация Python скрипта
5. Отправка скрипта на основной ПК
6. Выполнение скрипта на ПК
"""
import sys
import os
import yaml
import logging
import argparse
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, os.path.dirname(__file__))

from modules import SpeechRecognizer, CommandProcessor, NetworkClient


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/voice_command_client.log')
    ]
)
logger = logging.getLogger(__name__)


class VoiceCommandClient:
    def __init__(self, config_path='config.yaml'):
        """
        Инициализация клиента голосового управления

        Args:
            config_path: путь к файлу конфигурации
        """
        logger.info("Инициализация системы голосового управления...")

        # Загрузка конфигурации
        self.config = self._load_config(config_path)

        # Инициализация компонентов
        self.speech_recognizer = None
        self.command_processor = None
        self.network_client = None

        self._init_components()

    def _load_config(self, config_path):
        """Загрузка конфигурации"""
        config_file = Path(config_path)

        if not config_file.exists():
            logger.warning(f"Конфигурационный файл не найден: {config_path}")
            logger.info("Использование конфигурации по умолчанию")
            return self._default_config()

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Конфигурация загружена из {config_path}")
                return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            return self._default_config()

    def _default_config(self):
        """Конфигурация по умолчанию"""
        return {
            'speech': {
                'model_path': 'model',
                'sample_rate': 16000,
                'activation_word': 'джарвис',
                'device_index': None
            },
            'llm': {
                'ollama_url': 'http://localhost:11434',
                'model': 'llama3.2:3b'
            },
            'network': {
                'server_host': '192.168.1.100',
                'server_port': 5000,
                'api_key': None
            }
        }

    def _init_components(self):
        """Инициализация всех компонентов"""
        try:
            # Распознаватель речи
            speech_config = self.config['speech']
            self.speech_recognizer = SpeechRecognizer(
                model_path=speech_config['model_path'],
                sample_rate=speech_config['sample_rate']
            )
            logger.info("✓ Распознаватель речи инициализирован")

            # Процессор команд
            llm_config = self.config['llm']
            self.command_processor = CommandProcessor(
                ollama_url=llm_config['ollama_url'],
                model=llm_config['model']
            )
            logger.info("✓ Процессор команд инициализирован")

            # Сетевой клиент
            network_config = self.config['network']
            self.network_client = NetworkClient(
                server_host=network_config['server_host'],
                server_port=network_config['server_port'],
                api_key=network_config.get('api_key')
            )
            logger.info("✓ Сетевой клиент инициализирован")

        except Exception as e:
            logger.error(f"Ошибка при инициализации компонентов: {e}")
            raise

    def list_microphones(self):
        """Вывод списка доступных микрофонов"""
        devices = self.speech_recognizer.list_microphones()
        print("\nДоступные микрофоны:")
        for device in devices:
            print(f"  [{device['index']}] {device['name']} ({device['channels']} каналов)")
        print()

    def test_components(self):
        """Тестирование всех компонентов"""
        logger.info("Запуск тестов компонентов...")

        # Тест сети
        print("\n1. Проверка соединения с сервером...")
        if self.network_client.test_connection():
            print("   ✓ Сервер доступен")
        else:
            print("   ✗ Сервер недоступен")

        # Тест микрофона
        print("\n2. Список доступных микрофонов:")
        self.list_microphones()

        # Тест распознавания
        print("\n3. Тест распознавания речи (скажите что-нибудь в течение 5 секунд)...")
        text = self.speech_recognizer.listen_and_recognize(
            duration=5,
            activation_word=None  # Без слова активации для теста
        )
        if text:
            print(f"   ✓ Распознано: '{text}'")
        else:
            print("   ✗ Речь не распознана")

        # Тест LLM
        print("\n4. Тест генерации кода...")
        code = self.command_processor.process_command("покажи текущее время")
        if code:
            print(f"   ✓ Код сгенерирован:\n{code}")
        else:
            print("   ✗ Не удалось сгенерировать код")

        print("\nТестирование завершено\n")

    def process_voice_command(self, command_text):
        """
        Обработка одной голосовой команды

        Args:
            command_text: текст распознанной команды
        """
        logger.info(f"Обработка команды: '{command_text}'")

        # Генерация Python кода
        python_code = self.command_processor.process_command(command_text)

        if not python_code:
            logger.error("Не удалось сгенерировать код")
            print("❌ Не удалось обработать команду")
            return

        # Валидация кода
        is_valid, message = self.command_processor.validate_code(python_code)
        if not is_valid:
            logger.error(f"Невалидный код: {message}")
            print(f"❌ Невалидный код: {message}")
            return

        logger.info("Код прошел валидацию")
        print(f"\n📝 Сгенерирован код:\n{'-'*50}\n{python_code}\n{'-'*50}\n")

        # Отправка на сервер
        result = self.network_client.send_script(python_code, command_text)

        if result and result.get('success'):
            print(f"✅ Команда выполнена успешно")
            if result.get('output'):
                print(f"\n📤 Результат:\n{result['output']}")
        else:
            error = result.get('error', 'Неизвестная ошибка') if result else 'Ошибка соединения'
            print(f"❌ Ошибка выполнения: {error}")

    def run_continuous(self):
        """Запуск в режиме непрерывного прослушивания"""
        logger.info("Запуск в режиме непрерывного прослушивания...")

        activation_word = self.config['speech']['activation_word']
        device_index = self.config['speech'].get('device_index')

        print(f"\n🎤 Слушаю... (Скажите '{activation_word}' + команда)")
        print("   Нажмите Ctrl+C для остановки\n")

        try:
            self.speech_recognizer.listen_continuously(
                callback=self.process_voice_command,
                device_index=device_index,
                activation_word=activation_word
            )
        except KeyboardInterrupt:
            print("\n\n👋 Остановка системы...")
            logger.info("Система остановлена пользователем")

    def run_once(self, duration=5):
        """
        Одноразовое прослушивание

        Args:
            duration: длительность записи в секундах
        """
        logger.info("Запуск в режиме одноразового прослушивания...")

        activation_word = self.config['speech']['activation_word']
        device_index = self.config['speech'].get('device_index')

        print(f"\n🎤 Говорите (скажите '{activation_word}' + команда)...")

        text = self.speech_recognizer.listen_and_recognize(
            duration=duration,
            device_index=device_index,
            activation_word=activation_word
        )

        if text:
            print(f"\n✓ Распознано: '{text}'\n")
            self.process_voice_command(text)
        else:
            print("\n❌ Команда не распознана или слово активации не обнаружено\n")


def main():
    """Главная функция"""
    parser = argparse.ArgumentParser(
        description='Система голосового управления для Orange Pi Zero 2W'
    )
    parser.add_argument(
        '-c', '--config',
        default='config.yaml',
        help='Путь к файлу конфигурации'
    )
    parser.add_argument(
        '-t', '--test',
        action='store_true',
        help='Запустить тесты компонентов'
    )
    parser.add_argument(
        '-m', '--list-mics',
        action='store_true',
        help='Показать список микрофонов'
    )
    parser.add_argument(
        '-o', '--once',
        action='store_true',
        help='Одноразовое прослушивание (по умолчанию: непрерывное)'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=5,
        help='Длительность записи для одноразового режима (секунды)'
    )

    args = parser.parse_args()

    try:
        client = VoiceCommandClient(config_path=args.config)

        if args.list_mics:
            client.list_microphones()
        elif args.test:
            client.test_components()
        elif args.once:
            client.run_once(duration=args.duration)
        else:
            client.run_continuous()

    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
