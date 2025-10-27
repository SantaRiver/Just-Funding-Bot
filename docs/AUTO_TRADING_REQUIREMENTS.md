# 🤖 Требования для автоматической торговли (Auto-Trading)

## 📋 Текущее состояние

**Сейчас бот работает в режиме READ-ONLY:**
- ✅ Получение funding rates
- ✅ Получение цен и контрактов
- ✅ Анализ и поиск возможностей
- ❌ **НЕТ** торговых функций
- ❌ **НЕТ** API ключей
- ❌ **НЕТ** управления позициями

## 🔑 Что нужно добавить для торговли

### 1. API ключи и авторизация

#### Для каждой биржи нужны:

**Bybit:**
```env
BYBIT_API_KEY=your_api_key_here
BYBIT_API_SECRET=your_api_secret_here
BYBIT_TESTNET=true  # true для testnet, false для mainnet
```

**Binance:**
```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true
```

**MEXC, Gate.io, и т.д.:**
```env
MEXC_API_KEY=...
MEXC_API_SECRET=...
GATEIO_API_KEY=...
GATEIO_API_SECRET=...
# и так далее для каждой биржи
```

#### Как получить API ключи:

1. **Bybit**: https://www.bybit.com/app/user/api-management
2. **Binance**: https://www.binance.com/en/my/settings/api-management
3. **MEXC**: https://www.mexc.com/user/openapi

⚠️ **Важно**: Включите только нужные разрешения:
- ✅ **Чтение** (Read) - всегда
- ✅ **Торговля** (Trade/Spot & Futures) - для открытия позиций
- ❌ **Вывод** (Withdrawal) - НИКОГДА не включайте!

#### Whitelist IP адресов

Для безопасности привяжите API ключи к конкретному IP:
- Укажите IP вашего сервера
- Если нет статического IP, используйте VPS

### 2. Расширение базового класса ExchangeAdapter

Добавить торговые методы в `exchanges/base.py`:

```python
from abc import abstractmethod
from typing import Optional, Dict
from enum import Enum

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class ExchangeAdapter(ABC):
    def __init__(self, name: str, api_key: str = None, api_secret: str = None):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        # ... existing code ...
    
    # === НОВЫЕ МЕТОДЫ ДЛЯ ТОРГОВЛИ ===
    
    @abstractmethod
    async def get_account_balance(self) -> Dict:
        """Получить баланс аккаунта"""
        pass
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[Dict]:
        """Получить информацию о текущей позиции"""
        pass
    
    @abstractmethod
    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        leverage: int = 1
    ) -> Dict:
        """Открыть позицию (LONG или SHORT)"""
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str) -> Dict:
        """Закрыть позицию"""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Установить плечо для символа"""
        pass
    
    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> Dict:
        """Получить стакан для проверки ликвидности"""
        pass
```

### 3. Реализация торговых методов для каждой биржи

#### Пример для Bybit (`exchanges/bybit_adapter.py`):

```python
import hmac
import hashlib
import time

class BybitAdapter(ExchangeAdapter):
    def __init__(self, api_key: str = None, api_secret: str = None, testnet: bool = True):
        super().__init__("BYBIT", api_key, api_secret)
        self.BASE_URL = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
    
    def _generate_signature(self, params: dict) -> str:
        """Генерация подписи для Bybit API"""
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def get_account_balance(self) -> Dict:
        """Получить баланс USDT"""
        timestamp = str(int(time.time() * 1000))
        params = {
            'api_key': self.api_key,
            'timestamp': timestamp,
            'accountType': 'UNIFIED'
        }
        params['sign'] = self._generate_signature(params)
        
        url = f"{self.BASE_URL}/v5/account/wallet-balance"
        response = await self._get_client().get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        # Парсинг баланса из ответа
        # ...
        return data
    
    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        leverage: int = 1
    ) -> Dict:
        """Открыть позицию на Bybit"""
        # Установить плечо
        await self.set_leverage(symbol, leverage)
        
        # Создать ордер
        timestamp = str(int(time.time() * 1000))
        order_side = "Buy" if side == PositionSide.LONG else "Sell"
        
        params = {
            'api_key': self.api_key,
            'timestamp': timestamp,
            'category': 'linear',
            'symbol': symbol,
            'side': order_side,
            'orderType': 'Market',
            'qty': str(quantity),
            'timeInForce': 'GTC',
            'positionIdx': 0  # One-way mode
        }
        params['sign'] = self._generate_signature(params)
        
        url = f"{self.BASE_URL}/v5/order/create"
        response = await self._get_client().post(url, json=params)
        response.raise_for_status()
        
        return response.json()
    
    # ... остальные методы
```

