from .configuration_client import ConfigurationClient
from ...models import date, format_date
import pytest
import json
import respx
from copy import deepcopy
from httpx import Response
from mock import MagicMock, AsyncMock
domain_client = MagicMock()
copy_factory_client = ConfigurationClient(domain_client)
token = 'header.payload.sign'


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    global copy_factory_client
    domain_client = MagicMock()
    domain_client.token = token
    domain_client.request_copyfactory = AsyncMock()
    copy_factory_client = ConfigurationClient(domain_client)


class TestConfigurationClient:
    @pytest.mark.asyncio
    async def test_generate_account_id(self):
        """Should generate account id."""
        assert len(copy_factory_client.generate_account_id()) == 64

    @pytest.mark.asyncio
    async def test_generate_strategy_id(self):
        """Should retrieve CopyFactory accounts from API."""
        expected = {
            'id': 'ABCD'
        }
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        id = await copy_factory_client.generate_strategy_id()
        assert id == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/unused-strategy-id',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_generate_strategy_id_with_account_token(self):
        """Should not generate strategy id with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.generate_strategy_id()
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke generate_strategy_id method, because you have connected ' + \
                   'with account access token. Please use API access token from ' + \
                   'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_strategies_from_api(self):
        """Should retrieve strategies from API."""
        expected = [{
            '_id': 'ABCD',
            'platformCommissionRate': 0.01,
            'name': 'Test strategy',
            'accountId': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'maxTradeRisk': 0.1,
            'riskLimits': [{
                'type': 'monthly',
                'applyTo': 'balance',
                'maxRelativeRisk': 0.5,
                'closePositions': False,
                'startTime': '2020-08-24T00:00:01.000Z'
            }],
            'timeSettings': {
                'lifetimeInHours': 192,
                'openingIntervalInMinutes': 5
            }
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        strategies = await copy_factory_client.get_strategies(True, 100, 200)
        expected[0]['riskLimits'][0]['startTime'] = date(expected[0]['riskLimits'][0]['startTime'])
        assert strategies == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/strategies',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
            'params': {
                'includeRemoved': True,
                'limit': 100,
                'offset': 200
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_strategies_with_account_token(self):
        """Should not retrieve strategies with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_strategies()
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_strategies method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_strategy_from_api(self):
        """Should retrieve strategy from API."""
        expected = {
            '_id': 'ABCD',
            'platformCommissionRate': 0.01,
            'name': 'Test strategy',
            'accountId': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'maxTradeRisk': 0.1,
            'riskLimits': [{
                'type': 'monthly',
                'applyTo': 'balance',
                'maxRelativeRisk': 0.5,
                'closePositions': False,
                'startTime': '2020-08-24T00:00:01.000Z'
            }],
            'timeSettings': {
                'lifetimeInHours': 192,
                'openingIntervalInMinutes': 5
            }
        }
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        strategy = await copy_factory_client.get_strategy('ABCD')
        assert strategy == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/strategies/ABCD',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_retrieve_strategy_with_account_token(self):
        """Should not retrieve strategy with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_strategy('ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_strategy method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_update_strategy(self):
        """Should update strategy via API."""
        strategy = {
            'name': 'Test strategy',
            'description': 'Test description',
            'maxTradeRisk': 0.1,
            'riskLimits': [{
                'type': 'monthly',
                'applyTo': 'balance',
                'maxRelativeRisk': 0.5,
                'closePositions': False,
                'startTime': date('2020-08-24T00:00:01.000Z')
            }],
            'timeSettings': {
                'lifetimeInHours': 192,
                'openingIntervalInMinutes': 5
            }
        }
        json_copy = deepcopy(strategy)
        json_copy['riskLimits'][0]['startTime'] = format_date(json_copy['riskLimits'][0]['startTime'])
        await copy_factory_client.update_strategy('ABCD', strategy)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/strategies/ABCD',
            'method': 'PUT',
            'headers': {
                'auth-token': token
            },
            'body': json_copy
        })

    @pytest.mark.asyncio
    async def test_not_update_strategy_with_account_token(self):
        """Should not update strategy with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.update_strategy('ABCD', {})
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke update_strategy method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_remove_strategy(self):
        """Should remove strategy via API."""
        payload = {'mode': 'preserve', 'removeAfter': date('2020-08-24T00:00:01.000Z')}
        await copy_factory_client.remove_strategy('ABCD', payload)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/strategies/ABCD',
            'method': 'DELETE',
            'headers': {
                'auth-token': token
            },
            'body': payload
        })

    @pytest.mark.asyncio
    async def test_not_remove_strategy_with_account_token(self):
        """Should not remove strategy with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.remove_strategy('ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke remove_strategy method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_portfolio_strategies(self):
        """Should retrieve portfolio strategies from API."""
        expected = [{
            '_id': 'ABCD',
            'platformCommissionRate': 0.01,
            'name': 'Test strategy',
            'members': [{
                'strategyId': 'BCDE',
                'riskLimits': [{
                    'type': 'daily',
                    'startTime': '2020-08-24T00:00:00.000Z'
                }]
            }],
            'maxTradeRisk': 0.1,
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        strategies = await copy_factory_client.get_portfolio_strategies(True, 100, 200)
        expected[0]['members'][0]['riskLimits'][0]['startTime'] = \
            date(expected[0]['members'][0]['riskLimits'][0]['startTime'])
        assert strategies == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/portfolio-strategies',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
            'params': {
                'includeRemoved': True,
                'limit': 100,
                'offset': 200
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_portfolio_strategies_with_account_token(self):
        """Should not retrieve portfolio strategies from API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_portfolio_strategies()
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_portfolio_strategies method, because you have connected '\
                                    'with account access token. Please use API access token from '\
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_portfolio_strategy(self):
        """Should retrieve portfolio strategy from API."""
        expected = {
            '_id': 'ABCD',
            'platformCommissionRate': 0.01,
            'name': 'Test strategy',
            'members': [{
                'strategyId': 'BCDE',
                'riskLimits': [{
                    'type': 'daily',
                    'startTime': '2020-08-24T00:00:00.000Z'
                }]
            }],
            'maxTradeRisk': 0.1,
        }
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        strategies = await copy_factory_client.get_portfolio_strategy('ABCD')
        expected['members'][0]['riskLimits'][0]['startTime'] = \
            date(expected['members'][0]['riskLimits'][0]['startTime'])
        assert strategies == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/portfolio-strategies/ABCD',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_retrieve_portfolio_strategy_with_account_token(self):
        """Should not retrieve portfolio strategy from API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_portfolio_strategy('ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_portfolio_strategy method, because you have connected '\
                                    'with account access token. Please use API access token from '\
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_update_portfolio_strategy(self):
        """Should update portfolio strategy via API."""
        strategy = {
            'name': 'Test strategy',
            'members': [{
                'strategyId': 'BCDE'
            }],
            'maxTradeRisk': 0.1,
        }
        await copy_factory_client.update_portfolio_strategy('ABCD', strategy)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/portfolio-strategies/ABCD',
            'method': 'PUT',
            'headers': {
                'auth-token': token
            },
            'body': strategy
        })

    @pytest.mark.asyncio
    async def test_not_update_portfolio_strategy_with_account_token(self):
        """Should not update portfolio strategy via API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.update_portfolio_strategy('ABCD', {})
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke update_portfolio_strategy method, because you have connected ' \
                                    'with account access token. Please use API access token from ' \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_remove_portfolio_strategy(self):
        """Should remove portfolio strategy via API."""
        payload = {'mode': 'preserve', 'removeAfter': date('2020-08-24T00:00:01.000Z')}
        await copy_factory_client.remove_portfolio_strategy('ABCD', payload)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/portfolio-strategies/ABCD',
            'method': 'DELETE',
            'headers': {
                'auth-token': token
            },
            'body': payload,
        })

    @pytest.mark.asyncio
    async def test_not_remove_portfolio_strategy_with_account_token(self):
        """Should not remove portfolio strategy with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.remove_portfolio_strategy('ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke remove_portfolio_strategy method, because you have ' \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_remove_portfolio_strategy_member(self):
        """Should remove portfolio strategy member via API."""
        payload = {'mode': 'preserve', 'removeAfter': date('2020-08-24T00:00:01.000Z')}
        await copy_factory_client.remove_portfolio_strategy_member('ABCD', 'BCDE', payload)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/portfolio-strategies/ABCD/members/BCDE',
            'method': 'DELETE',
            'headers': {
                'auth-token': token
            },
            'body': payload,
        })

    @pytest.mark.asyncio
    async def test_not_remove_portfolio_strategy_member_with_account_token(self):
        """Should not remove portfolio strategy member with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.remove_portfolio_strategy_member('ABCD', 'BCDE')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke remove_portfolio_strategy_member method, because you have ' \
                                    'connected with account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_copyfactory_subscribers_from_api(self):
        """Should retrieve CopyFactory subscribers from API."""
        expected = [{
          '_id': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
          'name': 'Demo account',
          'reservedMarginFraction': 0.25,
          'subscriptions': [
            {
              'strategyId': 'ABCD',
              'multiplier': 1
            }
          ]
        }]
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        accounts = await copy_factory_client.get_subscribers(True, 100, 200)
        assert accounts == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/subscribers',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
            'params': {
                'includeRemoved': True,
                'limit': 100,
                'offset': 200
            },
        }, True)

    @pytest.mark.asyncio
    async def test_not_retrieve_copyfactory_subscribers_with_account_token(self):
        """Should not retrieve CopyFactory subscribers via API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_subscribers()
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_subscribers method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_retrieve_copyfactory_subscriber_from_api(self):
        """Should retrieve CopyFactory subscriber from API."""
        expected = {
            '_id': 'e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'name': 'Demo account',
            'reservedMarginFraction': 0.25,
            'subscriptions': [
                {
                    'strategyId': 'ABCD',
                    'multiplier': 1
                }
            ]
        }
        domain_client.request_copyfactory = AsyncMock(return_value=expected)
        accounts = await copy_factory_client.get_subscriber('e8867baa-5ec2-45ae-9930-4d5cea18d0d6')
        assert accounts == expected
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'method': 'GET',
            'headers': {
                'auth-token': token
            },
        })

    @pytest.mark.asyncio
    async def test_not_retrieve_copyfactory_subscriber_with_account_token(self):
        """Should not retrieve CopyFactory subscriber from API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.get_subscriber('test')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke get_subscriber method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_update_copyfactory_subscriber(self):
        """Should update CopyFactory subscriber via API."""
        subscriber = {
            'name': 'Demo account',
            'reservedMarginFraction': 0.25,
            'subscriptions': [
                {
                    'strategyId': 'ABCD',
                    'multiplier': 1
                }
            ]
        }
        await copy_factory_client.update_subscriber('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', subscriber)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'method': 'PUT',
            'headers': {
                'auth-token': token
            },
            'body': subscriber,
        })

    @pytest.mark.asyncio
    async def test_not_update_copyfactory_subscriber_with_account_token(self):
        """Should not update CopyFactory subscriber via API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.update_subscriber('id', {})
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke update_subscriber method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_remove_copyfactory_subscriber(self):
        """Should remove CopyFactory subscriber via API."""
        payload = {'mode': 'preserve', 'removeAfter': date('2020-08-24T00:00:01.000Z')}
        await copy_factory_client.remove_subscriber('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', payload)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6',
            'method': 'DELETE',
            'headers': {
                'auth-token': token
            },
            'body': payload,
        })

    @pytest.mark.asyncio
    async def test_not_remove_copyfactory_subscriber_with_account_token(self):
        """Should not remove CopyFactory subscriber via API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.remove_subscriber('id')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke remove_subscriber method, because you have connected with ' + \
                                    'account access token. Please use API access token from ' + \
                                    'https://app.metaapi.cloud/token page to invoke this method.'

    @pytest.mark.asyncio
    async def test_remove_copyfactory_subscription(self):
        """Should remove CopyFactory subscription via API."""
        payload = {'mode': 'preserve', 'removeAfter': date('2020-08-24T00:00:01.000Z')}
        await copy_factory_client.remove_subscription('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', 'ABCD', payload)
        domain_client.request_copyfactory.assert_called_with({
            'url': '/users/current/configuration/subscribers/e8867baa-5ec2-45ae-9930-4d5cea18d0d6/subscriptions/ABCD',
            'method': 'DELETE',
            'headers': {
                'auth-token': token
            },
            'body': payload,
        })

    @pytest.mark.asyncio
    async def test_not_remove_copyfactory_subscription_with_account_token(self):
        """Should not remove CopyFactory subscription via API with account token."""
        domain_client.token = 'token'
        copy_factory_client = ConfigurationClient(domain_client)
        try:
            await copy_factory_client.remove_subscription('e8867baa-5ec2-45ae-9930-4d5cea18d0d6', 'ABCD')
            pytest.fail()
        except Exception as err:
            assert err.__str__() == 'You can not invoke remove_subscription method, because you have connected ' \
                                    'with account access token. Please use API access token from ' \
                                    'https://app.metaapi.cloud/token page to invoke this method.'
