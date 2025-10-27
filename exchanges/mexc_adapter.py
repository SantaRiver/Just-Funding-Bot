"""Асинхронный адаптер для биржи MEXC."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo


logger = logging.getLogger(__name__)


class MexcAdapter(ExchangeAdapter):
    """Асинхронный адаптер для работы с API MEXC Futures."""
    
    BASE_URL = "https://contract.mexc.com"
    
    def __init__(self):
        super().__init__("MEXC")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить топ контрактов."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/api/v1/contract/detail"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                logger.error(f"MEXC API error: {data}")
                return []
            
            contracts = []
            for contract in data.get('data', []):
                symbol = contract.get('symbol', '')
                if '_USDT' in symbol:
                    base = symbol.replace('_USDT', '')
                    contracts.append(ContractInfo(
                        symbol=symbol,
                        base_currency=base,
                        quote_currency='USDT'
                    ))
            
            return contracts[:limit]
        except Exception as e:
            logger.error(f"Error getting MEXC contracts: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного символа."""
        try:
            original_symbol = symbol
            # MEXC использует формат BTC_USDT
            if 'USDT' in symbol and '_' not in symbol:
                symbol = symbol.replace('USDT', '_USDT')
            
            logger.debug(f"MEXC: Getting rate for {original_symbol} -> {symbol}")
            
            client = self._get_client()
            
            # Сначала пробуем получить данные через ticker (один запрос)
            try:
                ticker_url = f"{self.BASE_URL}/api/v1/contract/ticker/{symbol}"
                ticker_response = await client.get(ticker_url, headers=self.headers, timeout=5)
                ticker_response.raise_for_status()
                ticker_data = ticker_response.json()
                
                if ticker_data.get('success') and ticker_data.get('data'):
                    data = ticker_data['data']
                    funding_rate = float(data.get('fundingRate', 0))
                    price = float(data.get('lastPrice', 0))
                    
                    logger.debug(f"MEXC: ✅ Got data from ticker for {symbol}: rate={funding_rate}, price={price}")
                    
                    # MEXC funding каждые 8 часов (00:00, 08:00, 16:00 UTC)
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
                        price=price,
                        next_funding_time=next_funding_time,
                        quote_currency='USDT'
                    )
                else:
                    logger.debug(f"MEXC: Ticker returned success={ticker_data.get('success')}, has data={bool(ticker_data.get('data'))}")
            except Exception as ticker_err:
                logger.debug(f"MEXC ticker failed for {symbol}: {ticker_err}")
                
            # Fallback: пробуем через funding_rate endpoint
            url = f"{self.BASE_URL}/api/v1/contract/funding_rate/{symbol}"
            response = await client.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                return None
            
            rate_data = data.get('data', {})
            funding_rate = float(rate_data.get('fundingRate', 0))
            
            # MEXC funding каждые 8 часов
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
                price=0,  # Цена недоступна
                next_funding_time=next_funding_time,
                quote_currency='USDT'
            )
        except Exception as e:
            logger.debug(f"Error getting MEXC funding rate for {symbol}: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        try:
            contracts = await self.get_top_contracts(limit=100)
            
            if not contracts:
                logger.warning("No contracts found from MEXC")
                return []
            
            # Параллельно получаем funding rates для топ-30 контрактов
            import asyncio
            tasks = [self.get_funding_rate(c.symbol) for c in contracts[:30]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            funding_rates = [r for r in results if isinstance(r, FundingRate)]
            logger.info(f"MEXC: Got {len(funding_rates)} funding rates from {len(contracts)} contracts")
            
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting all MEXC funding rates: {e}")
            return []
