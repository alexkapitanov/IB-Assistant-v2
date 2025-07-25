"""
Rate limiting для WebSocket соединений
"""
import asyncio
import time
from typing import Dict, Tuple, Optional
import redis
import os
import logging

logger = logging.getLogger(__name__)

# Настройки по умолчанию
DEFAULT_LIMIT = 5  # запросов
DEFAULT_WINDOW = 10  # секунд

class RateLimiter:
    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._redis_initialized = False
        self.local_cache: Dict[str, Tuple[int, float]] = {}  # ip -> (count, window_start)
    
    def _get_redis_client(self) -> Optional[redis.Redis]:
        """Ленивая инициализация Redis клиента"""
        if not self._redis_initialized:
            self._init_redis()
            self._redis_initialized = True
        return self._redis_client
    
    
    def _init_redis(self):
        """Инициализация Redis клиента с переменными окружения"""
        try:
            # Получаем настройки из переменных окружения
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            
            self._redis_client = redis.Redis(host=redis_host, port=redis_port, db=0, decode_responses=True, socket_timeout=5)
            # Проверяем соединение
            self._redis_client.ping()
            logger.info(f"Rate limiter using Redis at {redis_host}:{redis_port}")
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiting, using in-memory: {e}")
            self._redis_client = None
    
    async def check_rate_limit(self, ip: str, limit: int = DEFAULT_LIMIT, window: int = DEFAULT_WINDOW) -> bool:
        """
        Проверяет превышение лимита запросов
        Возвращает True если лимит превышен
        """
        redis_client = self._get_redis_client()
        if redis_client:
            return await self._check_redis(ip, limit, window, redis_client)
        else:
            return self._check_local(ip, limit, window)
    
    async def _check_redis(self, ip: str, limit: int, window: int, redis_client: redis.Redis) -> bool:
        """Проверка лимита через Redis"""
        try:
            key = f"rl:{ip}"
            current_time = int(time.time())
            
            # Получаем текущий счетчик
            current_count = await asyncio.get_event_loop().run_in_executor(
                None, redis_client.get, key
            )
            
            if current_count is None:
                # Первый запрос в окне
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: redis_client.setex(key, window, 1)
                )
                return False
            
            current_count = int(current_count)
            if current_count >= limit:
                return True  # Лимит превышен
            
            # Увеличиваем счетчик
            await asyncio.get_event_loop().run_in_executor(
                None, redis_client.incr, key
            )
            return False
            
        except Exception as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fallback на локальную проверку
            return self._check_local(ip, limit, window)
    
    def _check_local(self, ip: str, limit: int, window: int) -> bool:
        """Проверка лимита в памяти (fallback)"""
        current_time = time.time()
        
        if ip not in self.local_cache:
            self.local_cache[ip] = (1, current_time)
            return False
        
        count, window_start = self.local_cache[ip]
        
        # Проверяем, не истекло ли окно
        if current_time - window_start > window:
            self.local_cache[ip] = (1, current_time)
            return False
        
        if count >= limit:
            return True  # Лимит превышен
        
        # Увеличиваем счетчик
        self.local_cache[ip] = (count + 1, window_start)
        return False
    
    def cleanup_local_cache(self, max_age: int = 3600):
        """Очистка старых записей из локального кеша"""
        current_time = time.time()
        to_remove = []
        
        for ip, (_, window_start) in self.local_cache.items():
            if current_time - window_start > max_age:
                to_remove.append(ip)
        
        for ip in to_remove:
            del self.local_cache[ip]

# Глобальный экземпляр
rate_limiter = RateLimiter()

async def check_rate_limit(ip: str) -> bool:
    """Удобная функция для проверки лимита"""
    return await rate_limiter.check_rate_limit(ip)
