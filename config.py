"""Конфигурация приложения."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс конфигурации."""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    # Binance
    BINANCE_API_KEY = os.getenv("API_KEY")
    BINANCE_API_SECRET = os.getenv("API_SECRET")
    BINANCE_BASE_PATH = os.getenv("BASE_PATH", "https://fapi.binance.com")
    
    # Настройки мониторинга
    DEFAULT_THRESHOLD = 0.5  # Порог в процентах
    CHECK_INTERVAL = 600  # Интервал проверки в секундах (10 минут)
    ALERT_COOLDOWN = 3600  # Cooldown между алертами для одного токена (1 час)
    
    # Настройки агрегатора
    MAX_WORKERS = 10  # Количество потоков для параллельных запросов
    TOP_CONTRACTS_LIMIT = 20  # Количество топ контрактов для анализа
    
    # Тайм-ауты
    REQUEST_TIMEOUT = 10  # Тайм-аут для HTTP запросов
    
    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """
        Проверка наличия обязательных параметров конфигурации.
        
        Returns:
            True если конфигурация валидна
        """
        if not cls.TELEGRAM_BOT_TOKEN:
            print("Error: TELEGRAM_BOT_TOKEN not set in .env file")
            return False
        
        return True


# Экземпляр конфигурации
config = Config()
