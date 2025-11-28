"""
Модуль обработки голосовых команд и генерации Python скриптов
Использует локальную LLM через Ollama
"""
import requests
import json
import logging

logger = logging.getLogger(__name__)


class CommandProcessor:
    def __init__(self, ollama_url="http://localhost:11434", model="llama3.2:3b"):
        """
        Инициализация процессора команд

        Args:
            ollama_url: URL Ollama API
            model: название модели (llama3.2:3b оптимальна для 4GB RAM)
        """
        self.ollama_url = ollama_url
        self.model = model
        self.api_endpoint = f"{ollama_url}/api/generate"

        logger.info(f"Процессор команд инициализирован: {model}")

    def process_command(self, command_text):
        """
        Обработка голосовой команды и генерация Python скрипта

        Args:
            command_text: текст распознанной команды

        Returns:
            str: сгенерированный Python код или None
        """
        logger.info(f"Обработка команды: {command_text}")

        prompt = self._build_prompt(command_text)

        try:
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Низкая температура для более предсказуемого кода
                        "top_p": 0.9,
                        "num_predict": 512  # Ограничение длины ответа
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')

                # Извлечение Python кода из ответа
                python_code = self._extract_python_code(generated_text)

                if python_code:
                    logger.info(f"Сгенерирован Python код:\n{python_code}")
                    return python_code
                else:
                    logger.warning("Не удалось извлечь Python код из ответа")
                    return None

            else:
                logger.error(f"Ошибка API Ollama: {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Таймаут при обращении к Ollama")
            return None
        except Exception as e:
            logger.error(f"Ошибка при обработке команды: {e}")
            return None

    def _build_prompt(self, command_text):
        """Формирование промпта для LLM"""
        prompt = f"""Ты - ассистент, который конвертирует голосовые команды в Python скрипты.

Команда пользователя: "{command_text}"

Сгенерируй Python скрипт, который выполняет эту команду. Скрипт должен быть:
- Простым и понятным
- Безопасным (без опасных операций)
- Готовым к выполнению
- С обработкой базовых ошибок

Верни ТОЛЬКО Python код без объяснений. Обрами код в ```python и ```.

Примеры:

Команда: "открой браузер"
```python
import webbrowser
webbrowser.open('https://www.google.com')
print("Браузер открыт")
```

Команда: "покажи текущее время"
```python
from datetime import datetime
now = datetime.now()
print(f"Текущее время: {{now.strftime('%H:%M:%S')}}")
```

Команда: "создай файл hello.txt с текстом привет мир"
```python
with open('hello.txt', 'w', encoding='utf-8') as f:
    f.write('привет мир')
print("Файл создан")
```

Теперь сгенерируй код для команды выше:"""

        return prompt

    def _extract_python_code(self, text):
        """
        Извлечение Python кода из ответа LLM

        Args:
            text: текст ответа

        Returns:
            str: извлеченный Python код
        """
        # Поиск кода между ```python и ```
        if '```python' in text:
            start = text.find('```python') + len('```python')
            end = text.find('```', start)
            if end != -1:
                code = text[start:end].strip()
                return code

        # Поиск кода между ``` и ``` (без указания языка)
        if '```' in text:
            parts = text.split('```')
            if len(parts) >= 3:
                code = parts[1].strip()
                # Удаление первой строки, если это метка языка
                lines = code.split('\n')
                if lines[0].strip() in ['python', 'py']:
                    code = '\n'.join(lines[1:])
                return code.strip()

        # Если нет маркеров кода, возвращаем весь текст (возможно, это чистый код)
        # Но только если он начинается с типичных Python конструкций
        text = text.strip()
        python_keywords = ['import ', 'from ', 'def ', 'class ', 'if ', 'for ', 'while ', 'with ', 'print(']
        if any(text.startswith(kw) for kw in python_keywords):
            return text

        return None

    def validate_code(self, code):
        """
        Базовая валидация Python кода

        Args:
            code: Python код для проверки

        Returns:
            tuple: (bool, str) - валидность и сообщение об ошибке
        """
        if not code or not code.strip():
            return False, "Пустой код"

        # Проверка синтаксиса
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            return False, f"Синтаксическая ошибка: {e}"

        # Проверка на опасные операции
        dangerous_patterns = [
            'os.system',
            'subprocess.call',
            'subprocess.popen',
            'eval(',
            'exec(',
            '__import__',
            'rm -rf',
            'pickle.loads',
            'compile(',
        ]

        code_lower = code.lower()
        for pattern in dangerous_patterns:
            if pattern.lower() in code_lower:
                logger.warning(f"Обнаружена потенциально опасная операция: {pattern}")
                # Не блокируем, но предупреждаем
                # return False, f"Обнаружена опасная операция: {pattern}"

        return True, "OK"
