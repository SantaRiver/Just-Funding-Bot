"""Инициализация модуля exchanges."""
from exchanges.base import ExchangeAdapter
from exchanges.bybit_adapter import BybitAdapter
from exchanges.binance_adapter import BinanceAdapter
from exchanges.mexc_adapter import MexcAdapter
from exchanges.gateio_adapter import GateioAdapter
from exchanges.kucoin_adapter import KucoinAdapter
from exchanges.bitget_adapter import BitgetAdapter
from exchanges.bingx_adapter import BingxAdapter
from exchanges.bitmart_adapter import BitmartAdapter
from exchanges.okx_adapter import OkxAdapter

__all__ = [
    'ExchangeAdapter',
    'BybitAdapter',
    'BinanceAdapter',
    'MexcAdapter',
    'GateioAdapter',
    'KucoinAdapter',
    'BitgetAdapter',
    'BingxAdapter',
    'BitmartAdapter',
    'OkxAdapter',
]
