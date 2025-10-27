"""Сервис кэширования с TTL и защитой от thundering herd."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Callable, Awaitable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Запись в кэше."""
    data: Any
    timestamp: datetime
    ttl_seconds: int
    
    def is_valid(self) -> bool:
        """Проверяет валидность кэша."""
        now = datetime.now(timezone.utc)
        age = (now - self.timestamp).total_seconds()
        return age < self.ttl_seconds


class AsyncCache:
    """
    Асинхронный кэш с TTL и защитой от одновременных обновлений.
    
    Особенности:
    - TTL (time to live) для каждой записи
    - Защита от thundering herd: если идет обновление, другие запросы ждут
    - Thread-safe для asyncio
    """
    
    def __init__(self, default_ttl: int = 30):
        """
        Args:
            default_ttl: TTL по умолчанию в секундах
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()  # Для защиты _locks
        
    async def get_or_fetch(
        self,
        key: str,
        fetch_func: Callable[[], Awaitable[Any]],
        ttl: Optional[int] = None
    ) -> Any:
        """
        Получает данные из кэша или вызывает fetch_func для получения.
        
        Если кэш валиден - возвращает кэш.
        Если кэш невалиден и идет обновление - ждет завершения обновления.
        Если кэш невалиден и обновление не идет - запускает обновление.
        
        Args:
            key: Ключ кэша
            fetch_func: Асинхронная функция для получения данных
            ttl: TTL в секундах (если None - использует default_ttl)
            
        Returns:
            Данные из кэша или от fetch_func
        """
        ttl = ttl or self.default_ttl
        
        # Проверяем кэш
        if key in self._cache and self._cache[key].is_valid():
            age = (datetime.now(timezone.utc) - self._cache[key].timestamp).total_seconds()
            logger.debug(f"Cache HIT for '{key}' (age: {age:.1f}s)")
            return self._cache[key].data
        
        # Получаем или создаем lock для этого ключа
        async with self._lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            lock = self._locks[key]
        
        # Пытаемся получить lock
        if lock.locked():
            # Кто-то уже обновляет, ждем
            logger.info(f"Cache WAIT for '{key}' - update in progress")
            async with lock:
                # После ожидания проверяем кэш снова
                if key in self._cache and self._cache[key].is_valid():
                    logger.debug(f"Cache HIT after wait for '{key}'")
                    return self._cache[key].data
        
        # Получаем lock и обновляем
        async with lock:
            # Double-check: может кто-то уже обновил пока мы ждали
            if key in self._cache and self._cache[key].is_valid():
                logger.debug(f"Cache HIT (double-check) for '{key}'")
                return self._cache[key].data
            
            # Обновляем кэш
            logger.info(f"Cache MISS for '{key}' - fetching data")
            try:
                data = await fetch_func()
                
                # Сохраняем в кэш
                self._cache[key] = CacheEntry(
                    data=data,
                    timestamp=datetime.now(timezone.utc),
                    ttl_seconds=ttl
                )
                
                logger.info(f"Cache UPDATED for '{key}' (TTL: {ttl}s)")
                return data
                
            except Exception as e:
                logger.error(f"Error fetching data for '{key}': {e}")
                # Если есть старый кэш - возвращаем его
                if key in self._cache:
                    logger.warning(f"Returning stale cache for '{key}' due to error")
                    return self._cache[key].data
                raise
    
    async def invalidate(self, key: str) -> None:
        """Инвалидирует кэш для ключа."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated for '{key}'")
    
    async def clear(self) -> None:
        """Очищает весь кэш."""
        self._cache.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша."""
        now = datetime.now(timezone.utc)
        stats = {
            'total_entries': len(self._cache),
            'valid_entries': 0,
            'expired_entries': 0,
            'entries': []
        }
        
        for key, entry in self._cache.items():
            is_valid = entry.is_valid()
            age = (now - entry.timestamp).total_seconds()
            
            if is_valid:
                stats['valid_entries'] += 1
            else:
                stats['expired_entries'] += 1
            
            stats['entries'].append({
                'key': key,
                'age_seconds': age,
                'ttl_seconds': entry.ttl_seconds,
                'valid': is_valid
            })
        
        return stats
    
    async def cleanup_expired(self) -> int:
        """Удаляет истекшие записи из кэша."""
        expired = [key for key, entry in self._cache.items() if not entry.is_valid()]
        for key in expired:
            del self._cache[key]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired cache entries")
        
        return len(expired)


# Глобальный экземпляр кэша
_global_cache: Optional[AsyncCache] = None


def get_cache(ttl: int = 30) -> AsyncCache:
    """Возвращает глобальный экземпляр кэша."""
    global _global_cache
    if _global_cache is None:
        _global_cache = AsyncCache(default_ttl=ttl)
    return _global_cache
