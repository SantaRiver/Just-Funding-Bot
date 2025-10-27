"""Сервис для форматирования сообщений."""
from typing import List, Dict
from datetime import datetime, timezone, timedelta
from models import FundingRate


class MessageFormatter:
    """Форматирование сообщений для телеграм-бота."""
    
    @staticmethod
    def _get_rate_emoji(rate: float) -> str:
        """Возвращает эмодзи в зависимости от значения ставки."""
        abs_rate = abs(rate * 100)
        if abs_rate >= 1.0:
            return "🔴"  # Очень высокая
        elif abs_rate >= 0.5:
            return "🟠"  # Высокая
        elif abs_rate >= 0.1:
            return "🟡"  # Средняя
        else:
            return "🟢"  # Низкая
    
    @staticmethod
    def _get_direction_emoji(rate: float) -> str:
        """Возвращает стрелку в зависимости от направления ставки."""
        if rate > 0:
            return "📈"  # Long платят Short
        elif rate < 0:
            return "📉"  # Short платят Long
        else:
            return "➖"  # Нейтральная
    
    @staticmethod
    def _get_contract_link(exchange: str, symbol: str, token: str) -> str:
        """Генерирует ссылку на контракт для конкретной биржи."""
        # Очищаем символ от суффиксов
        clean_symbol = symbol.replace('PERP', '').replace('_USDT', '').replace('-USDT', '')
        
        urls = {
            'BYBIT': f'https://www.bybit.com/trade/usdt/{token}USDT',
            'BINANCE': f'https://www.binance.com/en/futures/{token}USDT',
            'MEXC': f'https://futures.mexc.com/exchange/{token}_USDT',
            'GATE': f'https://www.gate.io/futures_trade/USDT/{token}_USDT',
            'GATEIO': f'https://www.gate.io/futures_trade/USDT/{token}_USDT',
            'KUCOIN': f'https://www.kucoin.com/futures/trade/{token}USDTM',
            'BITGET': f'https://www.bitget.com/futures/usdt/{token}USDT',
            'BINGX': f'https://bingx.com/en-us/swap/{token}-USDT/',
            'BITMART': f'https://www.bitmart.com/contract/en?symbol={token}USDT',
            'OKX': f'https://www.okx.com/trade-swap/{token.lower()}-usdt-swap',
        }
        
        url = urls.get(exchange.upper(), '#')
        # Возвращаем кликабельную ссылку в HTML формате
        return f'<a href="{url}">Открыть ↗</a>'
    
    @staticmethod
    def format_alert(
        token: str,
        rates: List[FundingRate],
        threshold: float,
        source_exchange: str = None
    ) -> str:
        """
        Форматирует алерт о высокой ставке финансирования.
        
        Args:
            token: Базовый токен
            rates: Список ставок от разных бирж (отсортирован по убыванию abs rate)
            threshold: Пороговое значение в процентах
            source_exchange: Биржа-источник топа
            
        Returns:
            Отформатированное сообщение
        """
        if not rates:
            return ""
        
        # Получаем топовую ставку
        top_rate = rates[0]
        
        # Рассчитываем время до следующего funding
        now = datetime.now(timezone.utc)
        time_diff = top_rate.next_funding_time - now
        hours = int(time_diff.total_seconds() // 3600)
        minutes = int((time_diff.total_seconds() % 3600) // 60)
        
        # Конвертируем в UTC+3 для отображения
        local_time = top_rate.next_funding_time + timedelta(hours=3)
        date_str = local_time.strftime('%d-%m-%Y %H:%M')
        
        # Эмодзи для заголовка
        emoji = MessageFormatter._get_rate_emoji(top_rate.rate)
        direction = MessageFormatter._get_direction_emoji(top_rate.rate)
        
        # Формируем заголовок
        source_text = f" на {source_exchange}" if source_exchange else ""
        header = f"\n{emoji} <b>АЛЕРТ: {token}{source_text}</b> {direction}\n"
        header += f"⏰ Осталось: <b>{hours}ч {minutes}мин</b>\n"
        header += f"📊 Порог: {threshold}% | 📅 {date_str} (UTC+3)\n"
        header += f"{'─' * 45}\n\n"
        
        # Формируем таблицу с использованием HTML
        table = "<pre>"
        table += f"{'Биржа':<10} │ {'Цена':<9} │ {'Rate':<9} │ {'⏱️':<7}\n"
        table += f"{'─'*10}─┼─{'─'*9}─┼─{'─'*9}─┼─{'─'*7}\n"
        
        for i, rate in enumerate(rates, 1):  # Показываем все биржи
            time_to_funding = rate.next_funding_time - now
            hours_left = int(time_to_funding.total_seconds() // 3600)
            mins_left = int((time_to_funding.total_seconds() % 3600) // 60)
            countdown = f"{hours_left:02d}:{mins_left:02d}"
            
            # Форматируем процент со знаком
            rate_pct = rate.rate_percentage
            rate_str = f"{rate_pct:+.4f}%"
            
            # Эмодзи для каждой биржи
            rate_emoji = MessageFormatter._get_rate_emoji(rate.rate)
            
            # Форматируем цену
            if rate.price >= 1000:
                price_str = f"{rate.price:,.0f}"
            else:
                price_str = f"{rate.price:.2f}"
            
            table += f"{rate.exchange:<10} │ {price_str:<9} │ {rate_str:<9} │ {countdown:<7}\n"
        
        table += "</pre>"
        
        # Добавляем ссылки на контракты
        links = "📊 <b>Ссылки на контракты:</b>\n"
        for rate in rates:
            link = MessageFormatter._get_contract_link(rate.exchange, rate.symbol, token)
            links += f"  • <b>{rate.exchange}</b>: {link}\n"
        
        # Добавляем легенду
        legend = f"\n💡 <i>Легенда: 🔴 &gt;1% | 🟠 &gt;0.5% | 🟡 &gt;0.1% | 🟢 &lt;0.1%</i>\n"
        legend += f"<i>📈 Long→Short | 📉 Short→Long</i>"
        
        return header + table + links + legend
    
    @staticmethod
    def format_grouped_report(
        grouped_rates: Dict[str, List[FundingRate]],
        limit: int = 5
    ) -> str:
        """
        Форматирует отчет по топ токенам.
        
        Args:
            grouped_rates: Словарь {токен: [список ставок]}
            limit: Количество токенов для отображения
            
        Returns:
            Отформатированное сообщение
        """
        if not grouped_rates:
            return "❌ Нет данных для отображения"
        
        # Сортируем токены по максимальной абсолютной ставке
        sorted_tokens = sorted(
            grouped_rates.items(),
            key=lambda x: max(r.abs_rate for r in x[1]),
            reverse=True
        )[:limit]
        
        # Получаем информацию о времени funding
        now = datetime.now(timezone.utc)
        first_token_rates = sorted_tokens[0][1] if sorted_tokens else []
        if first_token_rates:
            # Берем время от первой ставки (должно быть от Bybit)
            bybit_rate = next((r for r in first_token_rates if r.exchange == "BYBIT"), first_token_rates[0])
            funding_time_local = bybit_rate.next_funding_time + timedelta(hours=3)
            time_str = funding_time_local.strftime('%H:%M')
            date_str = funding_time_local.strftime('%d.%m')
            
            # Проверяем что все токены из одной временной группы
            all_same_time = True
            for token, rates in sorted_tokens:
                bybit_rate_token = next((r for r in rates if r.exchange == "BYBIT"), None)
                if bybit_rate_token:
                    time_diff_check = abs((bybit_rate_token.next_funding_time - bybit_rate.next_funding_time).total_seconds() / 60)
                    if time_diff_check > 5:  # Более 5 минут разницы
                        all_same_time = False
                        import logging
                        logging.warning(f"⚠️  Token {token} has different funding time: {bybit_rate_token.next_funding_time} (diff: {time_diff_check:.1f} min)")
        else:
            time_str, date_str = "N/A", "N/A"
        
        # Заголовок
        message = f"\n🏆 <b>ТОП-{len(sorted_tokens)} ТОКЕНОВ</b>\n"
        message += f"⏰ Bybit funding: <b>{time_str}</b> ({date_str}, UTC+3)\n"
        message += f"<i>Другие биржи могут иметь другое время ⬇️</i>\n"
        message += f"{'─' * 45}\n\n"
        
        # Для каждого токена создаем красивую карточку
        for i, (token, rates) in enumerate(sorted_tokens, 1):
            if not rates:
                continue
            
            top_rate = rates[0]
            emoji = MessageFormatter._get_rate_emoji(top_rate.rate)
            direction = MessageFormatter._get_direction_emoji(top_rate.rate)
            
            # Получаем Bybit время для этого токена
            bybit_rate = next((r for r in rates if r.exchange == "BYBIT"), top_rate)
            token_time_local = bybit_rate.next_funding_time + timedelta(hours=3)
            token_time_str = token_time_local.strftime('%H:%M')
            
            # Заголовок токена с временем
            message += f"\n{emoji} <b>{i}. {token}</b> {direction} "
            message += f"<i>(⏰ {token_time_str})</i>\n"
            
            # Форматируем цену
            if top_rate.price >= 1000:
                price_str = f"${top_rate.price:,.0f}"
            else:
                price_str = f"${top_rate.price:.2f}"
            
            message += f"💰 Цена: {price_str}\n"
            
            # Таблица с биржами (показываем время для каждой)
            message += "<pre>"
            message += f"{'Биржа':<10} │ {'Rate':<9} │ {'Время':<7}\n"
            message += f"{'─'*10}─┼─{'─'*9}─┼─{'─'*7}\n"
            
            for rate in rates:  # Показываем все биржи
                rate_str = f"{rate.rate_percentage:+.4f}%"
                
                # Конкретное время funding для этой биржи (UTC+3)
                rate_time_local = rate.next_funding_time + timedelta(hours=3)
                time_str = rate_time_local.strftime('%H:%M')
                
                message += f"{rate.exchange:<10} │ {rate_str:<9} │ {time_str:<7}\n"
            
            message += "</pre>\n"
            
            # Таблица со ссылками на контракты (без pre, чтобы ссылки работали)
            message += "📊 <b>Ссылки на контракты:</b>\n"
            
            for rate in rates:
                # Генерируем ссылку на контракт
                link = MessageFormatter._get_contract_link(rate.exchange, rate.symbol, token)
                message += f"  • <b>{rate.exchange}</b>: {link}\n"
            
            message += ""
        
        # Добавляем легенду
        message += f"\n💡 <i>🔴 Очень высокая | 🟠 Высокая | 🟡 Средняя | 🟢 Низкая</i>\n"
        message += f"<i>📈 Long→Short | 📉 Short→Long</i>\n"
        message += f"<i>⏰ Все времена в UTC+3 (МСК). Разные биржи = разное время funding</i>"
        
        return message
    
    @staticmethod
    def format_simple_list(rates: List[FundingRate], limit: int = 10) -> str:
        """
        Форматирует простой список ставок.
        
        Args:
            rates: Список ставок
            limit: Количество для отображения
            
        Returns:
            Отформатированное сообщение
        """
        if not rates:
            return "Нет данных"
        
        message = "```\n"
        message += f"{'№':<3} {'Exchange':<10} {'Symbol':<12} {'Rate':<10} {'Price':<12}\n"
        message += "-" * 60 + "\n"
        
        for i, rate in enumerate(rates[:limit], 1):
            rate_str = f"{rate.rate_percentage:+.4f}%"
            message += f"{i:<3} {rate.exchange:<10} {rate.symbol:<12} {rate_str:<10} ${rate.price:<11.2f}\n"
        
        message += "```"
        
        return message
    
    @staticmethod
    def format_hedging_opportunities(opportunities: List[Dict], limit: int = 5) -> str:
        """
        Форматирует список возможностей для хеджирования.
        
        Args:
            opportunities: Список словарей с информацией о возможностях
            limit: Количество возможностей для отображения
            
        Returns:
            Отформатированное сообщение
        """
        if not opportunities:
            return "❌ Не найдено возможностей для хеджирования с заданными параметрами"
        
        # Заголовок
        message = f"\n💎 <b>ВОЗМОЖНОСТИ ДЛЯ ХЕДЖИРОВАНИЯ</b>\n"
        message += f"<i>Найдено: {len(opportunities)} | Показано топ-{min(limit, len(opportunities))}</i>\n"
        message += f"{'─' * 45}\n\n"
        
        # Показываем топ возможностей
        for i, opp in enumerate(opportunities[:limit], 1):
            token = opp['token']
            spread = opp['spread']
            long_rate = opp['long_rate']
            short_rate = opp['short_rate']
            long_exch = opp['long_exchange']
            short_exch = opp['short_exchange']
            
            # Определяем эмодзи по размеру спреда
            if spread >= 1.0:
                spread_emoji = "🔥"  # Очень выгодный спред
            elif spread >= 0.5:
                spread_emoji = "💰"  # Хороший спред
            else:
                spread_emoji = "💵"  # Средний спред
            
            # Заголовок возможности
            message += f"{spread_emoji} <b>{i}. {token}</b>\n"
            message += f"📊 Спред: <b>{spread:.4f}%</b>\n"
            
            # Форматируем цену
            if long_rate.price >= 1000:
                price_str = f"${long_rate.price:,.0f}"
            else:
                price_str = f"${long_rate.price:.2f}"
            message += f"💰 Цена: {price_str}\n\n"
            
            # Стратегия
            message += f"<b>🎯 Стратегия:</b>\n"
            message += f"📈 LONG на <b>{long_exch}</b>: {long_rate.rate_percentage:+.4f}%\n"
            message += f"📉 SHORT на <b>{short_exch}</b>: {short_rate.rate_percentage:+.4f}%\n\n"
            
            # Потенциальная прибыль
            profit_per_cycle = spread
            message += f"💵 Прибыль за цикл: <b>~{profit_per_cycle:.4f}%</b>\n"
            
            # Информация о времени
            from datetime import timezone, timedelta
            now = datetime.now(timezone.utc)
            time_to_funding = long_rate.next_funding_time - now
            hours = int(time_to_funding.total_seconds() // 3600)
            minutes = int((time_to_funding.total_seconds() % 3600) // 60)
            
            message += f"⏰ До funding: <b>{hours}ч {minutes}мин</b>\n\n"
            
            # Таблица со всеми биржами
            message += "<pre>"
            message += f"{'Биржа':<10} │ {'Rate':<9}\n"
            message += f"{'─'*10}─┼─{'─'*9}\n"
            
            # Сортируем от минимальной к максимальной ставке
            sorted_rates = sorted(opp['all_rates'], key=lambda x: x.rate)
            for rate in sorted_rates:
                rate_str = f"{rate.rate_percentage:+.4f}%"
                # Отмечаем выбранные биржи
                marker = ""
                if rate.exchange == long_exch:
                    marker = " 📈"
                elif rate.exchange == short_exch:
                    marker = " 📉"
                
                message += f"{rate.exchange:<10} │ {rate_str:<9}{marker}\n"
            
            message += "</pre>\n"
            
            # Ссылки на контракты
            message += "📊 <b>Ссылки:</b>\n"
            long_link = MessageFormatter._get_contract_link(long_exch, long_rate.symbol, token)
            short_link = MessageFormatter._get_contract_link(short_exch, short_rate.symbol, token)
            message += f"  • <b>{long_exch}</b> (LONG): {long_link}\n"
            message += f"  • <b>{short_exch}</b> (SHORT): {short_link}\n"
            
            # Разделитель между возможностями
            if i < min(limit, len(opportunities)):
                message += f"\n{'─' * 45}\n\n"
        
        # Легенда
        message += f"\n\n💡 <i>Спред = разница между макс и мин ставками</i>\n"
        message += f"<i>📈 LONG = покупка | 📉 SHORT = продажа</i>\n"
        message += f"<i>🔥 &gt;1% | 💰 &gt;0.5% | 💵 &gt;0.3%</i>\n"
        message += f"\n⚠️ <b>Важно:</b> <i>Учитывайте комиссии, проскальзывание и риски</i>"
        
        return message
