"""
Модули для системы голосового управления
"""
from .speech_recognition import SpeechRecognizer
from .command_processor import CommandProcessor
from .network_client import NetworkClient

__all__ = ['SpeechRecognizer', 'CommandProcessor', 'NetworkClient']
