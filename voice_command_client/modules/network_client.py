"""
Модуль сетевого клиента для отправки Python скриптов на основной ПК
"""
import requests
import json
import logging
import socket

logger = logging.getLogger(__name__)


class NetworkClient:
    def __init__(self, server_host, server_port=5000, api_key=None):
        """
        Инициализация сетевого клиента

        Args:
            server_host: IP-адрес или hostname основного ПК
            server_port: порт сервера
            api_key: ключ API для аутентификации
        """
        self.server_host = server_host
        self.server_port = server_port
        self.api_key = api_key
        self.base_url = f"http://{server_host}:{server_port}"

        logger.info(f"Сетевой клиент инициализирован: {self.base_url}")

    def check_connection(self):
        """
        Проверка доступности сервера

        Returns:
            bool: True если сервер доступен
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Сервер недоступен: {e}")
            return False

    def send_script(self, python_code, description=""):
        """
        Отправка Python скрипта на сервер для выполнения

        Args:
            python_code: Python код для выполнения
            description: описание команды

        Returns:
            dict: результат выполнения или None при ошибке
        """
        logger.info(f"Отправка скрипта на сервер: {description}")

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['X-API-Key'] = self.api_key

        payload = {
            'code': python_code,
            'description': description
        }

        try:
            response = requests.post(
                f"{self.base_url}/execute",
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Скрипт выполнен успешно")
                logger.info(f"Результат: {result.get('output', '')}")
                return result
            elif response.status_code == 401:
                logger.error("Ошибка аутентификации")
                return None
            elif response.status_code == 400:
                error = response.json().get('error', 'Unknown error')
                logger.error(f"Ошибка выполнения: {error}")
                return {'success': False, 'error': error}
            else:
                logger.error(f"Ошибка сервера: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Таймаут при отправке скрипта")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Не удалось подключиться к серверу {self.base_url}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при отправке скрипта: {e}")
            return None

    def get_status(self):
        """
        Получение статуса сервера

        Returns:
            dict: информация о сервере
        """
        try:
            response = requests.get(
                f"{self.base_url}/status",
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Ошибка при получении статуса: {e}")
            return None

    def test_connection(self):
        """
        Тестовая проверка соединения с сервером

        Returns:
            bool: успешность теста
        """
        logger.info("Тестирование соединения с сервером...")

        # Проверка доступности хоста
        try:
            socket.create_connection((self.server_host, self.server_port), timeout=5)
            logger.info(f"Порт {self.server_port} доступен")
        except socket.error as e:
            logger.error(f"Порт {self.server_port} недоступен: {e}")
            return False

        # Проверка HTTP endpoint
        if self.check_connection():
            logger.info("HTTP сервер отвечает")
            return True
        else:
            logger.error("HTTP сервер не отвечает")
            return False
