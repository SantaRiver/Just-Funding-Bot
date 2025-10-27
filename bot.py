"""Телеграм-бот для мониторинга funding rates."""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Set
import asyncio
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


# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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
            }
        
        welcome_message = (
            "👋 <b>Привет! Я Funding Rate Bot</b>\n\n"
            "📊 Мониторинг ставок финансирования на криптобиржах\n"
            "⚡ Асинхронный сбор данных от 9 бирж\n"
            "🚀 Кэширование данных (TTL 30 сек)\n\n"
            "<b>📋 Основные команды:</b>\n\n"
            "🏆 /top - Топ-5 токенов с ближайшим funding\n"
            "🔍 /token BTC - Данные по конкретному токену\n"
            "⚙️ /set_threshold 0.5 - Установить порог алерта\n"
            "🔔 /start_monitoring - Начать мониторинг\n"
            "🔕 /stop_monitoring - Остановить мониторинг\n"
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
        exchanges_list = ", ".join([ex.name for ex in self.aggregator.exchanges])
        await update.message.reply_text(f"🔄 Собираю данные от бирж: {exchanges_list}...")
        
        try:
            # Получаем топ контракты, сгруппированные по токенам (ASYNC)
            grouped = await self.aggregator.get_grouped_by_token(top_contracts_limit=5)
            
            if not grouped:
                await update.message.reply_text("Не удалось получить данные. Попробуйте позже.")
                return
            
            # Форматируем и отправляем отчет
            message = self.formatter.format_grouped_report(grouped, limit=5)
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error in top_command: {e}")
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
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показать текущие настройки."""
        chat_id = update.effective_chat.id
        settings = self.user_settings.get(chat_id, {'threshold': 0.5, 'monitoring': False})
        
        status_emoji = "🟢" if settings['monitoring'] else "🔴"
        status_text = "Активен" if settings['monitoring'] else "Неактивен"
        
        message = (
            f"\n📊 <b>Ваши настройки</b>\n"
            f"{'─' * 30}\n\n"
            f"⚙️ Порог алерта: <b>{settings['threshold']}%</b>\n"
            f"{status_emoji} Мониторинг: <b>{status_text}</b>\n\n"
            f"<i>💡 Используйте /start_monitoring для запуска</i>"
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
    
    def run(self):
        """Запуск бота."""
        self.app = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков команд
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("top", self.top_command))
        self.app.add_handler(CommandHandler("token", self.token_command))
        self.app.add_handler(CommandHandler("set_threshold", self.set_threshold_command))
        self.app.add_handler(CommandHandler("start_monitoring", self.start_monitoring_command))
        self.app.add_handler(CommandHandler("stop_monitoring", self.stop_monitoring_command))
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
