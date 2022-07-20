from ..metaApi_client import MetaApiClient
from typing_extensions import TypedDict
from typing import Optional


class NewMT4DemoAccount(TypedDict, total=False):
    """New MetaTrader 4 demo account request model."""
    accountType: Optional[str]
    """Account type. Available account type values can be found in mobile MT application or in MT terminal downloaded
    from our broker."""
    balance: float
    """Account balance."""
    email: str
    """Account holder's email."""
    leverage: float
    """Account leverage."""
    name: Optional[str]
    """Account holder's name."""
    phone: Optional[str]
    """Account holder's phone."""
    serverName: str
    """Server name."""


class NewMT4LiveAccount(TypedDict, total=False):
    """New MetaTrader 4 live account request model."""
    accountType: Optional[str]
    """Account type. Available account type values can be found in mobile MT application or in MT terminal downloaded
    from our broker."""
    address: Optional[str]
    """Account holder's address."""
    city: Optional[str]
    """Account holder's city."""
    country: Optional[str]
    """Account holder's country."""
    email: str
    """Account holder's email."""
    leverage: float
    """Account leverage."""
    name: Optional[str]
    """Account holder's name."""
    phone: Optional[str]
    """Account holder's phone."""
    serverName: str
    """Server name."""
    state: Optional[str]
    """Account holder's state"""
    zip: Optional[str]
    """Zip address."""


class NewMT5DemoAccount(TypedDict, total=False):
    """New MetaTrader 5 demo account request model."""
    accountType: Optional[str]
    """Account type. Available account type values can be found in mobile MT application or in MT terminal downloaded
    from our broker."""
    balance: float
    """Account balance."""
    email: str
    """Account holder's email."""
    leverage: float
    """Account leverage."""
    name: Optional[str]
    """Account holder's name."""
    phone: Optional[str]
    """Account holder's phone."""
    serverName: str
    """Server name."""


class NewMT5LiveAccount(TypedDict, total=False):
    """New MetaTrader 5 live account request model."""
    accountType: Optional[str]
    """Account type. Available account type values can be found in mobile MT application or in MT terminal downloaded
    from our broker."""
    address: Optional[str]
    """Account holder's address."""
    city: Optional[str]
    """Account holder's city."""
    country: Optional[str]
    """Account holder's country."""
    email: str
    """Account holder's email."""
    leverage: float
    """Account leverage."""
    name: Optional[str]
    """Account holder's name."""
    phone: Optional[str]
    """Account holder's phone."""
    serverName: str
    """Server name."""
    state: Optional[str]
    """Account holder's state"""
    zip: Optional[str]
    """Zip address."""


class MetatraderAccountCredentialsDto(TypedDict):
    """MetaTrader demo account model."""
    login: str
    """Account login."""
    password: str
    """Account password."""
    serverName: str
    """MetaTrader server name."""
    investorPassword: str
    """Account investor (read-only) password."""


class MetatraderAccountGeneratorClient(MetaApiClient):
    """metaapi.cloud MetaTrader account generator API client."""

    async def create_mt4_demo_account(self, account: NewMT4DemoAccount, profile_id: str = None) \
            -> MetatraderAccountCredentialsDto:
        """Creates new MetaTrader 4 demo account.
        See https://metaapi.cloud/docs/provisioning/api/generateAccount/createMT4DemoAccount/
        Method is accessible only with API access token.

        Args:
            account: Account to create.
            profile_id: Id of the provisioning profile that will be used as the basis for creating this account.

        Returns:
            A coroutine resolving with MetaTrader account credentials.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('create_mt4_demo_account')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{profile_id or "default"}/mt4-demo-accounts',
            'method': 'POST',
            'headers': {
                'auth-token': self._token
            },
            'body': account
        }
        return await self._httpClient.request(opts)

    async def create_mt4_live_account(self, account: NewMT4LiveAccount, profile_id: str = None) \
            -> MetatraderAccountCredentialsDto:
        """Creates new MetaTrader 4 live account.
        See https://metaapi.cloud/docs/provisioning/api/generateAccount/createMT4LiveAccount/
        Method is accessible only with API access token.

        Args:
            account: Account to create.
            profile_id: Id of the provisioning profile that will be used as the basis for creating this account.

        Returns:
            A coroutine resolving with MetaTrader account credentials.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('create_mt4_live_account')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{profile_id or "default"}/mt4-live-accounts',
            'method': 'POST',
            'headers': {
                'auth-token': self._token
            },
            'body': account
        }
        return await self._httpClient.request(opts)

    async def create_mt5_demo_account(self, account: NewMT5DemoAccount, profile_id: str = None) \
            -> MetatraderAccountCredentialsDto:
        """Creates new MetaTrader 5 demo account.
        See https://metaapi.cloud/docs/provisioning/api/generateAccount/createMT5DemoAccount/
        Method is accessible only with API access token.

        Args:
            account: Account to create.
            profile_id: Id of the provisioning profile that will be used as the basis for creating this account.

        Returns:
            A coroutine resolving with MetaTrader demo account created.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('create_mt5_demo_account')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{profile_id or "default"}/mt5-demo-accounts',
            'method': 'POST',
            'headers': {
                'auth-token': self._token
            },
            'body': account
        }
        return await self._httpClient.request(opts)

    async def create_mt5_live_account(self, account: NewMT5LiveAccount, profile_id: str = None) \
            -> MetatraderAccountCredentialsDto:
        """Creates new MetaTrader 5 live account.
        See https://metaapi.cloud/docs/provisioning/api/generateAccount/createMT5LiveAccount/
        Method is accessible only with API access token.

        Args:
            account: Account to create.
            profile_id: Id of the provisioning profile that will be used as the basis for creating this account.

        Returns:
            A coroutine resolving with MetaTrader demo account created.
        """
        if self._is_not_jwt_token():
            return self._handle_no_access_exception('create_mt5_live_account')
        opts = {
            'url': f'{self._host}/users/current/provisioning-profiles/{profile_id or "default"}/mt5-live-accounts',
            'method': 'POST',
            'headers': {
                'auth-token': self._token
            },
            'body': account
        }
        return await self._httpClient.request(opts)
