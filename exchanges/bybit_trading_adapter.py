"""Торговый адаптер для Bybit с поддержкой открытия/закрытия позиций."""
import hmac
import hashlib
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict
import logging

from exchanges.base_trading import (
    TradingExchangeAdapter,
    OrderSide,
    PositionSide,
    OrderType
)
from models import FundingRate

logger = logging.getLogger(__name__)


class BybitTradingAdapter(TradingExchangeAdapter):
    """
    Торговый адаптер для Bybit.
    Поддерживает чтение данных + открытие/закрытие позиций.
    """
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        testnet: bool = True
    ):
        super().__init__("BYBIT", api_key, api_secret)
        
        # Используем testnet или mainnet
        if testnet:
            self.BASE_URL = "https://api-testnet.bybit.com"
            logger.info(f"[{self.name}] Using TESTNET")
        else:
            self.BASE_URL = "https://api.bybit.com"
            logger.warning(f"[{self.name}] Using MAINNET - real money!")
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _generate_signature(self, params: Dict) -> str:
        """
        Генерация подписи для Bybit API v5.
        
        Bybit использует HMAC SHA256.
        """
        # Сортируем параметры по ключу
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _prepare_request(self, params: Dict = None) -> Dict:
        """Подготовить параметры запроса с подписью."""
        if not self._check_api_credentials():
            raise ValueError("API credentials not set")
        
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        
        request_params = {
            'api_key': self.api_key,
            'timestamp': timestamp,
            'recv_window': recv_window
        }
        
        if params:
            request_params.update(params)
        
        # Добавляем подпись
        request_params['sign'] = self._generate_signature(request_params)
        
        return request_params
    
    # ========== READ-ONLY МЕТОДЫ ==========
    
    async def get_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Получить funding rate (read-only, не требует API ключей)."""
        try:
            client = self._get_client()
            url = f"{self.BASE_URL}/v5/market/tickers"
            params = {"category": "linear", "symbol": symbol}
            
            response = await client.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
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
            logger.error(f"Error getting funding rate: {e}")
            return None
    
    async def get_all_funding_rates(self) -> List[FundingRate]:
        """Получить все funding rates."""
        # Реализация аналогична bybit_adapter.py
        # Здесь упрощенная версия для примера
        return []
    
    # ========== ТОРГОВЫЕ МЕТОДЫ ==========
    
    async def get_account_balance(self) -> Dict:
        """Получить баланс USDT аккаунта."""
        try:
            params = self._prepare_request({'accountType': 'UNIFIED'})
            
            url = f"{self.BASE_URL}/v5/account/wallet-balance"
            response = await self._get_client().get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                logger.error(f"API error: {data.get('retMsg')}")
                return {}
            
            # Парсим баланс
            result = data.get('result', {})
            accounts = result.get('list', [])
            
            if not accounts:
                return {'total': 0, 'available': 0, 'used': 0, 'currency': 'USDT'}
            
            account = accounts[0]
            total_balance = float(account.get('totalEquity', 0))
            available_balance = float(account.get('totalAvailableBalance', 0))
            
            return {
                'total': total_balance,
                'available': available_balance,
                'used': total_balance - available_balance,
                'currency': 'USDT'
            }
            
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return {}
    
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Получить информацию о позиции."""
        try:
            params = self._prepare_request({
                'category': 'linear',
                'symbol': symbol
            })
            
            url = f"{self.BASE_URL}/v5/position/list"
            response = await self._get_client().get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                return None
            
            positions = data.get('result', {}).get('list', [])
            
            if not positions:
                return None
            
            pos = positions[0]
            size = float(pos.get('size', 0))
            
            if size == 0:
                return None  # Позиция закрыта
            
            return {
                'symbol': pos.get('symbol'),
                'side': 'LONG' if pos.get('side') == 'Buy' else 'SHORT',
                'size': size,
                'entry_price': float(pos.get('avgPrice', 0)),
                'mark_price': float(pos.get('markPrice', 0)),
                'unrealized_pnl': float(pos.get('unrealisedPnl', 0)),
                'leverage': int(pos.get('leverage', 1))
            }
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    async def get_all_positions(self) -> List[Dict]:
        """Получить все открытые позиции."""
        try:
            params = self._prepare_request({'category': 'linear'})
            
            url = f"{self.BASE_URL}/v5/position/list"
            response = await self._get_client().get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                return []
            
            positions = data.get('result', {}).get('list', [])
            
            # Фильтруем только открытые позиции
            open_positions = []
            for pos in positions:
                size = float(pos.get('size', 0))
                if size > 0:
                    open_positions.append({
                        'symbol': pos.get('symbol'),
                        'side': 'LONG' if pos.get('side') == 'Buy' else 'SHORT',
                        'size': size,
                        'entry_price': float(pos.get('avgPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealisedPnl', 0)),
                        'leverage': int(pos.get('leverage', 1))
                    })
            
            return open_positions
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Установить плечо."""
        try:
            params = self._prepare_request({
                'category': 'linear',
                'symbol': symbol,
                'buyLeverage': str(leverage),
                'sellLeverage': str(leverage)
            })
            
            url = f"{self.BASE_URL}/v5/position/set-leverage"
            response = await self._get_client().post(url, json=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') == 0:
                logger.info(f"Leverage set to {leverage}x for {symbol}")
                return True
            else:
                logger.error(f"Error setting leverage: {data.get('retMsg')}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            return False
    
    async def open_market_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        reduce_only: bool = False
    ) -> Dict:
        """Открыть позицию по рыночной цене."""
        try:
            # Преобразуем PositionSide в Bybit side
            bybit_side = "Buy" if side == PositionSide.LONG else "Sell"
            
            params = self._prepare_request({
                'category': 'linear',
                'symbol': symbol,
                'side': bybit_side,
                'orderType': 'Market',
                'qty': str(quantity),
                'timeInForce': 'GTC',
                'positionIdx': 0,  # One-way mode
                'reduceOnly': reduce_only
            })
            
            url = f"{self.BASE_URL}/v5/order/create"
            response = await self._get_client().post(url, json=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                raise Exception(f"Order failed: {data.get('retMsg')}")
            
            result = data.get('result', {})
            
            logger.info(f"Order placed: {symbol} {side.value} {quantity}")
            
            return {
                'order_id': result.get('orderId'),
                'symbol': symbol,
                'side': side.value,
                'quantity': quantity,
                'status': 'SUBMITTED'
            }
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            raise
    
    async def close_position(self, symbol: str) -> Dict:
        """Закрыть позицию полностью."""
        try:
            # Получаем текущую позицию
            position = await self.get_position(symbol)
            
            if not position:
                logger.warning(f"No position to close for {symbol}")
                return {}
            
            # Закрываем противоположным ордером с reduce_only
            close_side = PositionSide.SHORT if position['side'] == 'LONG' else PositionSide.LONG
            
            result = await self.open_market_position(
                symbol=symbol,
                side=close_side,
                quantity=position['size'],
                reduce_only=True
            )
            
            logger.info(f"Position closed: {symbol}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise
    
    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """Получить стакан ордеров."""
        try:
            url = f"{self.BASE_URL}/v5/market/orderbook"
            params = {
                'category': 'linear',
                'symbol': symbol,
                'limit': min(depth, 50)  # Bybit max 50
            }
            
            response = await self._get_client().get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('retCode') != 0:
                return {'bids': [], 'asks': [], 'timestamp': 0}
            
            result = data.get('result', {})
            
            return {
                'bids': result.get('b', []),  # [[price, qty], ...]
                'asks': result.get('a', []),
                'timestamp': int(result.get('ts', 0))
            }
            
        except Exception as e:
            logger.error(f"Error getting order book: {e}")
            return {'bids': [], 'asks': [], 'timestamp': 0}
    
    async def get_position_margin_info(self, symbol: str) -> Dict:
        """Получить информацию о марже."""
        try:
            position = await self.get_position(symbol)
            
            if not position:
                return {}
            
            # Эта информация обычно включена в position response
            # Но может потребоваться отдельный запрос
            
            return {
                'initial_margin': 0.0,  # TODO: рассчитать из позиции
                'maintenance_margin': 0.0,
                'margin_ratio': 0.0,
                'liquidation_price': 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting margin info: {e}")
            return {}


# Пример использования:
"""
# Инициализация
adapter = BybitTradingAdapter(
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET",
    testnet=True  # Обязательно начинать с testnet!
)

# Проверка баланса
balance = await adapter.get_account_balance()
print(f"Available: ${balance['available']:.2f}")

# Установить плечо
await adapter.set_leverage("BTCUSDT", 2)

# Открыть LONG позицию
order = await adapter.open_market_position(
    symbol="BTCUSDT",
    side=PositionSide.LONG,
    quantity=0.001  # 0.001 BTC
)

# Проверить позицию
position = await adapter.get_position("BTCUSDT")
print(f"Position: {position}")

# Закрыть позицию
await adapter.close_position("BTCUSDT")
"""
