from .history_client import HistoryClient
from ...models import date, format_date
from datetime import datetime
import pytest
import respx
from mock import MagicMock, AsyncMock
domain_client = MagicMock()
history_client = HistoryClient(domain_client)
token = 'header.payload.sign'


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    global history_client
    domain_client = MagicMock()
    domain_client.request_copyfactory = AsyncMock()
    domain_client.token = token
    history_client = HistoryClient(domain_client)


class TestHistoryClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_transactions_for_provided_strategies_from_api(self):
        """Should retrieve transactions performed on provided strategies from API."""
        expected = [{
            'id': '64664661:close',
            'type': 'DEAL_TYPE_SELL',
            'time': '2020-08-02T21:01:01.830Z',
            'subscriberId': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'symbol': 'EURJPY',
            'subscriber': {
                'id': 'subscriberId',
                'name': 'Subscriber'
            },
            'demo': False,
            'providerUser': {
                'id': 'providerId',
                'name': 'Provider'
            },
            'strategy': {
                'id': 'ABCD'
            },
            'improvement': 0,
            'providerCommission': 0,
            'platformCommission': 0,
            'quantity': -0.04,
            'lotPrice': 117566.08744776,
            'tickPrice': 124.526,
            'amount': -4702.643497910401,
            'commission': -0.14,
            'swap': -0.14,
            'profit': 0.49
        }]
        time_from = datetime.now()
        time_till = datetime.now()
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        accounts = await history_client.get_provided_transactions(
            time_from, time_till, ['ABCD'], ['e8867baa-5ec2-45ae-9930-4d5cea18d0d6'], 100, 200)
        expected[0]['time'] = date(expected[0]['time'])
        assert accounts == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/provided-transactions',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
            'params': {
                'from': format_date(time_from),
                'till': format_date(time_till),
                'strategyId': ['ABCD'],
                'subscriberId': ['e8867baa-5ec2-45ae-9930-4d5cea18d0d6'],
                'offset': 100,
                'limit': 200
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_transactions_for_provided_strategies_with_account_token(self):
        """Should not retrieve transactions on provided strategies from API with account token."""
        domain_client.token = 'token'
        history_client = HistoryClient(domain_client)
        try:
            await history_client.get_provided_transactions(datetime.now(), datetime.now())
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_provided_transactions method, because ' + \
                   'you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @respx.mock
    @pytest.mark.asyncio
    async def test_retrieve_transactions_for_subscribed_strategies_from_api(self):
        """Should retrieve transactions performed on strategies current user is subscribed to from API."""
        expected = [{
            'id': '64664661:close',
            'type': 'DEAL_TYPE_SELL',
            'time': '2020-08-02T21:01:01.830Z',
            'subscriberId': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'symbol': 'EURJPY',
            'subscriberUser': {
                'id': 'subscriberId',
                'name': 'Subscriber'
            },
            'demo': False,
            'providerUser': {
                'id': 'providerId',
                'name': 'Provider'
            },
            'strategy': {
                'id': 'ABCD'
            },
            'improvement': 0,
            'providerCommission': 0,
            'platformCommission': 0,
            'quantity': -0.04,
            'lotPrice': 117566.08744776,
            'tickPrice': 124.526,
            'amount': -4702.643497910401,
            'commission': -0.14,
            'swap': -0.14,
            'profit': 0.49
        }]
        time_from = datetime.now()
        time_till = datetime.now()
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        accounts = await history_client.get_subscription_transactions(
            time_from, time_till, ['ABCD'], ['e8867baa-5ec2-45ae-9930-4d5cea18d0d6'], 100, 200)
        expected[0]['time'] = date(expected[0]['time'])
        assert accounts == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/subscription-transactions',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
            'params': {
                'from': format_date(time_from),
                'till': format_date(time_till),
                'strategyId': ['ABCD'],
                'subscriberId': ['e8867baa-5ec2-45ae-9930-4d5cea18d0d6'],
                'offset': 100,
                'limit': 200
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_transactions_for_subscribed_strategies_with_account_token(self):
        """Should not retrieve transactions on strategies subscribed to from API with account token."""
        history_client = HistoryClient(domain_client)
        try:
            await history_client.get_subscription_transactions(datetime.now(), datetime.now())
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_subscription_transactions method, ' + \
                   'because you have connected with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'