#### Аналогично для Binance, MEXC, Gate.io и т.д.

### 4. Создание торгового сервиса

Создать новый файл `services/trading.py`:

```python
"""Сервис для автоматической торговли"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from exchanges.base import ExchangeAdapter, PositionSide

logger = logging.getLogger(__name__)


@dataclass
class HedgePosition:
    """Информация о хедж-позиции"""
    token: str
    long_exchange: str
    short_exchange: str
    quantity: float
    entry_time: datetime
    long_price: float
    short_price: float
    expected_profit: float


class TradingService:
    """Сервис для выполнения торговых операций"""
    
    def __init__(self, exchanges: Dict[str, ExchangeAdapter]):
        """
        Args:
            exchanges: Словарь {exchange_name: ExchangeAdapter} с API ключами
        """
        self.exchanges = exchanges
        self.active_positions: List[HedgePosition] = []
    
    async def execute_hedge(
        self,
        opportunity: Dict,
        position_size_usd: float,
        leverage: int = 1,
        dry_run: bool = True
    ) -> Optional[HedgePosition]:
        """
        Выполнить хедж-стратегию
        
        Args:
            opportunity: Словарь с информацией о возможности (из find_hedging_opportunities)
            position_size_usd: Размер позиции в USD
            leverage: Плечо (1-10, рекомендуется 1-3)
            dry_run: Если True, только симуляция (не открывать реальные позиции)
        
        Returns:
            HedgePosition или None при ошибке
        """
        token = opportunity['token']
        long_exch = opportunity['long_exchange']
        short_exch = opportunity['short_exchange']
        long_rate = opportunity['long_rate']
        short_rate = opportunity['short_rate']
        
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Executing hedge for {token}")
        logger.info(f"  LONG on {long_exch}: {long_rate.rate_percentage:+.4f}%")
        logger.info(f"  SHORT on {short_exch}: {short_rate.rate_percentage:+.4f}%")
        logger.info(f"  Position size: ${position_size_usd} with {leverage}x leverage")
        
        try:
            # 1. Проверка балансов
            long_exchange_adapter = self.exchanges.get(long_exch)
            short_exchange_adapter = self.exchanges.get(short_exch)
            
            if not long_exchange_adapter or not short_exchange_adapter:
                logger.error("Exchange adapters not found")
                return None
            
            # Проверяем баланс на обеих биржах
            long_balance = await long_exchange_adapter.get_account_balance()
            short_balance = await short_exchange_adapter.get_account_balance()
            
            # Проверяем достаточно ли средств
            required_margin = position_size_usd / leverage
            if not self._check_sufficient_balance(long_balance, required_margin):
                logger.error(f"Insufficient balance on {long_exch}")
                return None
            if not self._check_sufficient_balance(short_balance, required_margin):
                logger.error(f"Insufficient balance on {short_exch}")
                return None
            
            # 2. Проверка ликвидности
            long_liquidity = await long_exchange_adapter.get_order_book(long_rate.symbol)
            short_liquidity = await short_exchange_adapter.get_order_book(short_rate.symbol)
            
            if not self._check_sufficient_liquidity(long_liquidity, position_size_usd):
                logger.warning(f"Low liquidity on {long_exch}")
            if not self._check_sufficient_liquidity(short_liquidity, position_size_usd):
                logger.warning(f"Low liquidity on {short_exch}")
            
            # 3. Открытие позиций (если не dry_run)
            if not dry_run:
                # Вычисляем количество контрактов
                long_quantity = position_size_usd / long_rate.price
                short_quantity = position_size_usd / short_rate.price
                
                # Открываем LONG
                logger.info(f"Opening LONG on {long_exch}: {long_quantity} {token}")
                long_order = await long_exchange_adapter.open_position(
                    symbol=long_rate.symbol,
                    side=PositionSide.LONG,
                    quantity=long_quantity,
                    leverage=leverage
                )
                logger.info(f"LONG opened: {long_order}")
                
                # Открываем SHORT
                logger.info(f"Opening SHORT on {short_exch}: {short_quantity} {token}")
                short_order = await short_exchange_adapter.open_position(
                    symbol=short_rate.symbol,
                    side=PositionSide.SHORT,
                    quantity=short_quantity,
                    leverage=leverage
                )
                logger.info(f"SHORT opened: {short_order}")
            
            # 4. Создаем запись о позиции
            hedge_position = HedgePosition(
                token=token,
                long_exchange=long_exch,
                short_exchange=short_exch,
                quantity=position_size_usd,
                entry_time=datetime.now(timezone.utc),
                long_price=long_rate.price,
                short_price=short_rate.price,
                expected_profit=opportunity['spread']
            )
            
            if not dry_run:
                self.active_positions.append(hedge_position)
            
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Hedge executed successfully")
            return hedge_position
            
        except Exception as e:
            logger.error(f"Error executing hedge: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def close_hedge(self, position: HedgePosition, dry_run: bool = True):
        """Закрыть хедж-позицию"""
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Closing hedge for {position.token}")
        
        try:
            long_adapter = self.exchanges.get(position.long_exchange)
            short_adapter = self.exchanges.get(position.short_exchange)
            
            if not dry_run:
                # Закрываем позиции
                await long_adapter.close_position(position.token + "USDT")
                await short_adapter.close_position(position.token + "USDT")
                
                # Удаляем из активных
                self.active_positions.remove(position)
            
            logger.info(f"Hedge closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing hedge: {e}")
    
    def _check_sufficient_balance(self, balance: Dict, required: float) -> bool:
        """Проверить достаточность баланса"""
        # Реализация зависит от структуры ответа биржи
        available = balance.get('available', 0)
        return available >= required
    
    def _check_sufficient_liquidity(self, order_book: Dict, size: float) -> bool:
        """Проверить достаточность ликвидности"""
        # Проверяем что в стакане есть достаточно объема
        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])
        
        total_bid_volume = sum(float(bid[1]) for bid in bids[:10])
        total_ask_volume = sum(float(ask[1]) for ask in asks[:10])
        
        # Нужно минимум 2x от размера позиции
        return total_bid_volume >= size * 2 and total_ask_volume >= size * 2
```

