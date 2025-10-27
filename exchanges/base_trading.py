"""Расширенный базовый класс для торговых адаптеров."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from enum import Enum
import httpx
import logging
from models import FundingRate, ContractInfo

logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Направление ордера"""
    BUY = "BUY"
    SELL = "SELL"


class PositionSide(Enum):
    """Направление позиции"""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(Enum):
    """Тип ордера"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TradingExchangeAdapter(ABC):
    """
    Расширенный абстрактный класс для работы с биржами.
    Включает торговые функции (открытие/закрытие позиций).
    """
    
    def __init__(self, name: str, api_key: str = None, api_secret: str = None):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.client: Optional[httpx.AsyncClient] = None
        self.timeout = 30.0  # Увеличен timeout для торговых операций
    
    def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                event_hooks={'response': [self._log_response], 'request': [self._log_request]}
            )
        return self.client
    
    async def _log_request(self, request: httpx.Request):
        """Логирование исходящих запросов."""
        logger.debug(f"[{self.name}] → {request.method} {request.url}")
    
    async def _log_response(self, response: httpx.Response):
        """Логирование входящих ответов."""
        status = response.status_code
        url = str(response.url)
        
        if status == 200:
            logger.debug(f"[{self.name}] ← {status} {url}")
        elif 400 <= status < 500:
            logger.warning(f"[{self.name}] ← {status} {url} - Client error")
            try:
                body = response.text[:200]
                logger.warning(f"[{self.name}] Response body: {body}...")
            except:
                pass
        elif status >= 500:
            logger.error(f"[{self.name}] ← {status} {url} - Server error")
    
    async def close(self):
        """Закрыть HTTP клиент."""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    # ========== READ-ONLY МЕТОДЫ (уже реализованы в базовых адаптерах) ==========
    
    @abstractmethod
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного контракта."""
        pass
    
    @abstractmethod
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить ставки финансирования для всех доступных контрактов."""
        pass
    
    # ========== ТОРГОВЫЕ МЕТОДЫ (нужно реализовать) ==========
    
    @abstractmethod
    async def get_account_balance(self) -> Dict:
        """
        Получить баланс аккаунта.
        
        Returns:
            {
                'total': float,  # Общий баланс
                'available': float,  # Доступный баланс
                'used': float,  # Используемый в позициях/ордерах
                'currency': str  # Валюта (обычно USDT)
            }
        """
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Получить информацию о текущей позиции.
        
        Args:
            symbol: Символ контракта (например, BTCUSDT)
        
        Returns:
            {
                'symbol': str,
                'side': str,  # 'LONG' или 'SHORT'
                'size': float,  # Размер позиции
                'entry_price': float,  # Цена входа
                'mark_price': float,  # Текущая mark price
                'unrealized_pnl': float,  # Нереализованная прибыль/убыток
                'leverage': int  # Плечо
            }
            или None если позиции нет
        """
        pass
    
    @abstractmethod
    async def get_all_positions(self) -> List[Dict]:
        """
        Получить все открытые позиции.
        
        Returns:
            Список позиций (структура как в get_position)
        """
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """
        Установить плечо для символа.
        
        Args:
            symbol: Символ контракта
            leverage: Плечо (обычно 1-125, но рекомендуется 1-10)
        
        Returns:
            True если успешно
        """
        pass
    
    @abstractmethod
    async def open_market_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        reduce_only: bool = False
    ) -> Dict:
        """
        Открыть позицию по рыночной цене.
        
        Args:
            symbol: Символ контракта
            side: LONG или SHORT
            quantity: Размер в базовой валюте (BTC, ETH и т.д.)
            reduce_only: Только уменьшение позиции (для закрытия)
        
        Returns:
            {
                'order_id': str,
                'symbol': str,
                'side': str,
                'quantity': float,
                'price': float,  # Цена исполнения
                'status': str  # 'FILLED', 'PARTIALLY_FILLED', etc.
            }
        """
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str) -> Dict:
        """
        Закрыть позицию полностью.
        
        Args:
            symbol: Символ контракта
        
        Returns:
            Информация о закрывающем ордере (структура как в open_market_position)
        """
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """
        Получить стакан ордеров.
        
        Args:
            symbol: Символ контракта
            depth: Глубина стакана (количество уровней)
        
        Returns:
            {
                'bids': [[price, quantity], ...],  # Заявки на покупку
                'asks': [[price, quantity], ...],  # Заявки на продажу
                'timestamp': int
            }
        """
        pass
    
    @abstractmethod
    async def get_position_margin_info(self, symbol: str) -> Dict:
        """
        Получить информацию о марже позиции.
        
        Returns:
            {
                'initial_margin': float,  # Начальная маржа
                'maintenance_margin': float,  # Поддерживающая маржа
                'margin_ratio': float,  # Процент маржи
                'liquidation_price': float  # Цена ликвидации
            }
        """
        pass
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========
    
    @abstractmethod
    def _generate_signature(self, params: Dict) -> str:
        """
        Генерация подписи для аутентификации.
        Каждая биржа имеет свой метод.
        """
        pass
    
    def _check_api_credentials(self) -> bool:
        """Проверить наличие API credentials."""
        if not self.api_key or not self.api_secret:
            logger.error(f"[{self.name}] API credentials not set")
            return False
        return True
    
    async def calculate_position_size(
        self,
        symbol: str,
        size_usd: float,
        leverage: int = 1
    ) -> float:
        """
        Рассчитать размер позиции в базовой валюте.
        
        Args:
            symbol: Символ контракта
            size_usd: Размер в USD
            leverage: Плечо
        
        Returns:
            Размер в базовой валюте (например, BTC)
        """
        # Получаем текущую цену
        funding_rate = await self.get_funding_rate(symbol)
        if not funding_rate:
            raise ValueError(f"Cannot get price for {symbol}")
        
        # Размер позиции = (size_usd * leverage) / price
        quantity = (size_usd * leverage) / funding_rate.price
        
        return quantity
    
    async def estimate_slippage(
        self,
        symbol: str,
        side: OrderSide,
        quantity: float
    ) -> float:
        """
        Оценить проскальзывание для ордера.
        
        Returns:
            Процент проскальзывания
        """
        order_book = await self.get_order_book(symbol, depth=50)
        
        # Выбираем нужную сторону стакана
        orders = order_book['asks'] if side == OrderSide.BUY else order_book['bids']
        
        if not orders:
            return float('inf')
        
        # Рассчитываем среднюю цену исполнения
        remaining = quantity
        total_cost = 0.0
        
        for price_str, qty_str in orders:
            price = float(price_str)
            qty = float(qty_str)
            
            if remaining <= 0:
                break
            
            executed = min(remaining, qty)
            total_cost += executed * price
            remaining -= executed
        
        if remaining > 0:
            # Недостаточно ликвидности
            return float('inf')
        
        avg_price = total_cost / quantity
        best_price = float(orders[0][0])
        
        # Проскальзывание в процентах
        slippage = abs((avg_price - best_price) / best_price) * 100
        
        return slippage
