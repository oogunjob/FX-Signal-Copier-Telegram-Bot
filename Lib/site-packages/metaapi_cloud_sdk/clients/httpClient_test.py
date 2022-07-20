from .httpClient import HttpClient
import re
import pytest
import respx
from datetime import datetime
import json
from httpx import Response
from freezegun import freeze_time
from ..metaApi.models import format_date
httpClient: HttpClient = None
test_url = 'http://example.com'
opts = {}


@pytest.fixture(autouse=True)
async def run_around_tests():
    global httpClient
    httpClient = HttpClient()
    global opts
    opts = {'url': test_url}
    yield


class TestHttpClient:
    @pytest.mark.asyncio
    async def test_load(self):
        """Should load HTML page from example.com"""
        response = await httpClient.request(opts)
        text = response.text
        assert re.search('doctype html', text)

    @pytest.mark.asyncio
    async def test_not_found(self):
        """Should return NotFound exception if server returns 404"""
        opts = {
            'url': f'{test_url}/not-found'
        }
        try:
            await httpClient.request(opts)
            raise Exception('NotFoundException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'NotFoundException'

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Should return ConnectTimeout exception if request is timed out"""
        httpClient = HttpClient(0.001, {'retries': 2, 'minDelayInSeconds': 0.05, 'maxDelayInSeconds': 0.2})
        try:
            await httpClient.request(opts)
            raise Exception('ConnectTimeout is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ConnectTimeout'

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_api_exception(self):
        """Should retry request on fail with ApiException exception."""
        respx.get(test_url).mock(side_effect=[Response(502), Response(502),
                                              Response(200, content=json.dumps('response'))])
        response = await httpClient.request(opts)
        assert response == 'response'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_internal_exception(self):
        """Should retry request on fail with InternalException exception."""
        respx.get(test_url).mock(side_effect=[Response(500), Response(500),
                                              Response(200, content=json.dumps('response'))])
        response = await httpClient.request(opts)
        assert response == 'response'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_on_retry_limit_exceeded(self):
        """Should return error if retry limit exceeded."""
        respx.get(test_url).mock(side_effect=Response(502))
        httpClient = HttpClient(60, {'retries': 2})
        try:
            await httpClient.request(opts)
            raise Exception('ApiException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ApiException'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_not_retry_if_exception_not_internal_exception_or_api_exception(self):
        """Should not retry if exception is neither InternalException nor ApiException."""
        error = {
            'id': 1,
            'error': 'error',
            'message': 'test',
            'details': [{'parameter': 'password', 'value': 'wrong', 'message': 'Invalid value'}]
        }
        respx.get(test_url).mock(side_effect=[Response(400, json=error), Response(400, json=error), Response(204)])
        try:
            await httpClient.request(opts)
            raise Exception('ValidationException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'ValidationException'
            assert err.__str__() == 'test, check error.details for more information'
            assert err.details == error['details']
        assert respx.get(test_url).call_count == 1

    def get_too_many_requests_error(self, sec):
        date = datetime.now().timestamp()
        date += sec
        recommended_retry_time = format_date(datetime.fromtimestamp(date))
        return Response(429, content=json.dumps({"metadata": {"recommendedRetryTime": recommended_retry_time}}))

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_after_wait_on_too_many_requests_error(self):
        """Should retry request after waiting on fail with TooManyRequestsException error."""
        respx.get(test_url).mock(side_effect=[self.get_too_many_requests_error(2),
                                              self.get_too_many_requests_error(3),
                                              Response(200, content=json.dumps('response'))])
        response = await httpClient.request(opts)
        assert response == 'response'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_recommended_time_too_long(self):
        """Should return error if recommended retry time is too long."""
        respx.get(test_url).mock(side_effect=[self.get_too_many_requests_error(2),
                                              self.get_too_many_requests_error(300),
                                              Response(200, content=json.dumps('response'))])
        try:
            await httpClient.request(opts)
            raise Exception('TooManyRequestsException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TooManyRequestsException'
        assert respx.get(test_url).call_count == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_not_count_retrying_too_many_requests_exception(self):
        """Should not count retrying TooManyRequestsException error."""
        respx.get(test_url).mock(side_effect=[self.get_too_many_requests_error(2), Response(502),
                                              Response(200, content=json.dumps('response'))])
        httpClient = HttpClient(60, {'retries': 1})
        response = await httpClient.request(opts)
        assert response == 'response'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_wait_for_retry_after_header(self):
        """Should wait for the retry-after header time before retrying."""
        httpClient = HttpClient()
        respx.get(test_url).mock(side_effect=[
            Response(202, headers={'retry-after': '3'}),
            Response(202, headers={'retry-after': '3'}),
            Response(200, content=json.dumps('response'))])
        response = await httpClient.request(opts)
        assert response == 'response'
        assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_wait_for_retry_after_header_if_http_time(self):
        """Should wait for the retry-after header time before retrying if header is in http time."""
        with freeze_time('2020-10-05 07:00:00.000', tick=True):
            httpClient = HttpClient()
            respx.get(test_url).mock(side_effect=[
                Response(202, headers={'retry-after': 'Mon, 05 Oct 2020 07:00:01 GMT'}),
                Response(202, headers={'retry-after': 'Mon, 05 Oct 2020 07:00:02 GMT'}),
                Response(200, content=json.dumps('response'))])
            response = await httpClient.request(opts)
            assert response == 'response'
            assert respx.get(test_url).call_count == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_retry_after_time_too_long(self):
        """Should return TimeoutException error if retry-after header time is too long."""
        httpClient = HttpClient(60, {'maxDelayInSeconds': 3})
        respx.get(test_url).mock(side_effect=[
            Response(202, headers={'retry-after': '30'}),
            Response(202, headers={'retry-after': '30'}),
            Response(200, content=json.dumps('response'))])
        try:
            await httpClient.request(opts)
            raise Exception('TimeoutException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            assert err.args[0] == 'Timed out waiting for the response'
        assert respx.get(test_url).call_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_return_error_if_timed_out_to_retry(self):
        """Should return TimeoutException error if timed out to retry."""
        respx.get(test_url).mock(side_effect=Response(202, headers={'retry-after': '1'}))
        httpClient = HttpClient(60, {'maxDelayInSeconds': 2, 'retries': 3})
        try:
            await httpClient.request(opts)
            raise Exception('TimeoutException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            assert err.args[0] == 'Timed out waiting for the response'
        assert respx.get(test_url).call_count == 6
