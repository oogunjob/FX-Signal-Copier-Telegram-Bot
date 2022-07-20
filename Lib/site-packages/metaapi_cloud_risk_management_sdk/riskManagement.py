from .clients.httpClient import HttpClient
from .clients.domain_client import DomainClient
from .clients.equityTracking.equityTracking_client import EquityTrackingClient
from .models import format_error
from typing_extensions import TypedDict
from typing import Optional


class RetryOpts(TypedDict):
    retries: Optional[int]
    """Maximum amount of request retries, default value is 5."""
    minDelayInSeconds: Optional[float]
    """Minimum delay in seconds until request retry, default value is 1."""
    maxDelayInSeconds: Optional[float]
    """Maximum delay in seconds until request retry, default value is 30."""


class RiskManagementOptions(TypedDict):
    """Risk management SDK options."""
    domain: Optional[str]
    """Domain to connect to."""
    extendedTimeout: Optional[float]
    """Timeout for extended http requests in seconds."""
    requestTimeout: Optional[float]
    """Timeout for http requests in seconds."""
    retryOpts: Optional[RetryOpts]
    """Options for request retries."""


class RiskManagement:
    """MetaApi risk management API SDK."""

    def __init__(self, token: str, opts: RiskManagementOptions = None):
        """Inits class instance.

        Args:
            token: Authorization token.
            opts: Connection options.
        """
        opts: RiskManagementOptions = opts or {}
        domain = opts['domain'] if 'domain' in opts else 'agiliumtrade.agiliumtrade.ai'
        request_timeout = opts['requestTimeout'] if 'requestTimeout' in opts else 10
        request_extended_timeout = opts['extendedTimeout'] if 'extendedTimeout' in opts else 70
        retry_opts = opts['retryOpts'] if 'retryOpts' in opts else {}
        http_client = HttpClient(request_timeout, request_extended_timeout, retry_opts)
        self._domainClient = DomainClient(http_client, token, 'risk-management-api-v1', domain)
        self._equityTrackingClient = EquityTrackingClient(self._domainClient)

    @property
    def risk_management_api(self) -> EquityTrackingClient:
        """Returns CopyFactory configuration API.

        Returns:
            Configuration API.
        """
        return self._equityTrackingClient

    @staticmethod
    def format_error(err: Exception):
        """Formats and outputs metaApi errors with additional information.

        Args:
            err: Exception to process.
        """
        return format_error(err)
