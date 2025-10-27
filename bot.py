"""Телеграм-бот для мониторинга funding rates."""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Dict, Set
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackContext
)

from exchanges import (
    BybitAdapter,
    BinanceAdapter,
    MexcAdapter,
    GateioAdapter,
    KucoinAdapter,
    BitgetAdapter,
    BingxAdapter,
    BitmartAdapter,
    OkxAdapter
)
from models import FundingRate
from services.aggregator import FundingRateAggregator
from services.formatter import MessageFormatter


# Создаем директорию для логов
logs_dir = Path(__file__).parent / "logs"
logs_dir.mkdir(exist_ok=True)

# Настройка логирования с записью в файлы
log_format = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Основной лог-файл (все уровни)
main_handler = RotatingFileHandler(
    logs_dir / "bot.log",
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5,
    encoding='utf-8'
)
main_handler.setFormatter(log_format)
main_handler.setLevel(logging.INFO)

# Лог-файл только для ошибок
error_handler = RotatingFileHandler(
    logs_dir / "errors.log",
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=3,
    encoding='utf-8'
)
error_handler.setFormatter(log_format)
error_handler.setLevel(logging.ERROR)

# Консольный вывод
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

# Настройка root logger
logging.basicConfig(
    level=logging.INFO,
    handlers=[main_handler, error_handler, console_handler]
)

# Отключаем избыточные логи от сторонних библиотек
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"📁 Логи сохраняются в: {logs_dir.absolute()}")

# Загрузка переменных окружения
load_dotenv()

# Глобальные переменные
aggregator: FundingRateAggregator = None
formatter = MessageFormatter()
user_settings: Dict[int, Dict] = {}  # {user_id: {threshold: float, monitoring: bool}}