### 5. Добавление команды в бота

В `bot.py` добавить команду для автоматического выполнения хеджа:

```python
async def execute_hedge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /execute_hedge - автоматически выполнить хедж"""
    
    # Проверка прав администратора
    if not self._is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Только администратор может выполнять торговые операции")
        return
    
    # Парсинг аргументов: /execute_hedge BTC 1000 2 true
    # token, size_usd, leverage, dry_run
    if len(context.args) < 2:
        await update.message.reply_text(
            "Использование: /execute_hedge <TOKEN> <SIZE_USD> [LEVERAGE] [DRY_RUN]\n"
            "Пример: /execute_hedge BTC 1000 2 true"
        )
        return
    
    token = context.args[0].upper()
    size_usd = float(context.args[1])
    leverage = int(context.args[2]) if len(context.args) > 2 else 1
    dry_run = context.args[3].lower() == 'true' if len(context.args) > 3 else True
    
    # Найти возможность для этого токена
    opportunities = await self.aggregator.find_hedging_opportunities(min_spread=0.3)
    opportunity = next((o for o in opportunities if o['token'] == token), None)
    
    if not opportunity:
        await update.message.reply_text(f"❌ Не найдено возможности для {token}")
        return
    
    # Выполнить хедж
    trading_service = self.get_trading_service()  # Нужно инициализировать
    result = await trading_service.execute_hedge(
        opportunity=opportunity,
        position_size_usd=size_usd,
        leverage=leverage,
        dry_run=dry_run
    )
    
    if result:
        mode = "🧪 ТЕСТОВЫЙ РЕЖИМ" if dry_run else "🔴 РЕАЛЬНАЯ ТОРГОВЛЯ"
        message = (
            f"{mode}\n\n"
            f"✅ Хедж выполнен для {token}\n\n"
            f"📈 LONG: {result.long_exchange} @ ${result.long_price:,.2f}\n"
            f"📉 SHORT: {result.short_exchange} @ ${result.short_price:,.2f}\n"
            f"💰 Размер: ${result.quantity:,.2f}\n"
            f"📊 Ожидаемая прибыль: {result.expected_profit:.4f}%"
        )
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("❌ Ошибка при выполнении хеджа")
```

