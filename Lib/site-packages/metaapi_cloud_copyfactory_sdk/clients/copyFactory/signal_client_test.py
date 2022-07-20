from .signal_client import SignalClient
import pytest
from ...models import date
from mock import MagicMock, AsyncMock
domain_client = MagicMock()
token = 'header.payload.sign'
host = {
    'host': 'https://copyfactory-api-v1',
    'region': 'vint-hill',
    'domain': 'agiliumtrade.ai'
}
signal_client = SignalClient('accountId', host, domain_client)


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    domain_client = MagicMock()
    domain_client.token = token
    domain_client.request_signal = AsyncMock()
    global signal_client
    signal_client = SignalClient('accountId', host, domain_client)


class TestTradingClient:
    @pytest.mark.asyncio
    async def test_generate_signal_id(self):
        """Should generate signal id."""
        assert len(signal_client.generate_signal_id()) == 8

    @pytest.mark.asyncio
    async def test_update_external_signal(self):
        """Should update external signal."""
        signal = {
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'time': date('2020-08-24T00:00:00.000Z'),
            'updateTime': date('2020-08-24T00:00:00.000Z'),
            'volume': 1
        }
        expected_signal = {
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'time': '2020-08-24T00:00:00.000Z',
            'updateTime': '2020-08-24T00:00:00.000Z',
            'volume': 1
        }

        await signal_client.update_external_signal('ABCD', '0123456', signal)
        domain_client.request_signal.assert_called_with({
            'url': '/users/current/strategies/ABCD/external-signals/0123456',
            'method': 'PUT',
            'headers': {
                'auth-token': token
            },
            'body': expected_signal
        }, host, 'accountId')

    @pytest.mark.asyncio
    async def test_remove_external_signal(self):
        """Should remove external signal."""
        signal = {'time': '2020-08-24T00:00:00.000Z'}
        await signal_client.remove_external_signal('ABCD', '0123456', signal)
        domain_client.request_signal.assert_called_with({
              'url': '/users/current/strategies/ABCD/external-signals/0123456/remove',
              'method': 'POST',
              'headers': {
                'auth-token': token
              },
              'body': signal
        }, host, 'accountId')

    @pytest.mark.asyncio
    async def test_retrieve_signals(self):
        """Should retrieve signals."""
        expected = [{
            'symbol': 'EURUSD',
            'type': 'POSITION_TYPE_BUY',
            'time': '2020-08-24T00:00:00.000Z',
            'closeAfter': '2020-08-24T00:00:00.000Z',
            'volume': 1
        }]

        domain_client.request_signal = AsyncMock(return_value=expected)
        stopouts = await signal_client.get_trading_signals()
        assert stopouts == expected
        domain_client.request_signal.assert_called_with({
            'url': '/users/current/subscribers/accountId/signals',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        }, host, 'accountId')
