"""Базовый абстрактный класс для биржевых адаптеров."""
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from models import FundingRate, ContractInfo


class ExchangeAdapter(ABC):
    """Абстрактный класс для работы с биржами (асинхронный)."""
    
    def __init__(self, name: str):
        self.name = name
        self.client: Optional[httpx.AsyncClient] = None
        self.timeout = 10.0
    
    async def __aenter__(self):
        """Контекстный менеджер для async with."""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие клиента при выходе из контекста."""
        if self.client:
            await self.client.aclose()
    
    def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self.client
    
    async def close(self):
        """Закрыть HTTP клиент."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    @abstractmethod
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """
        Получить топ контрактов с наибольшими ставками финансирования.
        
        Args:
            limit: Количество контрактов для возврата
            
        Returns:
            Список контрактов
        """
        pass
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """
        Получить ставку финансирования для конкретного контракта.
        
        Args:
            symbol: Символ контракта
            
        Returns:
            FundingRate или None если данные недоступны
        """
        pass
    
    @abstractmethod
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """
        Получить ставки финансирования для всех доступных контрактов.
        
        Returns:
            Список всех ставок финансирования
        """
        pass
    
    async def is_available(self) -> bool:
        """
        Проверить доступность биржи.
        
        Returns:
            True если биржа доступна
        """
        try:
            # Попытаться получить хотя бы один контракт
            contracts = await self.get_top_contracts(limit=1)
            return len(contracts) > 0
        except Exception:
            return False
