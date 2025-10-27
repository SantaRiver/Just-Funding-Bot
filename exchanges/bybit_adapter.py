"""Асинхронный адаптер для биржи Bybit."""
from datetime import datetime, timezone
from typing import List, Optional
import logging

from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo


logger = logging.getLogger(__name__)


class BybitAdapter(ExchangeAdapter):
    """Асинхронный адаптер для работы с API Bybit."""
    
    BASE_URL = "https://api.bybit.com"
    
    def __init__(self):
        super().__init__("BYBIT")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить топ контрактов с наибольшими ставками."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/v5/market/tickers"
            params = {"category": "linear"}
            
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return []
            
            contracts = []
            for item in data.get('result', {}).get('list', []):
                symbol = item.get('symbol', '')
                if symbol.endswith('USDT'):
                    base = symbol.replace('USDT', '')
                    contracts.append(ContractInfo(
                        symbol=symbol,
                        base_currency=base,
                        quote_currency='USDT'
                    ))
            
            return contracts[:limit]
        except Exception as e:
            logger.error(f"Error getting Bybit contracts: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного символа."""
        try:
            client = self._get_client()
            ticker_url = f"{self.BASE_URL}/v5/market/tickers"
            params = {"category": "linear", "symbol": symbol}
            
            response = await client.get(ticker_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
                logger.error(f"Bybit API error for {symbol}: {data.get('retMsg')}")
                return None
            
            ticker_list = data.get('result', {}).get('list', [])
            if not ticker_list:
                return None
            
            ticker = ticker_list[0]
            
            funding_rate = float(ticker.get('fundingRate', 0))
            next_funding_time_str = ticker.get('nextFundingTime', '0')
            price = float(ticker.get('lastPrice', 0))
            
            next_funding_time = datetime.fromtimestamp(
                int(next_funding_time_str) / 1000,
                tz=timezone.utc
            )
            
            return FundingRate(
                exchange=self.name,
                symbol=symbol,
                rate=funding_rate,
                price=price,
                next_funding_time=next_funding_time,
                quote_currency='USDT'
            )
        except Exception as e:
            logger.error(f"Error getting Bybit funding rate for {symbol}: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/v5/market/tickers"
            params = {"category": "linear"}
            
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
                logger.error(f"Bybit API error: {data.get('retMsg')}")
                return []
            
            funding_rates = []
            for ticker in data.get('result', {}).get('list', []):
                symbol = ticker.get('symbol', '')
                if not symbol.endswith('USDT'):
                    continue
                
                try:
                    funding_rate = float(ticker.get('fundingRate', 0))
                    next_funding_time_str = ticker.get('nextFundingTime', '0')
                    price = float(ticker.get('lastPrice', 0))
                    
                    if next_funding_time_str == '0':
                        continue
                    
                    next_funding_time = datetime.fromtimestamp(
                        int(next_funding_time_str) / 1000,
                        tz=timezone.utc
                    )
                    
                    funding_rates.append(FundingRate(
                        exchange=self.name,
                        symbol=symbol,
                        rate=funding_rate,
                        price=price,
                        next_funding_time=next_funding_time,
                        quote_currency='USDT'
                    ))
                except (ValueError, TypeError) as e:
                    logger.debug(f"Skipping {symbol}: {e}")
                    continue
            
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting all Bybit funding rates: {e}")
            return []
