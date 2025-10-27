import requests
from datetime import datetime, timezone


def get_top5_latest_group(symbols=None, limit_per_symbol=100):
    url = "https://fapi.binance.com/fapi/v1/fundingRate"
    all_rates = []

    if symbols is None:
        symbols = [None]

    for symbol in symbols:
        params = {'limit': limit_per_symbol}
        if symbol:
            params['symbol'] = symbol

        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Ошибка для {symbol}: {response.status_code}")
            continue

        data = response.json()
        for item in data:
            # добавляем модуль только для сортировки
            item['absFundingRate'] = abs(float(item['fundingRate']))
            all_rates.append(item)

    if not all_rates:
        return []

    # находим ближайший по времени fundingTime
    latest_time = max(item['fundingTime'] for item in all_rates)

    # фильтруем только эту группу
    latest_group = [item for item in all_rates if item['fundingTime'] == latest_time]

    # сортируем по модулю fundingRate по убыванию
    latest_group_sorted = sorted(latest_group, key=lambda x: x['absFundingRate'], reverse=True)

    # преобразуем дату в читаемый формат
    human_time = datetime.fromtimestamp(latest_time / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    # выводим табличку
    print(f"Funding Time (latest): {human_time} UTC\n")
    print(f"{'№':<3} {'Symbol':<10} {'FundingRate':<15} {'MarkPrice':<15} {'Time UTC'}")
    print("-" * 60)
    for i, r in enumerate(latest_group_sorted[:5], 1):
        print(f"{i:<3} {r['symbol']:<10} {r['fundingRate']:<15} {r['markPrice']:<15} {human_time}")


if __name__ == "__main__":
    get_top5_latest_group(symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SCRUSDT', 'SHELLUSDT'])
