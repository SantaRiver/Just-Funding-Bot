"""Async адаптер для OKX (OKEx)."""
from datetime import datetime, timezone
from typing import List, Optional
import logging
from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo

logger = logging.getLogger(__name__)


class OkxAdapter(ExchangeAdapter):
    """Адаптер для OKX Futures API."""
    
    BASE_URL = "https://www.okx.com"
    
    def __init__(self):
        super().__init__("OKX")
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить список топ контрактов."""
        try:
            endpoint = f"{self.BASE_URL}/api/v5/public/instruments"
            params = {"instType": "SWAP"}
            
            response = await self.client.get(endpoint, params=params, timeout=5.0)
            data = response.json()
            
            if data.get('code') != '0':
                logger.error(f"OKX API error: {data}")
                return []
            
            contracts = []
            for item in data.get('data', [])[:limit]:
                inst_id = item.get('instId', '')
                if not inst_id or not inst_id.endswith('-USDT-SWAP'):
                    continue
                
                base = inst_id.replace('-USDT-SWAP', '')
                
                contracts.append(ContractInfo(
                    exchange=self.name,
                    symbol=inst_id,
                    base_currency=base,
                    quote_currency='USDT'
                ))
            
            return contracts
            
        except Exception as e:
            logger.error(f"Error getting contracts from OKX: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить текущую ставку финансирования для символа."""
        try:
            endpoint = f"{self.BASE_URL}/api/v5/public/funding-rate"
            params = {"instId": symbol}
            
            response = await self.client.get(endpoint, params=params, timeout=5.0)
            
            if response is None or response.status_code != 200:
                return None
            
            data = response.json()
            
            if not data or data.get('code') != '0':
                logger.debug(f"OKX API error for {symbol}: {data}")
                return None
            
            result_list = data.get('data', [])
            if not result_list:
                return None
            
            result = result_list[0]
            funding_rate = float(result.get('fundingRate', 0))
            next_funding_time_ms = int(result.get('nextFundingTime', 0))
            
            if next_funding_time_ms == 0:
                return None
            
            next_funding_time = datetime.fromtimestamp(
                next_funding_time_ms / 1000,
                tz=timezone.utc
            )
            
            # Получаем цену
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
            logger.debug(f"OKX: No data for {symbol} - {e}")
            return None
    
    async def _get_mark_price(self, symbol: str) -> Optional[float]:
        """Получить mark price для символа."""
        try:
            endpoint = f"{self.BASE_URL}/api/v5/market/mark-price"
            params = {"instId": symbol, "instType": "SWAP"}
            
            response = await self.client.get(endpoint, params=params, timeout=5.0)
            data = response.json()
            
            if data.get('code') == '0':
                price_list = data.get('data', [])
                if price_list:
                    return float(price_list[0].get('markPx', 0))
            
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
