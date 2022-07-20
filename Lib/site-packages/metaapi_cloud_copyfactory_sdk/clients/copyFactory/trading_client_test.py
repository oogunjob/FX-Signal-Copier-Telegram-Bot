from .trading_client import TradingClient
import pytest
from ...models import date
from mock import MagicMock, AsyncMock
copy_factory_api_url = 'https://copyfactory-application-history-master-v1.agiliumtrade.agiliumtrade.ai'
domain_client = MagicMock()
trading_client = TradingClient(domain_client)
token = 'header.payload.sign'


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    domain_client = MagicMock()
    domain_client.request_copyfactory = AsyncMock()
    domain_client.token = token
    global trading_client
    trading_client = TradingClient(domain_client)


class TestTradingClient:
    @pytest.mark.asyncio
    async def test_resynchronize_copyfactory_account(self):
        """Should resynchronize CopyFactory account."""
        await trading_client.resynchronize('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', ['ABCD'], ['0123456'])
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6/resynchronize',
            'method': 'POST',
            'headers': {
                'auth-token': token
            },
            'params': {
                'strategyId': ['ABCD'],
                'positionId': ['0123456']
            }
        })

    @pytest.mark.asyncio
    async def test_not_resynchronize_account_with_account_token(self):
        """Should not resynchronize CopyFactory subscriber with account token."""
        domain_client.token = 'token'
        trading_client = TradingClient(domain_client)
        try:
            await trading_client.resynchronize('e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
                                               ['ABCD'], ['0123456'])
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke resynchronize method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_stopouts(self):
        """Should retrieve stopouts."""
        expected = [{
            'strategyId': 'accountId',
            'reason': 'monthly-balance',
            'stoppedAt': '2020-08-08T07:57:30.328Z',
            'strategy': {
                'id': 'ABCD',
                'name': 'Strategy'
            },
            'reasonDescription': 'total strategy equity drawdown exceeded limit',
            'sequenceNumber': 2
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        stopouts = await trading_client.get_stopouts('e8867baa-5ec2-45ae-9930-4d5cea18d0d6')
        assert stopouts == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6/stopouts',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_retrieve_stopouts_with_account_token(self):
        """Should not retrieve stopouts from API with account token."""
        domain_client.token = 'token'
        trading_client = TradingClient(domain_client)
        try:
            await trading_client.get_stopouts('e8867baa-5ec2-45ae-9930-4d5cea18d0d6')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_stopouts method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_reset_stopouts(self):
        """Should reset stopouts."""
        await trading_client.reset_stopouts('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', 'ABCD', 'daily-equity')
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/subscribers/' +
            'e8867baa-5ec2-45ae-9930-4d5cea18d0d6/subscription-strategies/ABCD/stopouts/daily-equity/reset',
            'method': 'POST',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_reset_stopouts_with_account_token(self):
        """Should not reset stopouts with account token."""
        domain_client.token = 'token'
        trading_client = TradingClient(domain_client)
        try:
            await trading_client.reset_stopouts('e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
                                                'ABCD', 'daily-equity')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke reset_stopouts method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_copy_trading_log(self):
        """Should retrieve copy trading user log."""
        expected = [{
          'time': '2020-08-08T07:57:30.328Z',
          'level': 'INFO',
          'message': 'message'
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        records = await trading_client.get_user_log('e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
                                                    date('2020-08-01T00:00:00.000Z'),
                                                    date('2020-08-10T00:00:00.000Z'), 10, 100)
        assert records == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6/user-log',
            'method': 'GET',
            'params': {
                'startTime': '2020-08-01T00:00:00.000Z',
                'endTime': '2020-08-10T00:00:00.000Z',
                'offset': 10,
                'limit': 100
            },
            'headers': {
                'auth-token': token
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_copy_trading_log_with_account_token(self):
        """Should not retrieve copy trading user log from API with account token."""
        domain_client.token = 'token'
        trading_client = TradingClient(domain_client)
        try:
            await trading_client.get_user_log('e8867baa-5ec2-45ae-9930-4d5cea18d0d6')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_user_log method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_copy_trading_strategy_log(self):
        """Should retrieve copy trading strategy log."""
        expected = [{
            'time': '2020-08-08T07:57:30.328Z',
            'level': 'INFO',
            'message': 'message'
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        records = await trading_client.get_strategy_log('ABCD', date('2020-08-01T00:00:00.000Z'),
                                                        date('2020-08-10T00:00:00.000Z'), 10, 100)
        assert records == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/strategies/ABCD/user-log',
            'method': 'GET',
            'params': {
                'startTime': '2020-08-01T00:00:00.000Z',
                'endTime': '2020-08-10T00:00:00.000Z',
                'offset': 10,
                'limit': 100
            },
            'headers': {
                'auth-token': token
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_copy_trading_strategy_log_with_account_token(self):
        """Should not retrieve copy trading strategy log from API with account token."""
        domain_client.token = 'token'
        trading_client = TradingClient(domain_client)
        try:
            await trading_client.get_strategy_log('ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_strategy_log method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_get_account(self):
        """Should get account."""
        domain_client.get_account_info = AsyncMock(return_value={'id': 'accountId', 'regions': ['vint-hill']})

        async def get_signal_client_host(regions):
            return {
                'host': 'https://copyfactory-api-v1',
                'regions': regions,
                'domain': 'agiliumtrade.ai'
            }

        domain_client.get_signal_client_host = AsyncMock(side_effect=get_signal_client_host)
        client = await trading_client.get_signal_client('accountId')
        assert client._accountId == 'accountId'
        assert client._host['regions'] == ['vint-hill']

    @pytest.mark.asyncio
    async def test_add_stopout_listener(self):
        """Should add stopout listener."""
        call_stub = MagicMock()
        trading_client._stopoutListenerManager.add_stopout_listener = call_stub
        listener = MagicMock()
        trading_client.add_stopout_listener(listener, 'accountId', 'ABCD', 1)
        call_stub.assert_called_with(listener, 'accountId', 'ABCD', 1)

    @pytest.mark.asyncio
    async def test_remove_stopout_listener(self):
        """Should remove stopout listener."""
        call_stub = MagicMock()
        trading_client._stopoutListenerManager.remove_stopout_listener = call_stub
        trading_client.remove_stopout_listener('id')
        call_stub.assert_called_with('id')
