"""Async адаптер для Bitget."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging
from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo

logger = logging.getLogger(__name__)


class BitgetAdapter(ExchangeAdapter):
    """Адаптер для Bitget Futures API."""
    
    BASE_URL = "https://api.bitget.com"
    
    def __init__(self):
        super().__init__("BITGET")
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить список топ контрактов."""
        try:
            client = self._get_client()
            endpoint = f"{self.BASE_URL}/api/mix/v1/market/contracts"
            params = {"productType": "umcbl"}  # USDT-margined
            
            response = await client.get(endpoint, params=params, timeout=5.0)
            data = response.json()
            
            if data.get('code') != '00000':
                logger.error(f"Bitget API error: {data}")
                return []
            
            contracts = []
            for item in data.get('data', [])[:limit]:
                symbol = item.get('symbol', '')
                if not symbol or not symbol.endswith('USDT'):
                    continue
                
                contracts.append(ContractInfo(
                    exchange=self.name,
                    symbol=symbol,
                    base_currency=symbol.replace('USDT', ''),
                    quote_currency='USDT'
                ))
            
            return contracts
            
        except Exception as e:
            logger.error(f"Error getting contracts from Bitget: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить текущую ставку финансирования для символа."""
        try:
            client = self._get_client()
            endpoint = f"{self.BASE_URL}/api/mix/v1/market/current-fundRate"
            params = {"symbol": symbol}
            
            response = await client.get(endpoint, params=params, timeout=5.0)
            
            if response is None or response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data or data.get('code') != '00000':
                logger.debug(f"Bitget API error for {symbol}: {data}")
                return None
            
            result = data.get('data', {})
            funding_rate = float(result.get('fundingRate', 0))
            
            # Bitget: funding каждые 8 часов (00:00, 08:00, 16:00 UTC)
            now = datetime.now(timezone.utc)
            hour = now.hour
            next_hour = ((hour // 8) + 1) * 8 % 24
            next_funding_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
            
            if next_hour < hour:
                next_funding_time += timedelta(days=1)
            
            # Получаем цену из ticker
            price = await self._get_mark_price(symbol)
            
            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=funding_rate,
                price=price or 0,
                next_funding_time=next_funding_time,
                quote_currency='USDT'
            )
            
        except Exception as e:
            logger.debug(f"Bitget: No data for {symbol} - {e}")
            return None
    
    async def _get_mark_price(self, symbol: str) -> Optional[float]:
        """Получить mark price для символа."""
        try:
            client = self._get_client()
            endpoint = f"{self.BASE_URL}/api/mix/v1/market/ticker"
            params = {"symbol": symbol}
            
            response = await client.get(endpoint, params=params, timeout=5.0)
            data = response.json()
            
            if data.get('code') == '00000':
                return float(data.get('data', {}).get('last', 0))
            
            return None
        except:
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
