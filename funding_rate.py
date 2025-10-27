import os
import logging
from dotenv import load_dotenv
from binance.um_futures import UMFutures
from datetime import datetime
import time
from itertools import groupby

logging.basicConfig(level=logging.INFO)
load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
client = UMFutures(key=API_KEY, secret=API_SECRET)


def get_upcoming_usdt_funding(top_n=10, limit_per_symbol=1):
    now_ts = int(time.time() * 1000)

    # Получаем список всех USDT-M perpetual символов
    exchange_info = client.exchange_info()
    symbols = [s['symbol'] for s in exchange_info['symbols'] if s['contractType'] == 'PERPETUAL']
    logging.info(f"Всего USDT-M perpetual символов: {len(symbols)}")

    upcoming_rates = []

    for symbol in symbols:
        try:
            rates = client.funding_rate(symbol=symbol, limit=limit_per_symbol)
            for r in rates:
                if r['fundingTime'] >= now_ts:
                    r['symbol'] = symbol
                    r['readableTime'] = datetime.fromtimestamp(r['fundingTime'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    upcoming_rates.append(r)
        except Exception as e:
            logging.warning(f"Не удалось получить funding rate для {symbol}: {e}")

    if not upcoming_rates:
        logging.info("Нет будущих funding rate")
        return []

    # Первичная сортировка по времени
    upcoming_rates.sort(key=lambda x: x['fundingTime'])

    # Группировка по времени и сортировка внутри группы по модулю
    grouped = []
    for ts, group in groupby(upcoming_rates, key=lambda x: x['fundingTime']):
        group_list = list(group)
        group_list.sort(key=lambda x: abs(float(x['fundingRate'])), reverse=True)
        grouped.extend(group_list)

    # Вывод топ-N
    print(f"Топ-{top_n} ближайших по времени и модулю funding rate:")
    for i, item in enumerate(grouped[:top_n], start=1):
        print(f"{i}. {item['symbol']} | rate={float(item['fundingRate']):.6f} | time={item['readableTime']}")

    return grouped


if __name__ == "__main__":
    get_upcoming_usdt_funding(top_n=10)
