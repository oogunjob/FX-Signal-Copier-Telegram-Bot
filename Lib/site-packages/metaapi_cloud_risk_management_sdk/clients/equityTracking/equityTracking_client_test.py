from .equityTracking_client import EquityTrackingClient
from .drawdownListener import DrawdownListener
import pytest
from mock import MagicMock, AsyncMock
domain_client = MagicMock()
equity_tracking_client = EquityTrackingClient(domain_client)
token = 'header.payload.sign'


class Listener(DrawdownListener):
    async def on_drawdown(self, drawdown_event):
        pass


listener: DrawdownListener = None


@pytest.fixture(autouse=True)
async def run_around_tests():
    global domain_client
    domain_client = MagicMock()
    domain_client.request_api = AsyncMock()
    domain_client.token = token
    global equity_tracking_client
    equity_tracking_client = EquityTrackingClient(domain_client)
    global listener
    listener = Listener()


class TestEquityTrackingClient:
    @pytest.mark.asyncio
    async def test_create_drawdown_tracker(self):
        """Should create drawdown tracker."""
        expected = {'id': 'trackerId'}
        tracker = {'name': 'trackerName'}
        domain_client.request_api = AsyncMock(return_value=expected)
        actual = await equity_tracking_client.create_drawdown_tracker('accountId', tracker)
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers',
            'method': 'POST',
            'body': tracker
        })

    @pytest.mark.asyncio
    async def test_retrieve_drawdown_trackers(self):
        """Should retrieve drawdown trackers."""
        expected = [{'name': 'trackerName'}]
        domain_client.request_api = AsyncMock(return_value=expected)
        actual = await equity_tracking_client.get_drawdown_trackers('accountId')
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers',
            'method': 'GET'
        })

    @pytest.mark.asyncio
    async def test_retrieve_drawdown_tracker_by_name(self):
        """Should retrieve drawdown tracker by name."""
        expected = {'name': 'trackerName'}
        domain_client.request_api = AsyncMock(return_value=expected)
        actual = await equity_tracking_client.get_drawdown_tracker_by_name('accountId', 'name')
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers/name/name',
            'method': 'GET'
        })

    @pytest.mark.asyncio
    async def test_update_drawdown_tracker(self):
        """Should update drawdown tracker."""
        update = {'name': 'newTrackerName'}
        await equity_tracking_client.update_drawdown_tracker('accountId', 'trackerId', update)
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers/trackerId',
            'method': 'PUT',
            'body': update
        })

    @pytest.mark.asyncio
    async def test_delete_drawdown_tracker(self):
        """Should delete drawdown tracker."""
        await equity_tracking_client.delete_drawdown_tracker('accountId', 'trackerId')
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers/trackerId',
            'method': 'DELETE'
        })

    @pytest.mark.asyncio
    async def test_retrieve_drawdown_events(self):
        """Should retrieve drawdown events."""
        expected = [{
            'sequenceNumber': 1,
            'accountId': 'accountId',
            'trackerId': 'trackerId',
            'period': 'day',
            'startBrokerTime': '2022-04-08 00:00:00.000',
            'endBrokerTime': '2022-04-08 23:59:59.999',
            'brokerTime': '2022-04-08 09:36:00.000',
            'absoluteDrawdown': 250,
            'relativeDrawdown': 0.25
        }]
        domain_client.request_api = AsyncMock(return_value=expected)

        actual = await equity_tracking_client.get_drawdown_events(
            '2022-04-08 09:36:00.000', '2022-04-08 10:36:00.000', 'accountId', 'trackerId', 100)
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/drawdown-events/by-broker-time',
            'params': {
                'startBrokerTime': '2022-04-08 09:36:00.000',
                'endBrokerTime': '2022-04-08 10:36:00.000',
                'accountId': 'accountId',
                'trackerId': 'trackerId',
                'limit': 100
            },
            'method': 'GET'
        })

    @pytest.mark.asyncio
    async def test_retrieve_drawdown_statistics(self):
        """Should retrieve drawdown statistics."""
        expected = [{
            'period': 'day',
            'startBrokerTime': '2022-04-08 00:00:00.000',
            'endBrokerTime': '2022-04-08 23:59:59.999',
            'initialBalance': 1000,
            'maxDrawdownTime': '2022-04-08 09:36:00.000',
            'maxAbsoluteDrawdown': 250,
            'maxRelativeDrawdown': 0.25,
            'thresholdExceeded': True
        }]
        domain_client.request_api = AsyncMock(return_value=expected)

        actual = await equity_tracking_client.get_drawdown_statistics('accountId', 'trackerId',
                                                                      '2022-04-08 09:36:00.000', 100)
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/drawdown-trackers/trackerId/statistics',
            'params': {'startTime': '2022-04-08 09:36:00.000', 'limit': 100},
            'method': 'GET'
        })

    @pytest.mark.asyncio
    async def test_retrieve_equity_chart(self):
        """Should retrieve equity chart."""
        expected = [{
            'startBrokerTime': '2022-04-08 00:00:00.000',
            'endBrokerTime': '2022-04-08 23:59:59.999',
            'averageBalance': 1050,
            'minBalance': 100,
            'maxBalance': 2000,
            'averageEquity': 1075,
            'minEquity': 50,
            'maxEquity': 2100
        }]
        domain_client.request_api = AsyncMock(return_value=expected)

        actual = await equity_tracking_client.get_equity_chart('accountId', '2022-04-08 09:36:00.000',
                                                               '2022-04-08 10:36:00.000')
        assert actual == expected
        domain_client.request_api.assert_called_with({
            'url': '/users/current/accounts/accountId/equity-chart',
            'params': {
                'startTime': '2022-04-08 09:36:00.000',
                'endTime': '2022-04-08 10:36:00.000'
            },
            'method': 'GET'
        })

    @pytest.mark.asyncio
    async def test_add_drawdown_listener(self):
        """Should add drawdown listener."""
        call_stub = MagicMock()
        equity_tracking_client._drawdownListenerManager.add_drawdown_listener = call_stub
        equity_tracking_client.add_drawdown_listener(listener, 'accountId', 'trackerId', 1)
        call_stub.assert_called_with(listener, 'accountId', 'trackerId', 1)

    @pytest.mark.asyncio
    async def test_remove_drawdown_listener(self):
        """Should remove drawdown listener."""
        call_stub = MagicMock()
        equity_tracking_client._drawdownListenerManager.remove_drawdown_listener = call_stub
        equity_tracking_client.remove_drawdown_listener('id')
        call_stub.assert_called_with('id')
