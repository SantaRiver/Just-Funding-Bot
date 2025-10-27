"""Инициализация модуля services."""
from services.aggregator import FundingRateAggregator
from services.formatter import MessageFormatter

__all__ = [
    'FundingRateAggregator',
    'MessageFormatter',
]
