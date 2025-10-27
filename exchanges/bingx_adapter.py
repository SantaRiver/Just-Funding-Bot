"""Async адаптер для BingX."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging
from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo

logger = logging.getLogger(__name__)


class BingxAdapter(ExchangeAdapter):
    """Адаптер для BingX Perpetual Swap API."""
    
    BASE_URL = "https://open-api.bingx.com"
    
    def __init__(self):
        super().__init__("BINGX")
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить список топ контрактов."""
        try:
            endpoint = f"{self.BASE_URL}/openApi/swap/v2/quote/contracts"
            
            response = await self.client.get(endpoint, timeout=5.0)
            data = response.json()
            
            if data.get('code') != 0:
                logger.error(f"BingX API error: {data}")
                return []
            
            contracts = []
            for item in data.get('data', [])[:limit]:
                symbol = item.get('symbol', '')
                if not symbol or not symbol.endswith('-USDT'):
                    continue
                
                contracts.append(ContractInfo(
                    exchange=self.name,
                    symbol=symbol,
                    base_currency=symbol.replace('-USDT', ''),
                    quote_currency='USDT'
                ))
            
            return contracts
            
        except Exception as e:
            logger.error(f"Error getting contracts from BingX: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить текущую ставку финансирования для символа."""
        try:
            endpoint = f"{self.BASE_URL}/openApi/swap/v2/quote/premiumIndex"
            params = {"symbol": symbol}
            
            response = await self.client.get(endpoint, params=params, timeout=5.0)
            
            if response is None or response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data or data.get('code') != 0:
                logger.debug(f"BingX API error for {symbol}: {data}")
                return None
            
            result = data.get('data', {})
            funding_rate = float(result.get('lastFundingRate', 0))
            next_funding_time_ms = int(result.get('nextFundingTime', 0))
            mark_price = float(result.get('markPrice', 0))
            
            if next_funding_time_ms == 0:
                # Fallback: funding каждые 8 часов
                now = datetime.now(timezone.utc)
                hour = now.hour
                next_hour = ((hour // 8) + 1) * 8 % 24
                next_funding_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
                if next_hour < hour:
                    next_funding_time += timedelta(days=1)
            else:
                next_funding_time = datetime.fromtimestamp(
                    next_funding_time_ms / 1000,
                    tz=timezone.utc
                )
            
            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=funding_rate,
                price=mark_price,
                next_funding_time=next_funding_time,
                quote_currency='USDT'
            )
            
        except Exception as e:
            logger.debug(f"BingX: No data for {symbol} - {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        contracts = await self.get_top_contracts(limit=30)
        
        if not contracts:
            return []
        
        rates = []
        for contract in contracts:
            rate = await self.get_funding_rate(contract.symbol)
            if rate:
                rates.append(rate)
        
        return rates