### 6. Система управления рисками

Создать `services/risk_management.py`:

```python
"""Система управления рисками"""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskLimits:
    """Лимиты рисков"""
    max_position_size_usd: float = 10000  # Макс размер позиции
    max_leverage: int = 3  # Макс плечо
    max_total_exposure_usd: float = 50000  # Макс общая экспозиция
    min_spread_pct: float = 0.3  # Мин спред для входа
    max_positions: int = 5  # Макс количество позиций
    min_liquidity_multiplier: float = 2.0  # Мин ликвидность (2x от размера)
    max_spread_decrease_pct: float = 50.0  # Закрыть если спред упал на 50%


class RiskManager:
    """Менеджер рисков"""
    
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.current_exposure = 0.0
        self.position_count = 0
    
    def can_open_position(
        self,
        size_usd: float,
        leverage: int,
        spread_pct: float,
        liquidity_check: bool
    ) -> tuple[bool, Optional[str]]:
        """
        Проверить можно ли открыть позицию
        
        Returns:
            (can_open, reason_if_not)
        """
        # Проверка размера позиции
        if size_usd > self.limits.max_position_size_usd:
            return False, f"Position size ${size_usd} exceeds limit ${self.limits.max_position_size_usd}"
        
        # Проверка плеча
        if leverage > self.limits.max_leverage:
            return False, f"Leverage {leverage}x exceeds limit {self.limits.max_leverage}x"
        
        # Проверка общей экспозиции
        new_exposure = self.current_exposure + size_usd
        if new_exposure > self.limits.max_total_exposure_usd:
            return False, f"Total exposure ${new_exposure} exceeds limit ${self.limits.max_total_exposure_usd}"
        
        # Проверка минимального спреда
        if spread_pct < self.limits.min_spread_pct:
            return False, f"Spread {spread_pct:.2f}% below minimum {self.limits.min_spread_pct}%"
        
        # Проверка количества позиций
        if self.position_count >= self.limits.max_positions:
            return False, f"Max positions {self.limits.max_positions} reached"
        
        # Проверка ликвидности
        if not liquidity_check:
            return False, "Insufficient liquidity"
        
        return True, None
    
    def should_close_position(
        self,
        entry_spread_pct: float,
        current_spread_pct: float
    ) -> tuple[bool, Optional[str]]:
        """Проверить нужно ли закрыть позицию"""
        
        # Если спред сильно уменьшился
        spread_decrease = ((entry_spread_pct - current_spread_pct) / entry_spread_pct) * 100
        if spread_decrease >= self.limits.max_spread_decrease_pct:
            return True, f"Spread decreased by {spread_decrease:.1f}%"
        
        # Если спред стал отрицательным (убыточная позиция)
        if current_spread_pct < 0:
            return True, "Spread became negative"
        
        return False, None
```

### 7. Мониторинг и логирование

Расширить систему логирования для торговли:

```python
# В bot.py или отдельном файле

# Создать отдельный лог-файл для торговых операций
trade_handler = RotatingFileHandler(
    logs_dir / "trades.log",
    maxBytes=10*1024*1024,
    backupCount=10,
    encoding='utf-8'
)
trade_handler.setFormatter(log_format)
trade_handler.setLevel(logging.INFO)

trade_logger = logging.getLogger("trading")
trade_logger.addHandler(trade_handler)

# Логировать все торговые операции
trade_logger.info(f"HEDGE_OPEN: {token} LONG={long_exch} SHORT={short_exch} SIZE=${size}")
trade_logger.info(f"HEDGE_CLOSE: {token} PROFIT=${profit}")
```

## 🔒 Безопасность

### Обязательные меры безопасности:

