from .latencyMonitor import LatencyMonitor
import pytest
from .models import date
monitor = LatencyMonitor()


@pytest.fixture(scope="module", autouse=True)
def run_around_tests():
    global monitor
    monitor = LatencyMonitor()
    yield


class TestLatencyMonitor:
    @pytest.mark.asyncio
    async def test_process_trade_latencies(self):
        """Should process trade latencies."""
        await monitor.on_trade('accountId', {
            'clientProcessingStarted': date('2020-12-07T13:22:48.000Z'),
            'serverProcessingStarted': date('2020-12-07T13:22:49.000Z'),
            'tradeStarted': date('2020-12-07T13:22:51.000Z'),
            'tradeExecuted': date('2020-12-07T13:22:54.000Z')
        })
        assert monitor.trade_latencies == {
            'clientLatency': {
                '1h': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1d': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1w': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                }
            },
            'serverLatency': {
                '1h': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1d': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1w': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                }
            },
            'brokerLatency': {
                '1h': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1d': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1w': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                }
            }
        }

    @pytest.mark.asyncio
    async def test_process_update_latencies(self):
        """Should process update latencies."""
        await monitor.on_update('accountId', {
            'eventGenerated': date('2020-12-07T13:22:48.000Z'),
            'serverProcessingStarted': date('2020-12-07T13:22:49.000Z'),
            'serverProcessingFinished': date('2020-12-07T13:22:51.000Z'),
            'clientProcessingFinished': date('2020-12-07T13:22:54.000Z')
        })
        assert monitor.update_latencies == {
            'brokerLatency': {
                '1h': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1d': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1w': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                }
            },
            'serverLatency': {
                '1h': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1d': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1w': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                }
            },
            'clientLatency': {
                '1h': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1d': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1w': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                }
            }
        }

    @pytest.mark.asyncio
    async def test_process_price_latencies(self):
        """Should process price streaming latencies."""
        await monitor.on_symbol_price('accountId', 'EURUSD', {
            'eventGenerated': date('2020-12-07T13:22:48.000Z'),
            'serverProcessingStarted': date('2020-12-07T13:22:49.000Z'),
            'serverProcessingFinished': date('2020-12-07T13:22:51.000Z'),
            'clientProcessingFinished': date('2020-12-07T13:22:54.000Z')
        })
        assert monitor.price_latencies == {
            'brokerLatency': {
                '1h': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1d': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                },
                '1w': {
                    'p50': 1000,
                    'p75': 1000,
                    'p90': 1000,
                    'p95': 1000,
                    'p98': 1000,
                    'avg': 1000,
                    'count': 1,
                    'min': 1000,
                    'max': 1000
                }
            },
            'serverLatency': {
                '1h': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1d': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                },
                '1w': {
                    'p50': 2000,
                    'p75': 2000,
                    'p90': 2000,
                    'p95': 2000,
                    'p98': 2000,
                    'avg': 2000,
                    'count': 1,
                    'min': 2000,
                    'max': 2000
                }
            },
            'clientLatency': {
                '1h': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1d': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                },
                '1w': {
                    'p50': 3000,
                    'p75': 3000,
                    'p90': 3000,
                    'p95': 3000,
                    'p98': 3000,
                    'avg': 3000,
                    'count': 1,
                    'min': 3000,
                    'max': 3000
                }
            }
        }

    @pytest.mark.asyncio
    async def test_process_request_latencies(self):
        """Should process request latencies."""
        await monitor.on_response('accountId', 'getSymbolPrice', {
            'clientProcessingStarted': date('2020-12-07T13:22:48.000Z'),
            'serverProcessingStarted': date('2020-12-07T13:22:49.000Z'),
            'serverProcessingFinished': date('2020-12-07T13:22:51.000Z'),
            'clientProcessingFinished': date('2020-12-07T13:22:51.000Z')
        })
        assert monitor.request_latencies == {
            'getSymbolPrice': {
                'clientLatency': {
                    '1h': {
                        'p50': 1000,
                        'p75': 1000,
                        'p90': 1000,
                        'p95': 1000,
                        'p98': 1000,
                        'avg': 1000,
                        'count': 1,
                        'min': 1000,
                        'max': 1000
                    },
                    '1d': {
                        'p50': 1000,
                        'p75': 1000,
                        'p90': 1000,
                        'p95': 1000,
                        'p98': 1000,
                        'avg': 1000,
                        'count': 1,
                        'min': 1000,
                        'max': 1000
                    },
                    '1w': {
                        'p50': 1000,
                        'p75': 1000,
                        'p90': 1000,
                        'p95': 1000,
                        'p98': 1000,
                        'avg': 1000,
                        'count': 1,
                        'min': 1000,
                        'max': 1000
                    }
                },
                'serverLatency': {
                    '1h': {
                        'p50': 2000,
                        'p75': 2000,
                        'p90': 2000,
                        'p95': 2000,
                        'p98': 2000,
                        'avg': 2000,
                        'count': 1,
                        'min': 2000,
                        'max': 2000
                    },
                    '1d': {
                        'p50': 2000,
                        'p75': 2000,
                        'p90': 2000,
                        'p95': 2000,
                        'p98': 2000,
                        'avg': 2000,
                        'count': 1,
                        'min': 2000,
                        'max': 2000
                    },
                    '1w': {
                        'p50': 2000,
                        'p75': 2000,
                        'p90': 2000,
                        'p95': 2000,
                        'p98': 2000,
                        'avg': 2000,
                        'count': 1,
                        'min': 2000,
                        'max': 2000
                    }
                }
            }
        }
