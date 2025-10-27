"""Асинхронный адаптер для биржи Gate.io."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo


logger = logging.getLogger(__name__)


class GateioAdapter(ExchangeAdapter):
    """Асинхронный адаптер для работы с API Gate.io Futures."""
    
    BASE_URL = "https://api.gateio.ws/api/v4"
    
    def __init__(self):
        super().__init__("GATE")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить топ контрактов."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/futures/usdt/contracts"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            contracts = []
            for contract in data:
                if contract.get('in_delisting') is False:
                    name = contract.get('name', '')
                    if '_USDT' in name:
                        base = name.replace('_USDT', '')
                        contracts.append(ContractInfo(
                            symbol=name,
                            base_currency=base,
                            quote_currency='USDT'
                        ))
            
            return contracts[:limit]
        except Exception as e:
            logger.error(f"Error getting Gate.io contracts: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного символа."""
        try:
            # Gate.io использует формат BTC_USDT
            if 'USDT' in symbol and '_' not in symbol:
                symbol = symbol.replace('USDT', '_USDT')
            
            client = self._get_client()
            url = f"{self.BASE_URL}/futures/usdt/contracts/{symbol}"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            funding_rate = float(data.get('funding_rate', 0))
            mark_price = float(data.get('mark_price', 0))
            
            # Gate.io funding обычно в 00:00, 08:00, 16:00 UTC
            now = datetime.now(timezone.utc)
            hour = now.hour
            next_hour = ((hour // 8) + 1) * 8 % 24
            next_funding_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
            
            if next_hour < hour:
                next_funding_time += timedelta(days=1)
            
            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=funding_rate,
                price=mark_price,
                next_funding_time=next_funding_time,
                quote_currency='USDT'
            )
        except Exception as e:
            logger.debug(f"Error getting Gate.io funding rate for {symbol}: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        try:
            contracts = await self.get_top_contracts(limit=1000)
            
            # Используем asyncio.gather для параллельного получения
            import asyncio
            tasks = [self.get_funding_rate(c.symbol) for c in contracts[:50]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            funding_rates = [r for r in results if isinstance(r, FundingRate)]
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting all Gate.io funding rates: {e}")
            return []
