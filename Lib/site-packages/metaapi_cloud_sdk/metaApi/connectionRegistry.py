from .streamingMetaApiConnection import StreamingMetaApiConnection
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from ..clients.metaApi.clientApi_client import ClientApiClient
from .metatraderAccountModel import MetatraderAccountModel
from .historyStorage import HistoryStorage
from .connectionRegistryModel import ConnectionRegistryModel
from datetime import datetime


class ConnectionRegistry(ConnectionRegistryModel):
    """Manages account connections"""

    def __init__(self, meta_api_websocket_client: MetaApiWebsocketClient, client_api_client: ClientApiClient,
                 application: str = 'MetaApi', refresh_subscriptions_opts: dict = None):
        """Inits a MetaTrader connection registry instance.

        Args:
            meta_api_websocket_client: MetaApi websocket client.
            client_api_client: Client API client.
            application: Application type.
            refresh_subscriptions_opts: Subscriptions refresh options.
        """
        refresh_subscriptions_opts = refresh_subscriptions_opts or {}
        self._meta_api_websocket_client = meta_api_websocket_client
        self._client_api_client = client_api_client
        self._application = application
        self._refresh_subscriptions_opts = refresh_subscriptions_opts
        self._connections = {}
        self._connectionLocks = {}

    def connect(self, account: MetatraderAccountModel, history_storage: HistoryStorage,
                history_start_time: datetime = None) -> StreamingMetaApiConnection:
        """Creates and returns a new account connection if doesnt exist, otherwise returns old.

        Args:
            account: MetaTrader account to connect to.
            history_storage: Terminal history storage.
            history_start_time: History start time.

        Returns:
            A coroutine resolving with account connection.
        """
        if account.id in self._connections:
            return self._connections[account.id]
        else:
            self._connections[account.id] = StreamingMetaApiConnection(
                self._meta_api_websocket_client, self._client_api_client, account, history_storage,
                self, history_start_time, self._refresh_subscriptions_opts)
            return self._connections[account.id]

    def remove(self, account_id: str):
        """Removes an account from registry.

        Args:
            account_id: MetaTrader account id to remove.
        """
        if account_id in self._connections:
            del self._connections[account_id]

    @property
    def application(self) -> str:
        """Returns application type.

        Returns:
            Application type.
        """
        return self._application
