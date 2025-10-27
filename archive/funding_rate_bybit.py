"""Устаревший скрипт для получения топ контрактов от Bybit.
Рекомендуется использовать новую архитектуру через exchanges/bybit_adapter.py
"""
import requests
from datetime import datetime, timezone


def get_top_bybit(limit: int = 5):
    """
    Получить топ контрактов от Bybit с наибольшими ставками финансирования.
    
    Args:
        limit: Количество контрактов для возврата (по умолчанию 5)
    """
    url = "https://www.bybit.com/x-api/contract/v5/public/support/trading-param?category=LinearPerpetual"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Ошибка запроса: {response.status_code}")
        return

    data = response.json()
    if data['ret_code'] != 0:
        print(f"Ошибка API: {data['ret_msg']}")
        return

    contracts = data['result']['list']

    # обработка пустых predictedFundingRate
    for c in contracts:
        try:
            c['predictedFundingRate'] = float(c.get('predictedFundingRate', 0) or 0)
        except ValueError:
            c['predictedFundingRate'] = 0
        c['absPredictedFundingRate'] = abs(c['predictedFundingRate'])

    # Сортируем и берем топ N (настраиваемый лимит)
    top_contracts = sorted(contracts, key=lambda x: x['absPredictedFundingRate'], reverse=True)[:limit]

    print(f"\nТоп-{limit} контрактов Bybit по ставке финансирования:\n")
    print(f"{'№':<3} {'Symbol':<12} {'FundingRate':<20} {'NextFundingTime':<20} {'Quote'}")
    print("-" * 80)
    for i, c in enumerate(top_contracts, 1):
        try:
            next_funding = datetime.fromtimestamp(int(c['nextFundingTimeE0']), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            next_funding = "N/A"
        
        # Показываем процент
        rate_pct = c['predictedFundingRate'] * 100
        print(f"{i:<3} {c['symbolName']:<12} {rate_pct:+.4f}%{'':<13} {next_funding:<20} {c['quoteCurrency']}")


# Обратная совместимость
def get_top5_bybit():
    """Обратная совместимость - получить топ-5."""
    get_top_bybit(limit=5)


if __name__ == "__main__":
    import sys
    
    # Проверяем, передан ли аргумент лимита
    limit = 5
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Ошибка: '{sys.argv[1]}' не является числом. Использую значение по умолчанию: 5")
    
    print("\n" + "="*80)
    print(" ВНИМАНИЕ: Это устаревший скрипт!")
    print(" Рекомендуется использовать новую систему: python example_usage.py")
    print("="*80)
    
    get_top_bybit(limit=limit)
    
    print("\n" + "="*80)
    print(f" Использование: python {sys.argv[0]} [limit]")
    print(f" Пример: python {sys.argv[0]} 20  (для получения топ-20)")
    print("="*80 + "\n")
