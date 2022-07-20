from ..httpClient import HttpClient
from .historicalMarketData_client import HistoricalMarketDataClient
from ...metaApi.models import date
import pytest
import respx
from httpx import Response
from freezegun import freeze_time
market_data_client_api_url = 'https://mt-market-data-client-api-v1.vint-hill.agiliumlabs.cloud'
http_client = HttpClient()
client = HistoricalMarketDataClient(http_client, 'header.payload.sign')
get_url_stub: respx.Route = None


@pytest.fixture(autouse=True)
async def run_around_tests():
    global http_client
    global client
    http_client = HttpClient()
    client = HistoricalMarketDataClient(http_client, 'header.payload.sign')
    global get_url_stub
    respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/regions')\
        .mock(return_value=Response(200, json=['vint-hill', 'us-west']))
    get_url_stub = respx.get('https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/'
                             'users/current/servers/mt-client-api')\
        .mock(return_value=Response(200, json={'domain': 'agiliumlabs.cloud'}))


class TestHistoricalMarketDataClient:

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_candles(self):
        """Should download historical candles from API."""
        expected = [{
            'symbol': 'AUDNZD',
            'timeframe': '15m',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'open': 1.03297,
            'high': 1.06309,
            'low': 1.02705,
            'close': 1.043,
            'tickVolume': 1435,
            'spread': 17,
            'volume': 345
        }]

        rsps = respx.get(f'{market_data_client_api_url}/users/current/accounts/accountId/historical-market-data/'
                         'symbols/AUDNZD/timeframes/15m/candles').mock(return_value=Response(200, json=expected))

        candles = await client.get_historical_candles('accountId', 'vint-hill', 'AUDNZD', '15m',
                                                      date('2020-04-07T03:45:00.000Z'), 1)
        expected[0]['time'] = date(expected[0]['time'])
        assert rsps.calls[0].request.url == f'{market_data_client_api_url}/users/current/accounts/accountId/' \
                                            'historical-market-data/symbols/AUDNZD/timeframes/15m/candles' \
                                            '?startTime=2020-04-07T03%3A45%3A00.000Z&limit=1'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert candles == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_candles_with_special_characters(self):
        """Should download historical candles from API for symbol with special characters."""
        expected = [{
            'symbol': 'GBPJPY#',
            'timeframe': '15m',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'open': 1.03297,
            'high': 1.06309,
            'low': 1.02705,
            'close': 1.043,
            'tickVolume': 1435,
            'spread': 17,
            'volume': 345
        }]

        rsps = respx.get().mock(return_value=Response(200, json=expected))
        candles = await client.get_historical_candles('accountId', 'vint-hill', 'GBPJPY#', '15m',
                                                      date('2020-04-07T03:45:00.000Z'), 1)
        expected[0]['time'] = date(expected[0]['time'])
        assert rsps.calls[0].request.url == f'{market_data_client_api_url}/users/current/accounts/accountId/' \
                                            'historical-market-data/symbols/GBPJPY%23/timeframes/15m/candles' \
                                            '?startTime=2020-04-07T03%3A45%3A00.000Z&limit=1'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert candles == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_ticks(self):
        """Should download historical ticks from API."""
        expected = [{
            'symbol': 'AUDNZD',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'bid': 1.05297,
            'ask': 1.05309,
            'last': 0.5298,
            'volume': 0.13,
            'side': 'buy'
        }]

        rsps = respx.get(f'{market_data_client_api_url}/users/current/accounts/accountId/historical-market-data/'
                         'symbols/AUDNZD/ticks').mock(return_value=Response(200, json=expected))
        ticks = await client.get_historical_ticks('accountId', 'vint-hill', 'AUDNZD',
                                                  date('2020-04-07T03:45:00.000Z'), 0, 1)
        expected[0]['time'] = date(expected[0]['time'])
        assert rsps.calls[0].request.url == f'{market_data_client_api_url}/users/current/accounts/accountId/' \
                                            'historical-market-data/symbols/AUDNZD/ticks' \
                                            '?startTime=2020-04-07T03%3A45%3A00.000Z&offset=0&limit=1'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert ticks == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_download_ticks_with_special_characters(self):
        """Should download historical ticks from API."""
        expected = [{
            'symbol': 'GBPJPY#',
            'time': '2020-04-07T03:45:00.000Z',
            'brokerTime': '2020-04-07 06:45:00.000',
            'bid': 1.05297,
            'ask': 1.05309,
            'last': 0.5298,
            'volume': 0.13,
            'side': 'buy'
        }]

        rsps = respx.get().mock(return_value=Response(200, json=expected))
        ticks = await client.get_historical_ticks('accountId', 'vint-hill', 'GBPJPY#',
                                                  date('2020-04-07T03:45:00.000Z'), 0, 1)
        expected[0]['time'] = date(expected[0]['time'])
        assert rsps.calls[0].request.url == f'{market_data_client_api_url}/users/current/accounts/accountId/' \
                                            'historical-market-data/symbols/GBPJPY%23/ticks' \
                                            '?startTime=2020-04-07T03%3A45%3A00.000Z&offset=0&limit=1'
        assert rsps.calls[0].request.method == 'GET'
        assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
        assert ticks == expected

    @respx.mock
    @pytest.mark.asyncio
    async def test_use_cached_url_on_repeated_request(self):
        """Should use cached url on repeated request."""
        with freeze_time() as frozen_datetime:
            expected = [{
                'symbol': 'AUDNZD',
                'timeframe': '15m',
                'time': '2020-04-07T03:45:00.000Z',
                'brokerTime': '2020-04-07 06:45:00.000',
                'open': 1.03297,
                'high': 1.06309,
                'low': 1.02705,
                'close': 1.043,
                'tickVolume': 1435,
                'spread': 17,
                'volume': 345
            }]

            rsps = respx.get(f'{market_data_client_api_url}/users/current/accounts/accountId/historical-market-data/'
                             'symbols/AUDNZD/timeframes/15m/candles').mock(return_value=Response(200, json=expected))

            await client.get_historical_candles('accountId', 'vint-hill', 'AUDNZD', '15m',
                                                date('2020-04-07T03:45:00.000Z'), 1)

            candles = await client.get_historical_candles('accountId', 'vint-hill', 'AUDNZD', '15m',
                                                          date('2020-04-07T03:45:00.000Z'), 1)
            expected[0]['time'] = date(expected[0]['time'])
            assert rsps.calls[0].request.url == f'{market_data_client_api_url}/users/current/accounts/accountId/' \
                                                'historical-market-data/symbols/AUDNZD/timeframes/15m/candles' \
                                                '?startTime=2020-04-07T03%3A45%3A00.000Z&limit=1'
            assert rsps.calls[0].request.method == 'GET'
            assert rsps.calls[0].request.headers['auth-token'] == 'header.payload.sign'
            assert candles == expected
            assert len(get_url_stub.calls) == 1
            frozen_datetime.tick(600)
            await client.get_historical_candles('accountId', 'vint-hill', 'AUDNZD', '15m',
                                                date('2020-04-07T03:45:00.000Z'), 1)
            assert len(get_url_stub.calls) == 2