class FundingBot:
    """Основной класс телеграм-бота."""
    
    def __init__(self, token: str, cache_ttl: int = 30, admin_user_id: int = None):
        self.token = token
        self.cache_ttl = cache_ttl
        self.admin_user_id = admin_user_id
        self.app = None
        self.aggregator = self._init_aggregator()
        self.formatter = MessageFormatter()
        self.user_settings: Dict[int, Dict] = {}
        self.alert_cooldown: Dict[str, datetime] = {}  # {token: last_alert_time}
        self.time_alert_sent: Dict[str, Set[str]] = {}  # {chat_id: set of "token_20m" or "token_10m"}
        
    def _init_aggregator(self) -> FundingRateAggregator:
        """Инициализация агрегатора с адаптерами бирж."""
        exchanges = [
            BybitAdapter(),
            BinanceAdapter(),
            MexcAdapter(),
            GateioAdapter(),
            KucoinAdapter(),
            BitgetAdapter(),
            BingxAdapter(),
            BitmartAdapter(),
            OkxAdapter(),
        ]
        logger.info(f"Initializing aggregator with {len(exchanges)} exchanges, cache TTL: {self.cache_ttl}s")
        return FundingRateAggregator(exchanges, cache_ttl=self.cache_ttl)
    
    def _is_admin(self, user_id: int) -> bool:
        """Проверка является ли пользователь администратором."""
        if self.admin_user_id is None:
            logger.warning("ADMIN_USER_ID not set - admin commands are disabled")
            return False
        return user_id == self.admin_user_id
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start."""
        chat_id = update.effective_chat.id
        
        # Инициализируем настройки чата (поддержка как ЛС, так и групп)
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {
                'threshold': 0.5,  # 0.5% по умолчанию
                'monitoring': False,
                'tokens': set(),  # Токены для мониторинга
                'time_alerts': False,  # Алерты за 20/10 минут до funding
            }
        
        welcome_message = (
            "👋 <b>Привет! Я Funding Rate Bot</b>\n\n"
            "📊 Мониторинг ставок финансирования на криптобиржах\n"
            "⚡ Асинхронный сбор данных от 9 бирж\n"
            "🚀 Кэширование данных (TTL 30 сек)\n\n"
            "<b>📋 Основные команды:</b>\n\n"
            "🏆 /top - Топ-5 токенов с ближайшим funding\n"
            "🔍 /token BTC - Данные по конкретному токену\n"
            "💎 /hedge - Найти возможности для хеджирования\n"
            "⚙️ /set_threshold 0.5 - Установить порог алерта\n"
            "🔔 /start_monitoring - Начать мониторинг по порогу\n"
            "🔕 /stop_monitoring - Остановить мониторинг\n"
            "⏰ /start_time_alerts - Алерты за 20/10 мин до funding\n"
            "⏰ /stop_time_alerts - Остановить time-based алерты\n"
            "📊 /status - Текущие настройки\n\n"
            "<b>🔧 Управление кэшем:</b>\n"
            "📈 /cache_stats - Статистика кэша\n"
            "🗑️ /clear_cache - Очистить кэш\n\n"
            "<i>💡 Поддерживаемые биржи: Bybit, Binance, MEXC, Gate.io, KuCoin, Bitget, BingX, BitMart, OKX</i>"
        )
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help."""
        await self.start(update, context)
    
    async def top_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /top - показать топ токенов."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        exchanges_list = ", ".join([ex.name for ex in self.aggregator.exchanges])
        await update.message.reply_text(f"🔄 Собираю данные от бирж: {exchanges_list}...")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔥 /top command from user {user_id} in chat {chat_id}")
        logger.info(f"{'='*80}")
        logger.info(f"📡 Активных бирж: {len(self.aggregator.exchanges)}")
        logger.info(f"📋 Список бирж: {exchanges_list}")
        
        try:
            from datetime import datetime
            start_time = datetime.now()
            
            # Получаем топ контракты, сгруппированные по токенам (ASYNC)
            logger.info(f"🚀 Начинаю сбор данных...")
            grouped = await self.aggregator.get_grouped_by_token(top_contracts_limit=5)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n{'='*80}")
            logger.info(f"⏱️  ИТОГО: Сбор данных завершен за {elapsed:.2f}s")
            logger.info(f"{'='*80}")
            
            if not grouped:
                logger.warning("❌ Не получено данных от бирж")
                await update.message.reply_text("Не удалось получить данные. Попробуйте позже.")
                return
            
            # Логируем итоговую статистику
            total_exchanges_responded = sum(len(rates) for rates in grouped.values())
            total_possible = len(grouped) * len(self.aggregator.exchanges)
            success_rate = (total_exchanges_responded / total_possible * 100) if total_possible > 0 else 0
            
            logger.info(f"📊 Статистика по токенам:")
            for token, rates in grouped.items():
                logger.info(f"   • {token}: {len(rates)}/{len(self.aggregator.exchanges)} бирж ответили")
            
            logger.info(f"\n✅ Общий успех: {total_exchanges_responded}/{total_possible} ({success_rate:.1f}%)")
            logger.info(f"{'='*80}\n")
            
            # Форматируем и отправляем отчет
            message = self.formatter.format_grouped_report(grouped, limit=5)
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"❌ Error in top_command: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            await update.message.reply_text(f"Произошла ошибка: {str(e)}")
    
    async def token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /token - получить данные по токену."""
        if not context.args:
            await update.message.reply_text("Использование: /token <SYMBOL>\nПример: /token BTC")
            return
        
        token = context.args[0].upper().replace('USDT', '')
        await update.message.reply_text(f"🔄 Получаю данные по {token}...")
        
        try:
            # Получаем данные от всех бирж ПАРАЛЛЕЛЬНО
            import asyncio
            tasks = []
            for exchange in self.aggregator.exchanges:
                tasks.append(self.aggregator._get_rate_for_token(exchange, token))
            
            # Запускаем все задачи параллельно
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Собираем успешные результаты
            rates = [r for r in results if isinstance(r, FundingRate)]
            
            if not rates:
                await update.message.reply_text(f"Не найдено данных по токену {token}")
                return
            
            # Сортируем по абсолютной ставке
            rates.sort(key=lambda x: x.abs_rate, reverse=True)
            
            # Форматируем сообщение
            message = self.formatter.format_alert(
                token=token,
                rates=rates,
                threshold=self.user_settings.get(update.effective_user.id, {}).get('threshold', 0.5)
            )
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in token_command: {e}")
            await update.message.reply_text(f"Произошла ошибка: {str(e)}")
    
    async def set_threshold_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /set_threshold - установить порог алерта."""
        if not context.args:
            await update.message.reply_text(
                "Использование: /set_threshold <VALUE>\n"
                "Пример: /set_threshold 0.5 (для порога в 0.5%)"
            )
            return
        
        try:
            threshold = float(context.args[0])
            chat_id = update.effective_chat.id
            
            if chat_id not in self.user_settings:
                self.user_settings[chat_id] = {'threshold': threshold, 'monitoring': False}
            else:
                self.user_settings[chat_id]['threshold'] = threshold
            
            await update.message.reply_text(f"✅ Порог алерта установлен на {threshold}%")
            
        except ValueError:
            await update.message.reply_text("Ошибка: укажите корректное числовое значение")
    
    async def start_monitoring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start_monitoring - начать мониторинг."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Используем chat_id для хранения настроек (поддержка групп)
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {'threshold': 0.5, 'monitoring': True}
        else:
            self.user_settings[chat_id]['monitoring'] = True
        
        # Останавливаем старую задачу если есть
        old_jobs = context.job_queue.get_jobs_by_name(f"monitor_{chat_id}")
        for job in old_jobs:
            job.schedule_removal()
        
        # Запускаем задачу мониторинга для чата
        context.job_queue.run_repeating(
            self.check_alerts,
            interval=600,  # каждые 10 минут
            first=10,
            data={'chat_id': chat_id},
            name=f"monitor_{chat_id}"
        )
        
        threshold = self.user_settings[chat_id]['threshold']
        chat_type = update.effective_chat.type
        chat_info = "группе" if chat_type in ['group', 'supergroup'] else "личке"
        
        await update.message.reply_text(
            f"✅ Мониторинг запущен в {chat_info}!\n"
            f"Порог: {threshold}%\n"
            f"Проверка каждые 10 минут"
        )
    
    async def stop_monitoring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop_monitoring - остановить мониторинг."""
        chat_id = update.effective_chat.id
        
        if chat_id in self.user_settings:
            self.user_settings[chat_id]['monitoring'] = False
        
        # Останавливаем задачу мониторинга
        jobs = context.job_queue.get_jobs_by_name(f"monitor_{chat_id}")
        for job in jobs:
            job.schedule_removal()
        
        await update.message.reply_text("✅ Мониторинг остановлен")
    
    async def start_time_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start_time_alerts - начать time-based алерты."""
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Используем chat_id для хранения настроек (поддержка групп)
        if chat_id not in self.user_settings:
            self.user_settings[chat_id] = {
                'threshold': 0.5,
                'monitoring': False,
                'time_alerts': True
            }
        else:
            self.user_settings[chat_id]['time_alerts'] = True
        
        # Останавливаем старую задачу если есть
        old_jobs = context.job_queue.get_jobs_by_name(f"time_alerts_{chat_id}")
        for job in old_jobs:
            job.schedule_removal()
        
        # Запускаем задачу проверки time-based алертов (каждые 2 минуты)
        context.job_queue.run_repeating(
            self.check_time_alerts,
            interval=120,  # каждые 2 минуты
            first=10,
            data={'chat_id': chat_id},
            name=f"time_alerts_{chat_id}"
        )
        
        chat_type = update.effective_chat.type
        chat_info = "группе" if chat_type in ['group', 'supergroup'] else "личке"
        
        await update.message.reply_text(
            f"✅ Time-based алерты запущены в {chat_info}!\n"
            f"⏰ Вы будете получать уведомления:\n"
            f"  • За 20 минут до funding\n"
            f"  • За 10 минут до funding\n"
            f"🔍 Проверка каждые 2 минуты"
        )
    
    async def stop_time_alerts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stop_time_alerts - остановить time-based алерты."""
        chat_id = update.effective_chat.id
        
        if chat_id in self.user_settings:
            self.user_settings[chat_id]['time_alerts'] = False
        
        # Останавливаем задачу time-based алертов
        jobs = context.job_queue.get_jobs_by_name(f"time_alerts_{chat_id}")
        for job in jobs:
            job.schedule_removal()
        
        # Очищаем отправленные алерты для этого чата
        if str(chat_id) in self.time_alert_sent:
            self.time_alert_sent[str(chat_id)].clear()
        
        await update.message.reply_text("✅ Time-based алерты остановлены")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показать текущие настройки."""
        chat_id = update.effective_chat.id
        settings = self.user_settings.get(chat_id, {'threshold': 0.5, 'monitoring': False, 'time_alerts': False})
        
        status_emoji = "🟢" if settings.get('monitoring') else "🔴"
        status_text = "Активен" if settings.get('monitoring') else "Неактивен"
        
        time_alerts_emoji = "🟢" if settings.get('time_alerts') else "🔴"
        time_alerts_text = "Активны" if settings.get('time_alerts') else "Неактивны"
        
        message = (
            f"\n📊 <b>Ваши настройки</b>\n"
            f"{'─' * 30}\n\n"
            f"⚙️ Порог алерта: <b>{settings.get('threshold', 0.5)}%</b>\n"
            f"{status_emoji} Мониторинг по порогу: <b>{status_text}</b>\n"
            f"{time_alerts_emoji} Time-based алерты: <b>{time_alerts_text}</b>\n\n"
            f"<i>💡 /start_monitoring - запуск мониторинга по порогу</i>\n"
            f"<i>⏰ /start_time_alerts - алерты за 20/10 мин до funding</i>"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def cache_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /cache_stats - показать статистику кэша (только для админа)."""
        user_id = update.effective_user.id
        
        # Проверка прав администратора
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
            logger.warning(f"User {user_id} attempted to access cache_stats without admin rights")
            return
        
        try:
            stats = await self.aggregator.get_cache_stats()
            
            message = f"\n📊 <b>Статистика кэша</b>\n"
            message += f"{'─' * 30}\n\n"
            message += f"⚙️ Cache TTL: <b>{self.cache_ttl}с</b>\n"
            message += f"📦 Всего записей: <b>{stats['total_entries']}</b>\n"
            message += f"✅ Валидных: <b>{stats['valid_entries']}</b>\n"
            message += f"❌ Истекших: <b>{stats['expired_entries']}</b>\n\n"
            
            if stats['entries']:
                message += "<b>Записи в кэше:</b>\n"
                for entry in stats['entries']:
                    status = "✅" if entry['valid'] else "❌"
                    message += f"{status} <code>{entry['key']}</code>\n"
                    message += f"   Возраст: {entry['age_seconds']:.1f}с / TTL: {entry['ttl_seconds']}с\n"
            else:
                message += "<i>Кэш пуст</i>"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in cache_stats_command: {e}")
            await update.message.reply_text(f"Ошибка: {str(e)}")
    
    async def clear_cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /clear_cache - очистить кэш (только для админа)."""
        user_id = update.effective_user.id
        
        # Проверка прав администратора
        if not self._is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав для выполнения этой команды")
            logger.warning(f"User {user_id} attempted to clear cache without admin rights")
            return
        
        try:
            await self.aggregator.clear_cache()
            await update.message.reply_text("✅ Кэш очищен")
            logger.info(f"Cache cleared by admin user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in clear_cache_command: {e}")
            await update.message.reply_text(f"Ошибка: {str(e)}")
    
    async def hedge_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /hedge - найти возможности для хеджирования."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Проверяем есть ли аргумент с минимальным спредом
        min_spread = 0.3  # По умолчанию 0.3%
        if context.args:
            try:
                min_spread = float(context.args[0])
                if min_spread < 0:
                    await update.message.reply_text("❌ Минимальный спред должен быть положительным числом")
                    return
            except ValueError:
                await update.message.reply_text(
                    "Использование: /hedge [MIN_SPREAD]\n"
                    "Пример: /hedge 0.5 (для минимального спреда 0.5%)\n"
                    "По умолчанию: 0.3%"
                )
                return
        
        exchanges_list = ", ".join([ex.name for ex in self.aggregator.exchanges])
        await update.message.reply_text(
            f"🔍 Ищу возможности для хеджирования...\n"
            f"Минимальный спред: {min_spread}%\n"
            f"Биржи: {exchanges_list}"
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"💎 /hedge command from user {user_id} in chat {chat_id}")
        logger.info(f"Min spread: {min_spread}%")
        logger.info(f"{'='*80}")
        
        try:
            from datetime import datetime
            start_time = datetime.now()
            
            # Получаем возможности для хеджирования
            logger.info(f"🚀 Начинаю поиск возможностей для хеджирования...")
            opportunities = await self.aggregator.find_hedging_opportunities(min_spread=min_spread)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"\n{'='*80}")
            logger.info(f"⏱️  ИТОГО: Поиск завершен за {elapsed:.2f}s")
            logger.info(f"{'='*80}")
            
            if not opportunities:
                await update.message.reply_text(
                    f"❌ Не найдено возможностей для хеджирования с минимальным спредом {min_spread}%\n\n"
                    f"💡 Попробуйте уменьшить минимальный спред: /hedge 0.2"
                )
                return
            
            # Логируем статистику
            logger.info(f"📊 Найдено возможностей: {len(opportunities)}")
            for i, opp in enumerate(opportunities[:5], 1):
                logger.info(
                    f"  {i}. {opp['token']}: Спред {opp['spread']:.4f}% | "
                    f"LONG {opp['long_exchange']} ({opp['long_rate'].rate_percentage:+.4f}%) | "
                    f"SHORT {opp['short_exchange']} ({opp['short_rate'].rate_percentage:+.4f}%)"
                )
            
            # Форматируем и отправляем отчет
            message = self.formatter.format_hedging_opportunities(opportunities, limit=5)
            await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"❌ Error in hedge_command: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Stack trace:\n{traceback.format_exc()}")
            await update.message.reply_text(f"Произошла ошибка: {str(e)}")
    
    async def check_alerts(self, context: CallbackContext):
        """Проверка алертов для чата (запускается периодически)."""
        chat_id = context.job.data['chat_id']
        settings = self.user_settings.get(chat_id)
        
        if not settings or not settings['monitoring']:
            return
        
        threshold = settings['threshold']
        
        try:
            logger.info(f"Checking alerts for chat {chat_id}, threshold {threshold}%")
            
            # Получаем топ контракты (ASYNC)
            grouped = await self.aggregator.get_grouped_by_token(top_contracts_limit=5)
            
            if not grouped:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ Не удалось получить данные от бирж"
                )
                return
            
            # Проверяем есть ли токены с превышением порога
            alerts = []
            for token, rates in grouped.items():
                if not rates:
                    continue
                
                top_rate = rates[0]
                
                # Проверяем, превышает ли абсолютная ставка порог
                if top_rate.abs_rate * 100 >= threshold:
                    # Проверяем cooldown (не чаще раза в час для одного токена)
                    cooldown_key = f"{chat_id}_{token}"
                    last_alert = self.alert_cooldown.get(cooldown_key)
                    
                    if last_alert and (datetime.now(timezone.utc) - last_alert).total_seconds() < 3600:
                        continue  # Пропускаем, если алерт был недавно
                    
                    alerts.append((token, rates))
                    
                    # Обновляем время последнего алерта
                    self.alert_cooldown[cooldown_key] = datetime.now(timezone.utc)
            
            # Формируем и отправляем сводку
            if alerts:
                # Есть алерты - отправляем их
                for token, rates in alerts:
                    top_rate = rates[0]
                    message = self.formatter.format_alert(
                        token=token,
                        rates=rates,
                        threshold=threshold,
                        source_exchange=top_rate.exchange
                    )
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    logger.info(f"Alert sent to chat {chat_id} for token {token}")
            else:
                # Нет алертов - отправляем обычную сводку
                message = self.formatter.format_top_tokens(grouped, source_exchange="BYBIT")
                summary = f"📊 <b>Регулярная сводка</b>\n"
                summary += f"⚙️ Порог алерта: <b>{threshold}%</b>\n"
                summary += f"✅ Все ставки ниже порога\n\n"
                summary += message
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=summary,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                
                logger.info(f"Regular summary sent to chat {chat_id} - no alerts")
        
        except Exception as e:
            logger.error(f"Error in check_alerts: {e}")
    
    async def check_time_alerts(self, context: CallbackContext):
        """Проверка алертов по времени до funding (за 20 и 10 минут)."""
        chat_id = context.job.data['chat_id']
        settings = self.user_settings.get(chat_id)
        
        if not settings or not settings.get('time_alerts'):
            return
        
        try:
            logger.info(f"Checking time-based alerts for chat {chat_id}")
            
            # Получаем топ контракты (ASYNC)
            grouped = await self.aggregator.get_grouped_by_token(top_contracts_limit=10)
            
            if not grouped:
                return
            
            # Инициализируем set для отслеживания отправленных алертов
            if str(chat_id) not in self.time_alert_sent:
                self.time_alert_sent[str(chat_id)] = set()
            
            current_time = datetime.now(timezone.utc)
            
            # Проверяем каждый токен
            for token, rates in grouped.items():
                if not rates:
                    continue
                
                # Берем ближайшее время funding
                top_rate = rates[0]
                time_until_funding = (top_rate.next_funding_time - current_time).total_seconds() / 60
                
                # Проверяем интервалы (с некоторой погрешностью)
                alert_key_20m = f"{token}_20m"
                alert_key_10m = f"{token}_10m"
                
                # За 20 минут (18-22 минуты)
                if 18 <= time_until_funding <= 22 and alert_key_20m not in self.time_alert_sent[str(chat_id)]:
                    message = (
                        f"⏰ <b>До funding осталось ~20 минут</b>\n\n"
                        f"🪙 <b>Токен:</b> {token}\n"
                        f"⏱️ <b>Funding через:</b> {int(time_until_funding)} мин\n"
                        f"📅 <b>Точное время:</b> {top_rate.next_funding_time.strftime('%H:%M:%S UTC')}\n\n"
                        f"📊 <b>Ставки на биржах:</b>\n"
                    )
                    
                    for rate in rates[:5]:  # Топ-5 бирж
                        message += f"• <b>{rate.exchange}:</b> {rate.rate_percentage:+.4f}% (${rate.price:.2f})\n"
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    self.time_alert_sent[str(chat_id)].add(alert_key_20m)
                    logger.info(f"20-minute alert sent to chat {chat_id} for token {token}")
                
                # За 10 минут (8-12 минут)
                elif 8 <= time_until_funding <= 12 and alert_key_10m not in self.time_alert_sent[str(chat_id)]:
                    message = (
                        f"⏰ <b>До funding осталось ~10 минут!</b>\n\n"
                        f"🪙 <b>Токен:</b> {token}\n"
                        f"⏱️ <b>Funding через:</b> {int(time_until_funding)} мин\n"
                        f"📅 <b>Точное время:</b> {top_rate.next_funding_time.strftime('%H:%M:%S UTC')}\n\n"
                        f"📊 <b>Ставки на биржах:</b>\n"
                    )
                    
                    for rate in rates[:5]:  # Топ-5 бирж
                        message += f"• <b>{rate.exchange}:</b> {rate.rate_percentage:+.4f}% (${rate.price:.2f})\n"
                    
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    self.time_alert_sent[str(chat_id)].add(alert_key_10m)
                    logger.info(f"10-minute alert sent to chat {chat_id} for token {token}")
                
                # Очищаем старые алерты (если funding прошло)
                if time_until_funding < 0:
                    self.time_alert_sent[str(chat_id)].discard(alert_key_20m)
                    self.time_alert_sent[str(chat_id)].discard(alert_key_10m)
        
        except Exception as e:
            logger.error(f"Error in check_time_alerts: {e}")
    
    def run(self):
        """Запуск бота."""
        self.app = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков команд
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("top", self.top_command))
        self.app.add_handler(CommandHandler("token", self.token_command))
        self.app.add_handler(CommandHandler("hedge", self.hedge_command))
        self.app.add_handler(CommandHandler("set_threshold", self.set_threshold_command))
        self.app.add_handler(CommandHandler("start_monitoring", self.start_monitoring_command))
        self.app.add_handler(CommandHandler("stop_monitoring", self.stop_monitoring_command))
        self.app.add_handler(CommandHandler("start_time_alerts", self.start_time_alerts_command))
        self.app.add_handler(CommandHandler("stop_time_alerts", self.stop_time_alerts_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("cache_stats", self.cache_stats_command))
        self.app.add_handler(CommandHandler("clear_cache", self.clear_cache_command))
        
        logger.info("Bot started")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Главная функция."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    # Читаем конфигурацию кэша из .env
    cache_ttl_str = os.getenv("CACHE_TTL", "30")
    # Обрезаем комментарии (все после #)
    cache_ttl_str = cache_ttl_str.split('#')[0].strip()
    try:
        cache_ttl = int(cache_ttl_str)
        logger.info(f"Cache TTL set to: {cache_ttl} seconds")
    except ValueError:
        logger.error(f"Invalid CACHE_TTL in .env: {cache_ttl_str}, using default 30")
        cache_ttl = 30
    
    # Читаем ID администратора из .env
    admin_user_id_str = os.getenv("ADMIN_USER_ID")
    admin_user_id = None
    if admin_user_id_str:
        # Обрезаем комментарии
        admin_user_id_str = admin_user_id_str.split('#')[0].strip()
        try:
            admin_user_id = int(admin_user_id_str)
            logger.info(f"Admin user ID set to: {admin_user_id}")
        except ValueError:
            logger.error(f"Invalid ADMIN_USER_ID in .env: {admin_user_id_str}")
    else:
        logger.warning("ADMIN_USER_ID not set - cache management commands will be disabled")
    
    bot = FundingBot(telegram_token, cache_ttl=cache_ttl, admin_user_id=admin_user_id)
    bot.run()


if __name__ == "__main__":
    main()
