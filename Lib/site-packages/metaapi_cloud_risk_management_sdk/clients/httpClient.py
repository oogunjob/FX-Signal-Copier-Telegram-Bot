from .errorHandler import UnauthorizedException, ForbiddenException, ApiException, ConflictException, \
    ValidationException, InternalException, NotFoundException, TooManyRequestsException
from typing_extensions import TypedDict
from typing import Optional
from ..models import ExceptionMessage, date
from .timeoutException import TimeoutException
import json
import asyncio
import sys
import httpx
from datetime import datetime
from httpx import HTTPError, Response


if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class RequestOptions(TypedDict):
    """Options for HttpClient requests."""
    method: Optional[str]
    url: str
    headers: Optional[dict]
    params: Optional[dict]
    body: Optional[dict]
    files: Optional[dict]
    timeout: Optional[float]


class HttpClient:
    """HTTP client library based on requests module."""
    def __init__(self, timeout: float = 10, extended_timeout: float = 70, retry_opts=None):
        """Inits HttpClient class instance.

        Args:
            timeout: Request timeout in seconds.
            extended_timeout: Extended request timeout in seconds.
            retry_opts: Retry options.
        """
        if retry_opts is None:
            retry_opts = {}
        self._timeout = timeout
        self._extendedTimeout = extended_timeout
        self._retries = retry_opts['retries'] if 'retries' in retry_opts else 5
        self._minRetryDelayInSeconds = retry_opts['minDelayInSeconds'] if 'minDelayInSeconds' in retry_opts else 1
        self._maxRetryDelayInSeconds = retry_opts['maxDelayInSeconds'] if 'maxDelayInSeconds' in retry_opts else 30

    async def request(self, options: dict, is_extended_timeout: bool = False):
        """Performs a request. Response errors are returned as ApiError or subclasses.

        Args:
            options: Request options.
            is_extended_timeout: Whether to run the request with an extended timeout.

        Returns:
            Request result.
        """
        options['timeout'] = self._extendedTimeout if is_extended_timeout else self._timeout
        try:
            response = await self._make_request(options)
            response.raise_for_status()
            if response.content:
                try:
                    response = response.json()
                except Exception as err:
                    print('Error parsing json', err)
        except HTTPError as err:
            raise self._convert_error(err)
        return response

    async def request_with_failover(self, options: RequestOptions, retry_counter: int = 0, end_time: float = None) \
            -> Response:
        """Performs a request. Response errors are returned as ApiException or subclasses.

        Args:
            options: Request options.

        Returns:
            A request response.
        """
        options['timeout'] = self._timeout
        if not end_time:
            end_time = datetime.now().timestamp() + self._maxRetryDelayInSeconds * self._retries
        retry_after_seconds = 0
        try:
            response = await self._make_request(options)
            response.raise_for_status()
            if response.status_code == 202:
                retry_after_seconds = response.headers['retry-after']
                if isinstance(retry_after_seconds, str):
                    retry_after_seconds = float(retry_after_seconds)
            if response.content:
                try:
                    response = response.json()
                except Exception as err:
                    print('Error parsing json', err)
        except HTTPError as err:
            retry_counter = await self._handle_error(err, retry_counter, end_time)
            return await self.request_with_failover(options, retry_counter, end_time)
        if retry_after_seconds:
            await self._handle_retry(end_time, retry_after_seconds)
            response = await self.request_with_failover(options, retry_counter, end_time)
        return response

    async def _make_request(self, options: RequestOptions) -> Response:
        timeout = options['timeout'] if 'timeout' in options else self._timeout
        async with httpx.AsyncClient(timeout=timeout) as client:
            method = options['method'] if ('method' in options) else 'GET'
            url = options['url']
            params = options['params'] if 'params' in options else None
            files = options['files'] if 'files' in options else None
            headers = options['headers'] if 'headers' in options else None
            body = options['body'] if 'body' in options else None
            req = client.build_request(method, url, params=params, files=files, headers=headers, json=body)
            response = await client.send(req)
            return response

    async def _handle_retry(self, end_time: float, retry_after: float):
        if end_time > datetime.now().timestamp() + retry_after:
            await asyncio.sleep(retry_after)
        else:
            raise TimeoutException('Timed out waiting for the response')

    async def _handle_error(self, err, retry_counter: int, end_time: float):
        if err.__class__.__name__ == 'ConnectTimeout':
            error = err
        else:
            error = self._convert_error(err)
        if error.__class__.__name__ in ['ConflictException', 'InternalException', 'ApiException', 'ConnectTimeout'] \
                and retry_counter < self._retries:
            pause = min(pow(2, retry_counter) * self._minRetryDelayInSeconds, self._maxRetryDelayInSeconds)
            await asyncio.sleep(pause)
            return retry_counter + 1
        elif error.__class__.__name__ == 'TooManyRequestsException':
            retry_time = date(error.metadata['recommendedRetryTime']).timestamp()
            if retry_time < end_time:
                await asyncio.sleep(retry_time - datetime.now().timestamp())
                return retry_counter
        raise error

    def _convert_error(self, err: HTTPError):
        if err.__class__.__name__ == 'ConnectTimeout':
            return err
        try:
            response: ExceptionMessage or TypedDict = json.loads(err.response.text)
        except Exception:
            response = {}
        err_message = response['message'] if 'message' in response else (
            err.response.reason_phrase if hasattr(err, 'response') else None)
        status = None
        if hasattr(err, 'response'):
            status = err.response.status_code
        if status == 400:
            details = response['details'] if 'details' in response else []
            return ValidationException(err_message, details)
        elif status == 401:
            return UnauthorizedException(err_message)
        elif status == 403:
            return ForbiddenException(err_message)
        elif status == 404:
            return NotFoundException(err_message)
        elif status == 409:
            return ConflictException(err_message)
        elif status == 429:
            err_metadata = response['metadata'] if 'metadata' in response else {}
            return TooManyRequestsException(err_message, err_metadata)
        elif status == 500:
            return InternalException(err_message)
        else:
            return ApiException(err_message, status)
