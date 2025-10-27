"""Асинхронный адаптер для биржи KuCoin."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo


logger = logging.getLogger(__name__)


class KucoinAdapter(ExchangeAdapter):
    """Асинхронный адаптер для работы с API KuCoin Futures."""
    
    BASE_URL = "https://api-futures.kucoin.com"
    
    def __init__(self):
        super().__init__("KUCOIN")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить топ контрактов."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/api/v1/contracts/active"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != '200000':
                logger.error(f"KuCoin API error: {data}")
                return []
            
            contracts = []
            for contract in data.get('data', []):
                symbol = contract.get('symbol', '')
                base = contract.get('baseCurrency', '')
                if 'USDT' in symbol:
                    contracts.append(ContractInfo(
                        symbol=symbol,
                        base_currency=base,
                        quote_currency='USDT'
                    ))
            
            return contracts[:limit]
        except Exception as e:
            logger.error(f"Error getting KuCoin contracts: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного символа."""
        try:
            # Пробуем разные форматы
            symbols_to_try = [symbol, symbol.replace('USDT', 'USDTM'), f"{symbol}M"]
            
            client = self._get_client()
            
            for sym in symbols_to_try:
                try:
                    url = f"{self.BASE_URL}/api/v1/funding-rate/{sym}/current"
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get('code') != '200000':
                        continue
                    
                    rate_data = data.get('data', {})
                    funding_rate = float(rate_data.get('value', 0))
                    
                    # Получаем цену
                    ticker_url = f"{self.BASE_URL}/api/v1/ticker"
                    ticker_params = {'symbol': sym}
                    ticker_response = await client.get(ticker_url, params=ticker_params, headers=self.headers)
                    ticker_response.raise_for_status()
                    ticker_data = ticker_response.json()
                    
                    price = 0
                    if ticker_data.get('code') == '200000':
                        price = float(ticker_data.get('data', {}).get('price', 0))
                    
                    # KuCoin funding каждые 8 часов
                    now = datetime.now(timezone.utc)
                    hour = now.hour
                    next_hour = ((hour // 8) + 1) * 8 % 24
                    next_funding_time = now.replace(hour=next_hour, minute=0, second=0, microsecond=0)
                    
                    if next_hour < hour:
                        next_funding_time += timedelta(days=1)
                    
                    return FundingRate(
                        exchange=self.name,
                        symbol=sym,
                        rate=funding_rate,
                        price=price,
                        next_funding_time=next_funding_time,
                        quote_currency='USDT'
                    )
                except:
                    continue
            
            return None
        except Exception as e:
            logger.debug(f"Error getting KuCoin funding rate for {symbol}: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        try:
            contracts = await self.get_top_contracts(limit=50)
            
            import asyncio
            tasks = [self.get_funding_rate(c.symbol) for c in contracts]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            funding_rates = [r for r in results if isinstance(r, FundingRate)]
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting all KuCoin funding rates: {e}")
            return []
