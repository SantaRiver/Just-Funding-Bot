"""Модели данных для funding rate бота."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FundingRate:
    """Модель для хранения данных о ставке финансирования."""
    
    exchange: str
    symbol: str
    rate: float
    price: float
    next_funding_time: datetime
    quote_currency: str = "USDT"
    
    @property
    def rate_percentage(self) -> float:
        """Возвращает ставку в процентах."""
        return self.rate * 100
    
    @property
    def abs_rate(self) -> float:
        """Возвращает абсолютное значение ставки."""
        return abs(self.rate)
    
    def __repr__(self) -> str:
        return (f"FundingRate(exchange={self.exchange}, symbol={self.symbol}, "
                f"rate={self.rate_percentage:.4f}%, price={self.price})")


@dataclass
class ContractInfo:
    """Информация о контракте."""
    
    symbol: str
    base_currency: str
    quote_currency: str
    is_active: bool = True
    
    def __repr__(self) -> str:
        return f"ContractInfo(symbol={self.symbol}, base={self.base_currency}, quote={self.quote_currency})"
