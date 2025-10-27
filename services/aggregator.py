"""Асинхронный сервис для агрегации данных от разных бирж."""
from typing import List, Dict, Optional
from datetime import datetime, timezone
import logging
import asyncio

from models import FundingRate
from exchanges.base import ExchangeAdapter
from services.cache import get_cache


logger = logging.getLogger(__name__)


class FundingRateAggregator:
    """Асинхронный сервис для агрегации ставок финансирования от разных бирж."""
    
    def __init__(self, exchanges: List[ExchangeAdapter], cache_ttl: int = 30):
        """
        Инициализация агрегатора.
        
        Args:
            exchanges: Список адаптеров бирж
            cache_ttl: Время жизни кэша в секундах (по умолчанию 30)
        """
        self.exchanges = exchanges
        self.cache = get_cache(ttl=cache_ttl)
        self.cache_ttl = cache_ttl
    
    def get_rates_by_symbol(self, symbol: str) -> List[FundingRate]:
        """
        Получить ставки финансирования для конкретного символа от всех бирж.
        
        Args:
            symbol: Символ контракта (будет нормализован для каждой биржи)
            
        Returns:
            Список ставок от всех доступных бирж
        """
        rates = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаем задачи для каждой биржи
            future_to_exchange = {
                executor.submit(self._safe_get_funding_rate, exchange, symbol): exchange
                for exchange in self.exchanges
            }
            
            # Собираем результаты по мере выполнения
            for future in as_completed(future_to_exchange):
                exchange = future_to_exchange[future]
                try:
                    rate = future.result()
                    if rate:
                        rates.append(rate)
                except Exception as e:
                    logger.error(f"Error getting rate from {exchange.name}: {e}")
        
        return rates
    
    def get_all_rates(self) -> List[FundingRate]:
        """
        Получить все ставки финансирования от всех бирж.
        
        Returns:
            Список всех ставок
        """
        all_rates = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Создаем задачи для каждой биржи
            future_to_exchange = {
                executor.submit(self._safe_get_all_rates, exchange): exchange
                for exchange in self.exchanges
            }
            
            # Собираем результаты
            for future in as_completed(future_to_exchange):
                exchange = future_to_exchange[future]
                try:
                    rates = future.result()
                    all_rates.extend(rates)
                    logger.info(f"Got {len(rates)} rates from {exchange.name}")
                except Exception as e:
                    logger.error(f"Error getting rates from {exchange.name}: {e}")
        
        return all_rates
    
    def get_top_rates(self, limit: int = 20, by_abs: bool = True) -> List[FundingRate]:
        """
        Получить топ ставок финансирования.
        
        Args:
            limit: Количество топ ставок
            by_abs: Сортировать по абсолютному значению
            
        Returns:
            Отсортированный список ставок
        """
        all_rates = self.get_all_rates()
        
        if by_abs:
            all_rates.sort(key=lambda x: x.abs_rate, reverse=True)
        else:
            all_rates.sort(key=lambda x: x.rate, reverse=True)
        
        return all_rates[:limit]
    
    async def get_grouped_by_token(self, top_contracts_limit: int = 5) -> Dict[str, List[FundingRate]]:
        """
        Получить данные, сгруппированные по токенам (ASYNC) с кэшированием.
        Использует Bybit для получения топ контрактов по следующему funding time,
        затем собирает данные по ним от всех бирж.
        
        Логика:
        1. Проверка кэша (TTL 30 сек по умолчанию)
        2. Получить все funding rates от Bybit
        3. Сгруппировать по времени следующего funding
        4. Взять ближайшую по времени группу
        5. Отсортировать по funding rate (по абсолютному значению)
        6. Взять топ-N контрактов
        7. Для каждого контракта собрать данные от всех бирж ПАРАЛЛЕЛЬНО
        
        Args:
            top_contracts_limit: Количество топ контрактов для анализа (по умолчанию 5)
            
        Returns:
            Словарь {base_token: [список ставок от разных бирж]}
        """
        # Ключ кэша включает параметры запроса
        cache_key = f"grouped_by_token:{top_contracts_limit}"
        
        # Используем кэш с защитой от одновременных запросов
        return await self.cache.get_or_fetch(
            key=cache_key,
            fetch_func=lambda: self._fetch_grouped_by_token(top_contracts_limit),
            ttl=self.cache_ttl
        )
    
    async def _fetch_grouped_by_token(self, top_contracts_limit: int = 5) -> Dict[str, List[FundingRate]]:
        """
        Внутренний метод для получения данных (без кэша).
        Вызывается только когда кэш невалиден.
        """
        # Получаем Bybit как источник топ контрактов
        source_exchange = next((ex for ex in self.exchanges if ex.name == "BYBIT"), None)
        if not source_exchange:
            source_exchange = self.exchanges[0] if self.exchanges else None
        
        if not source_exchange:
            logger.error("No exchanges available")
            return {}
        
        # Получаем ВСЕ funding rates от Bybit
        logger.info(f"Getting all funding rates from {source_exchange.name}")
        all_bybit_rates = await source_exchange.get_all_funding_rates()
        
        if not all_bybit_rates:
            logger.warning("No funding rates found from Bybit")
            return {}
        
        logger.info(f"Got {len(all_bybit_rates)} funding rates from Bybit")
        
        # Группируем по времени следующего funding
        from collections import defaultdict
        time_groups = defaultdict(list)
        
        for rate in all_bybit_rates:
            # Округляем время до минуты для группировки
            funding_time_key = rate.next_funding_time.replace(second=0, microsecond=0)
            time_groups[funding_time_key].append(rate)
        
        if not time_groups:
            logger.warning("No time groups found")
            return {}
        
        # Находим ближайшее время
        now = datetime.now(timezone.utc)
        future_times = [t for t in time_groups.keys() if t > now]
        
        if not future_times:
            logger.warning("No future funding times found")
            return {}
        
        # Логируем все доступные времена для диагностики
        logger.info(f"Available funding times: {sorted(future_times)[:3]}")
        
        nearest_time = min(future_times)
        logger.info(f"✅ Nearest funding time: {nearest_time} (in {(nearest_time - now).total_seconds() / 60:.1f} minutes)")
        
        # Берем группу с ближайшим временем
        nearest_group = time_groups[nearest_time]
        logger.info(f"Found {len(nearest_group)} contracts with nearest funding time")
        
        # Проверяем что все контракты действительно из одной группы
        for rate in nearest_group:
            time_diff_minutes = (rate.next_funding_time - nearest_time).total_seconds() / 60
            if abs(time_diff_minutes) > 1:  # Больше 1 минуты разницы
                logger.warning(f"⚠️  Contract {rate.symbol} has different funding time: {rate.next_funding_time} (diff: {time_diff_minutes:.1f} min)")
        
        # Сортируем по абсолютному значению funding rate
        nearest_group.sort(key=lambda x: x.abs_rate, reverse=True)
        
        # Берем топ-N контрактов
        top_contracts = nearest_group[:top_contracts_limit]
        logger.info(f"Selected top {len(top_contracts)} contracts by funding rate:")
        for i, contract in enumerate(top_contracts, 1):
            logger.info(f"  {i}. {contract.symbol}: {contract.rate_percentage:+.4f}% (funding at {contract.next_funding_time})")
        
        # Для каждого контракта собираем данные от всех бирж ПАРАЛЛЕЛЬНО
        grouped_rates: Dict[str, List[FundingRate]] = {}
        
        for bybit_rate in top_contracts:
            # Извлекаем базовый токен из символа
            symbol = bybit_rate.symbol
            base_token = symbol.replace('USDT', '').replace('PERP', '')
            
            logger.info(f"Getting rates for {base_token} (Bybit rate: {bybit_rate.rate_percentage:+.4f}%)...")
            
            # Собираем данные от всех бирж ПАРАЛЛЕЛЬНО
            rates = [bybit_rate]  # Добавляем ставку от Bybit
            
            # Создаем задачи для всех бирж (кроме Bybit)
            tasks = []
            for exchange in self.exchanges:
                if exchange.name == "BYBIT":
                    continue
                tasks.append(self._get_rate_for_token(exchange, base_token))
            
            # Запускаем все задачи параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Собираем результаты
            for result in results:
                if isinstance(result, FundingRate):
                    rates.append(result)
                elif isinstance(result, Exception):
                    logger.debug(f"Task failed: {result}")
            
            if rates:
                # Сортируем по абсолютному значению ставки
                rates.sort(key=lambda x: x.abs_rate, reverse=True)
                grouped_rates[base_token] = rates
                logger.info(f"  -> Collected {len(rates)} rates for {base_token}")
        
        return grouped_rates
    
    async def _get_rate_for_token(self, exchange: ExchangeAdapter, base_token: str) -> Optional[FundingRate]:
        """Вспомогательный метод для получения ставки от одной биржи."""
        try:
            symbol_variants = self._get_symbol_variants(base_token, 'USDT')
            
            logger.debug(f"{exchange.name}: trying variants {symbol_variants} for {base_token}")
            
            for symbol_variant in symbol_variants:
                rate = await exchange.get_funding_rate(symbol_variant)
                if rate:
                    logger.info(f"  ✅ {exchange.name}: {base_token} = {rate.rate_percentage:+.4f}%")
                    return rate
            
            logger.warning(f"  ⚠️  {exchange.name}: No data for {base_token} (tried {len(symbol_variants)} variants)")
            return None
        except Exception as e:
            logger.error(f"  ❌ {exchange.name}: Error for {base_token}: {e}")
            return None
    
    def _safe_get_funding_rate(self, exchange: ExchangeAdapter, symbol: str) -> Optional[FundingRate]:
        """Безопасное получение ставки с обработкой ошибок."""
        try:
            return exchange.get_funding_rate(symbol)
        except Exception as e:
            logger.debug(f"Error getting rate from {exchange.name} for {symbol}: {e}")
            return None
    
    def _safe_get_all_rates(self, exchange: ExchangeAdapter) -> List[FundingRate]:
        """Безопасное получение всех ставок с обработкой ошибок."""
        try:
            return exchange.get_all_funding_rates()
        except Exception as e:
            logger.error(f"Error getting all rates from {exchange.name}: {e}")
            return []
    
    async def get_cache_stats(self) -> Dict:
        """Получить статистику кэша."""
        return self.cache.get_stats()
    
    async def clear_cache(self) -> None:
        """Очистить кэш."""
        await self.cache.clear()
    
    async def invalidate_cache(self, key: str) -> None:
        """Инвалидировать конкретный ключ кэша."""
        await self.cache.invalidate(key)
    
    @staticmethod
    def _get_symbol_variants(base: str, quote: str) -> List[str]:
        """
        Генерирует варианты символов для разных бирж.
        
        Args:
            base: Базовый актив (например, BTC)
            quote: Котируемый актив (например, USDT)
            
        Returns:
            Список вариантов символов
        """
        return [
            f"{base}{quote}",       # BTCUSDT (Binance, Bybit)
            f"{base}_{quote}",      # BTC_USDT (Gate.io, MEXC)
            f"{base}-{quote}",      # BTC-USDT (BingX)
            f"{base}{quote}M",      # BTCUSDTM (KuCoin может использовать)
        ]
