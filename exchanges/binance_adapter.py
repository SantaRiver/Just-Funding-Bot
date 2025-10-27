"""Асинхронный адаптер для биржи Binance."""
from datetime import datetime, timezone
from typing import List, Optional
import logging

from exchanges.base import ExchangeAdapter
from models import FundingRate, ContractInfo

logger = logging.getLogger(__name__)


class BinanceAdapter(ExchangeAdapter):
    """Асинхронный адаптер для работы с API Binance Futures."""
    
    BASE_URL = "https://fapi.binance.com"
    
    def __init__(self):
        super().__init__("BINANCE")
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        }
    
    async def get_top_contracts(self, limit: int = 20) -> List[ContractInfo]:
        """Получить топ контрактов с наибольшими ставками."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/fapi/v1/exchangeInfo"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            contracts = []
            for symbol_info in data.get('symbols', []):
                if symbol_info.get('contractType') == 'PERPETUAL' and \
                   symbol_info.get('status') == 'TRADING':
                    symbol = symbol_info.get('symbol', '')
                    base = symbol_info.get('baseAsset', '')
                    quote = symbol_info.get('quoteAsset', '')
                    
                    contracts.append(ContractInfo(
                        symbol=symbol,
                        base_currency=base,
                        quote_currency=quote
                    ))
            
            return contracts[:limit]
        except Exception as e:
            logger.error(f"Error getting Binance contracts: {e}")
            return []
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить ставку финансирования для конкретного символа."""
        try:
            client = self._get_client()
            funding_url = f"{self.BASE_URL}/fapi/v1/premiumIndex"
            params = {"symbol": symbol}
            
            response = await client.get(funding_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            funding_rate = float(data.get('lastFundingRate', 0))
            next_funding_time_ms = int(data.get('nextFundingTime', 0))
            mark_price = float(data.get('markPrice', 0))
            
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
            logger.error(f"Error getting Binance funding rate for {symbol}: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все ставки финансирования."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/fapi/v1/premiumIndex"
            response = await client.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            funding_rates = []
            for item in data:
                try:
                    symbol = item.get('symbol', '')
                    funding_rate = float(item.get('lastFundingRate', 0))
                    next_funding_time_ms = int(item.get('nextFundingTime', 0))
                    mark_price = float(item.get('markPrice', 0))
                    
                    if next_funding_time_ms == 0:
                        continue
                    
                    next_funding_time = datetime.fromtimestamp(
                        next_funding_time_ms / 1000,
                        tz=timezone.utc
                    )
                    
                    funding_rates.append(FundingRate(
                        exchange=self.name,
                        symbol=symbol,
                        rate=funding_rate,
                        price=mark_price,
                        next_funding_time=next_funding_time,
                        quote_currency='USDT'
                    ))
                except (ValueError, TypeError, KeyError) as e:
                    logger.debug(f"Skipping {item.get('symbol', 'unknown')}: {e}")
                    continue
            
            return funding_rates
        except Exception as e:
            logger.error(f"Error getting all Binance funding rates: {e}")
            return []
