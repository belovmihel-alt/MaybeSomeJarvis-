"""
Модуль распознавания речи для Orange Pi Zero 2W
Использует Vosk для офлайн распознавания (легковесный вариант для ARM)
"""
import os
import json
import wave
import pyaudio
from vosk import Model, KaldiRecognizer
import logging

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self, model_path="model", sample_rate=16000, chunk_size=8000):
        """
        Инициализация распознавателя речи

        Args:
            model_path: путь к модели Vosk
            sample_rate: частота дискретизации (16000 Hz для Vosk)
            chunk_size: размер буфера
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size

        # Загрузка модели Vosk
        if not os.path.exists(model_path):
            raise ValueError(f"Модель не найдена: {model_path}. "
                           "Скачайте модель с https://alphacephei.com/vosk/models")

        logger.info(f"Загрузка модели Vosk из {model_path}...")
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, sample_rate)

        # Настройка PyAudio
        self.audio = pyaudio.PyAudio()
        logger.info("Распознаватель речи инициализирован")

    def list_microphones(self):
        """Список доступных микрофонов"""
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        devices = []
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                devices.append({
                    'index': i,
                    'name': device_info.get('name'),
                    'channels': device_info.get('maxInputChannels')
                })
        return devices

    def listen_and_recognize(self, duration=5, device_index=None, activation_word="джарвис"):
        """
        Слушает микрофон и распознает речь

        Args:
            duration: максимальная длительность записи в секундах
            device_index: индекс устройства ввода (None = по умолчанию)
            activation_word: слово активации (если None, то распознается любая речь)

        Returns:
            str: распознанный текст или None
        """
        logger.info("Начинаю прослушивание...")

        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size
            )
            stream.start_stream()

            frames_count = int(self.sample_rate / self.chunk_size * duration)
            text = ""

            for i in range(frames_count):
                data = stream.read(self.chunk_size, exception_on_overflow=False)

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    if result.get('text'):
                        text += result['text'] + " "
                        logger.info(f"Промежуточный результат: {result['text']}")

            # Финальный результат
            final_result = json.loads(self.recognizer.FinalResult())
            if final_result.get('text'):
                text += final_result['text']

            stream.stop_stream()
            stream.close()

            text = text.strip().lower()
            logger.info(f"Распознано: {text}")

            # Проверка на слово активации
            if activation_word and activation_word.lower() not in text:
                logger.info(f"Слово активации '{activation_word}' не обнаружено")
                return None

            # Удаление слова активации из команды
            if activation_word:
                text = text.replace(activation_word.lower(), "").strip()

            return text if text else None

        except Exception as e:
            logger.error(f"Ошибка при распознавании речи: {e}")
            return None

    def listen_continuously(self, callback, device_index=None, activation_word="джарвис"):
        """
        Непрерывное прослушивание с callback при распознавании

        Args:
            callback: функция, вызываемая при распознавании (принимает текст)
            device_index: индекс устройства ввода
            activation_word: слово активации
        """
        logger.info("Запуск непрерывного прослушивания...")

        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size
        )
        stream.start_stream()

        try:
            while True:
                data = stream.read(self.chunk_size, exception_on_overflow=False)

                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get('text', '').strip().lower()

                    if text:
                        logger.info(f"Распознано: {text}")

                        # Проверка на слово активации
                        if not activation_word or activation_word.lower() in text:
                            # Удаление слова активации
                            if activation_word:
                                text = text.replace(activation_word.lower(), "").strip()

                            if text:
                                callback(text)

                        # Сброс распознавателя для новой фразы
                        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

        except KeyboardInterrupt:
            logger.info("Остановка прослушивания...")
        finally:
            stream.stop_stream()
            stream.close()

    def __del__(self):
        """Освобождение ресурсов"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
