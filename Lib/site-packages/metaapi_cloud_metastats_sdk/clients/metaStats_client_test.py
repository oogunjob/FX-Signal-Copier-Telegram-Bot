import pytest
import respx
from httpx import Response
from mock import MagicMock, AsyncMock
from .httpClient import HttpClient
from .metaStats_client import MetaStatsClient

token = 'header.payload.sign'
expected = {
    'trades': 10,
    'equity': 10102.5,
    'balance': 10105,
    'profit': 104,
    'deposits': 10001
}
account_id = '1234567'
host = 'agiliumtrade.ai'
domain_client = MagicMock()
metastats_client = MetaStatsClient(domain_client)
domain_call_mock = MagicMock()
domain_client.request_metastats = domain_call_mock


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_call_mock
    domain_call_mock = AsyncMock(return_value={'metrics': expected})
    global domain_client
    domain_client = MagicMock()
    domain_client.token = token
    domain_client.request_metastats = domain_call_mock
    global metastats_client
    metastats_client = MetaStatsClient(domain_client)
    yield


class TestGetMetrics:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_metrics(self):
        """Should retrieve account metrics from API."""
        metrics = await metastats_client.get_metrics(account_id)
        assert metrics == expected
        assert domain_call_mock.call_args[0][0](host, account_id) == {
            'url': 'agiliumtrade.ai/users/current/accounts/1234567/metrics',
            'method': 'GET',
            'headers': {'auth-token': token},
            'params': {'includeOpenPositions': False}
        }
        assert domain_call_mock.call_args[0][1] == '1234567'

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_metrics_with_open_positions(self):
        """Should retrieve account metrics with included open positions from API."""
        expected['inclusive'] = False
        metrics = await metastats_client.get_metrics(account_id, True)
        assert metrics == expected
        assert domain_call_mock.call_args[0][0](host, account_id) == {
            'url': 'agiliumtrade.ai/users/current/accounts/1234567/metrics',
            'method': 'GET',
            'headers': {'auth-token': token},
            'params': {'includeOpenPositions': True}
        }
        assert domain_call_mock.call_args[0][1] == '1234567'


start_time = '2020-01-01 00:00:00.000'
end_time = '2021-01-01 00:00:00.000'


class TestGetTrades:

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_account_trades(self):
        """Should retrieve account trades from API."""
        expected = [{'_id': '1'}]
        domain_call_mock = AsyncMock(return_value={'trades': expected})
        domain_client.request_metastats = domain_call_mock
        trades = await metastats_client.get_account_trades(account_id, start_time, end_time)
        assert trades == expected
        assert domain_call_mock.call_args[0][0](host, account_id) == {
            'url': f'agiliumtrade.ai/users/current/accounts/1234567/historical-trades/{start_time}/{end_time}',
            'method': 'GET',
            'headers': {'auth-token': token},
            'params': {'updateHistory': True, 'limit': 1000, 'offset': 0}
        }
        assert domain_call_mock.call_args[0][1] == '1234567'


class TestGetOpenTrades:

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_account_open_trades(self):
        """Should retrieve account open trades from API."""
        expected = [{'_id': '1'}]
        domain_call_mock = AsyncMock(return_value={'openTrades': expected})
        domain_client.request_metastats = domain_call_mock
        open_trades = await metastats_client.get_account_open_trades(account_id)
        assert open_trades == expected
        assert domain_call_mock.call_args[0][0](host, account_id) == {
            'url': 'agiliumtrade.ai/users/current/accounts/1234567/open-trades',
            'method': 'GET',
            'headers': {'auth-token': token}
        }
        assert domain_call_mock.call_args[0][1] == '1234567'