1. **API ключи**:
   - Хранить в `.env`, НИКОГДА в коде
   - Не коммитить в Git (добавить в `.gitignore`)
   - Использовать только необходимые разрешения
   - Привязать к IP адресу

2. **Testnet сначала**:
   - Всегда тестировать на testnet
   - Проверить все функции
   - Только потом переходить на mainnet

3. **Лимиты**:
   - Установить максимальный размер позиции
   - Установить максимальное плечо (рекомендуется ≤3x)
   - Установить максимальную общую экспозицию

4. **Мониторинг**:
   - Логировать все торговые операции
   - Настроить алерты в Telegram
   - Проверять позиции каждый час

5. **Kill switch**:
   - Добавить команду для экстренного закрытия всех позиций
   - Автоматическое закрытие при большом PnL убытке

## 📊 Пример конфигурации

`.env` файл для торговли:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_user_id

# Cache
CACHE_TTL=30

# Bybit
BYBIT_API_KEY=your_api_key
BYBIT_API_SECRET=your_api_secret
BYBIT_TESTNET=true

# Binance
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true

# Trading Settings
MAX_POSITION_SIZE_USD=1000
MAX_LEVERAGE=2
MAX_TOTAL_EXPOSURE_USD=5000
MIN_SPREAD_PCT=0.5
DRY_RUN_MODE=true  # false для реальной торговли
```

## 🧪 Тестирование

### План тестирования:

1. **Unit тесты** для каждого exchange adapter
2. **Integration тесты** для торгового сервиса
3. **Testnet торговля** минимум 2 недели
4. **Paper trading** (симуляция) еще 1 месяц
5. Только после этого → **Real trading** с малым капиталом

### Пример теста:

```python
# tests/test_trading.py

import pytest
from services.trading import TradingService
from exchanges.bybit_adapter import BybitAdapter

@pytest.mark.asyncio
async def test_execute_hedge_dry_run():
    """Тест хеджа в dry-run режиме"""
    
    # Создаем адаптеры (testnet)
    bybit = BybitAdapter(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    binance = BinanceAdapter(
        api_key="test_key",
        api_secret="test_secret",
        testnet=True
    )
    
    exchanges = {
        "BYBIT": bybit,
        "BINANCE": binance
    }
    
    trading_service = TradingService(exchanges)
    
    # Симулируем возможность
    opportunity = {
        'token': 'BTC',
        'spread': 1.25,
        'long_exchange': 'BINANCE',
        'short_exchange': 'BYBIT',
        'long_rate': ...,
        'short_rate': ...
    }
    
    # Выполняем в dry-run
    result = await trading_service.execute_hedge(
        opportunity=opportunity,
        position_size_usd=100,
        leverage=1,
        dry_run=True
    )
    
    assert result is not None
    assert result.token == 'BTC'
```

## 📝 Roadmap

### Этап 1: Подготовка (1-2 недели)
- [ ] Получить API ключи от всех бирж
- [ ] Настроить testnet аккаунты
- [ ] Реализовать базовые торговые методы
- [ ] Добавить систему рисков

### Этап 2: Testnet (2-4 недели)
- [ ] Тестировать открытие/закрытие позиций
- [ ] Тестировать хедж стратегию
- [ ] Собрать статистику
- [ ] Отладить все баги

### Этап 3: Paper Trading (1-2 месяца)
- [ ] Симуляция реальной торговли
- [ ] Оптимизация параметров
- [ ] Бэктестинг стратегии
- [ ] Анализ результатов

### Этап 4: Production (с осторожностью!)
- [ ] Запуск с минимальным капиталом ($100-500)
- [ ] Мониторинг 24/7
- [ ] Постепенное увеличение капитала
- [ ] Continuous improvement

## ⚠️ DISCLAIMER

**КРИТИЧЕСКИ ВАЖНО:**

1. **Автоматическая торговля — это РИСК**
2. **Можете ПОТЕРЯТЬ все деньги**
3. **Начинайте с TESTNET**
4. **Используйте только средства, которые можете позволить себе потерять**
5. **Этот код НЕ является финансовым советом**
6. **Вы несете полную ответственность за свои торговые решения**

---

**Если есть вопросы — задавайте ДО начала реальной торговли! 🚨**
