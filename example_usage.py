"""Примеры использования системы мониторинга funding rates."""
import logging
from exchanges import (
    BybitAdapter,
    BinanceAdapter,
    MexcAdapter,
    GateioAdapter,
    KucoinAdapter,
    BitgetAdapter,
    BingxAdapter
)
from services.aggregator import FundingRateAggregator
from services.formatter import MessageFormatter

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def example_1_get_top_rates():
    """Пример 1: Получить топ ставок от всех бирж."""
    print("\n" + "="*80)
    print("ПРИМЕР 1: Топ-10 ставок финансирования от всех бирж")
    print("="*80 + "\n")
    
    # Инициализация адаптеров
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        # Добавьте другие биржи по желанию
    ]
    
    # Создание агрегатора
    aggregator = FundingRateAggregator(exchanges, max_workers=5)
    
    # Получение топ ставок
    top_rates = aggregator.get_top_rates(limit=10, by_abs=True)
    
    # Форматирование и вывод
    formatter = MessageFormatter()
    message = formatter.format_simple_list(top_rates, limit=10)
    print(message)


def example_2_get_rates_by_token():
    """Пример 2: Получить ставки для конкретного токена от всех бирж."""
    print("\n" + "="*80)
    print("ПРИМЕР 2: Ставки для BTC от всех доступных бирж")
    print("="*80 + "\n")
    
    token = "BTC"
    
    # Инициализация
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        MexcAdapter(),
    ]
    
    aggregator = FundingRateAggregator(exchanges, max_workers=5)
    
    # Получаем ставки для BTC
    rates = []
    for exchange in exchanges:
        symbol_variants = FundingRateAggregator._get_symbol_variants(token, 'USDT')
        for symbol in symbol_variants:
            rate = exchange.get_funding_rate(symbol)
            if rate:
                rates.append(rate)
                break
    
    if rates:
        # Сортируем по абсолютной ставке
        rates.sort(key=lambda x: x.abs_rate, reverse=True)
        
        formatter = MessageFormatter()
        message = formatter.format_alert(
            token=token,
            rates=rates,
            threshold=0.5
        )
        print(message)
    else:
        print(f"Не найдено данных для {token}")


def example_3_get_grouped_by_token():
    """Пример 3: Получить топ контракты и сгруппировать по токенам."""
    print("\n" + "="*80)
    print("ПРИМЕР 3: Топ-5 токенов с группировкой по биржам")
    print("="*80 + "\n")
    
    # Инициализация с несколькими биржами
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        GateioAdapter(),
    ]
    
    aggregator = FundingRateAggregator(exchanges, max_workers=10)
    
    # Получаем топ контракты, сгруппированные по токенам
    print("Получаю топ контракты от Bybit и данные от других бирж...")
    grouped = aggregator.get_grouped_by_token(top_contracts_limit=10)
    
    # Форматируем и выводим
    formatter = MessageFormatter()
    message = formatter.format_grouped_report(grouped, limit=5)
    print(message)


def example_4_check_specific_exchanges():
    """Пример 4: Проверить доступность конкретных бирж."""
    print("\n" + "="*80)
    print("ПРИМЕР 4: Проверка доступности бирж")
    print("="*80 + "\n")
    
    exchanges = [
        BybitAdapter(),
        BinanceAdapter(),
        MexcAdapter(),
        GateioAdapter(),
        KucoinAdapter(),
        BitgetAdapter(),
        BingxAdapter(),
    ]
    
    for exchange in exchanges:
        try:
            is_available = exchange.is_available()
            status = "✅ Доступна" if is_available else "❌ Недоступна"
            print(f"{exchange.name:<12} - {status}")
        except Exception as e:
            print(f"{exchange.name:<12} - ❌ Ошибка: {str(e)[:50]}")


def example_5_single_exchange_top_contracts():
    """Пример 5: Получить топ контракты от одной биржи."""
    print("\n" + "="*80)
    print("ПРИМЕР 5: Топ-20 контрактов от Bybit")
    print("="*80 + "\n")
    
    bybit = BybitAdapter()
    
    # Получаем топ контракты (теперь с настраиваемым лимитом)
    contracts = bybit.get_top_contracts(limit=20)
    
    print(f"Получено контрактов: {len(contracts)}\n")
    print(f"{'№':<4} {'Symbol':<15} {'Base':<10} {'Quote'}")
    print("-" * 50)
    
    for i, contract in enumerate(contracts[:20], 1):
        print(f"{i:<4} {contract.symbol:<15} {contract.base_currency:<10} {contract.quote_currency}")


def main():
    """Запуск всех примеров."""
    print("\n" + "="*80)
    print(" ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ FUNDING RATE BOT")
    print("="*80)
    
    try:
        # Запускаем примеры по очереди
        example_4_check_specific_exchanges()
        
        example_5_single_exchange_top_contracts()
        
        example_1_get_top_rates()
        
        # Закомментируйте примеры ниже, если не хотите долго ждать
        # (они делают много запросов к API)
        
        # example_2_get_rates_by_token()
        
        # example_3_get_grouped_by_token()
        
        print("\n" + "="*80)
        print(" Примеры выполнены успешно!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
