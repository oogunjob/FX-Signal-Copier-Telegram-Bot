from .metatraderAccountApi import MetatraderAccountApi
from .metatraderAccount import MetatraderAccount
from ..clients.errorHandler import NotFoundException
from ..clients.metaApi.metaApiWebsocket_client import MetaApiWebsocketClient
from ..clients.metaApi.metatraderAccount_client import MetatraderAccountClient, NewMetatraderAccountDto
from .streamingMetaApiConnection import StreamingMetaApiConnection
from ..clients.metaApi.reconnectListener import ReconnectListener
from ..clients.metaApi.historicalMarketData_client import HistoricalMarketDataClient
from .connectionRegistry import ConnectionRegistry
from .memoryHistoryStorage import MemoryHistoryStorage
from .historyStorage import HistoryStorage
from mock import AsyncMock, MagicMock, patch
from .metatraderAccountModel import MetatraderAccountModel
from ..clients.metaApi.expertAdvisor_client import ExpertAdvisorClient
from .expertAdvisor import ExpertAdvisor
from httpx import Response
from datetime import datetime
from .models import date
import pytest


class MockClient(MetatraderAccountClient):
    def get_accounts(self, provisioning_profile_id: str = None) -> Response:
        pass

    def get_account(self, id: str) -> Response:
        pass

    def create_account(self, account: NewMetatraderAccountDto) -> Response:
        pass

    def delete_account(self, id: str) -> Response:
        pass

    def deploy_account(self, id: str) -> Response:
        pass

    def undeploy_account(self, id: str) -> Response:
        pass

    def redeploy_account(self, id: str) -> Response:
        pass


class MockWebsocketClient(MetaApiWebsocketClient):
    def add_synchronization_listener(self, account_id: str, listener):
        pass

    def add_reconnect_listener(self, listener: ReconnectListener):
        pass

    def subscribe(self, account_id: str):
        pass


class MockStorage(MemoryHistoryStorage):
    async def last_history_order_time(self) -> datetime:
        return date('2020-01-01T00:00:00.000Z')

    async def last_deal_time(self) -> datetime:
        return date('2020-01-02T00:00:00.000Z')


class MockRegistry(ConnectionRegistry):
    async def connect(self, account: MetatraderAccountModel, history_storage: HistoryStorage,
                      history_start_time: datetime = None):
        pass

    def remove(self, account_id: str):
        pass


client: MockClient = None
websocket_client: MockWebsocketClient = None
registry: MockRegistry = None
api: MetatraderAccountApi = None
ea_client: ExpertAdvisorClient = None
history_client: HistoricalMarketDataClient = None


@pytest.fixture(autouse=True)
async def run_around_tests():
    global client
    client = MockClient(MagicMock(), MagicMock())
    global websocket_client
    websocket_client = MockWebsocketClient(MagicMock(), 'token')
    global registry
    registry = MockRegistry(websocket_client, MagicMock())
    global api
    registry.connect = AsyncMock()
    registry.remove = MagicMock()
    global ea_client
    ea_client = ExpertAdvisorClient(MagicMock(), 'token')
    global history_client
    history_client = HistoricalMarketDataClient(MagicMock(), 'token')
    api = MetatraderAccountApi(client, websocket_client, registry, ea_client, history_client, 'MetaApi')
    yield


class TestMetatraderAccountApi:
    @pytest.mark.asyncio
    async def test_retrieve_mt_accounts(self):
        """Should retrieve MT accounts."""
        client.get_accounts = AsyncMock(return_value=[{'_id': 'id'}])
        accounts = await api.get_accounts({'provisioningProfileId': 'profileId'})
        assert list(map(lambda a: a.id, accounts)) == ['id']
        for account in accounts:
            assert isinstance(account, MetatraderAccount)
        client.get_accounts.assert_called_with({'provisioningProfileId': 'profileId'})

    @pytest.mark.asyncio
    async def test_retrieve_mt_account_by_id(self):
        """Should retrieve MT account by id."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud',
            'accessToken': '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        })
        account = await api.get_account('id')
        assert account.id == 'id'
        assert account.login == '50194988'
        assert account.name == 'mt5a'
        assert account.server == 'ICMarketsSC-Demo'
        assert account.provisioning_profile_id == 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076'
        assert account.magic == 123456
        assert account.application == 'MetaApi'
        assert account.connection_status == 'DISCONNECTED'
        assert account.state == 'DEPLOYED'
        assert account.type == 'cloud'
        assert account.access_token == '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        assert isinstance(account, MetatraderAccount)
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_retrieve_mt_account_by_token(self):
        """Should retrieve MT account by id."""
        client.get_account_by_token = AsyncMock(return_value={
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud',
            'accessToken': '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        })
        account = await api.get_account_by_token()
        assert account.id == 'id'
        assert account.login == '50194988'
        assert account.name == 'mt5a'
        assert account.server == 'ICMarketsSC-Demo'
        assert account.provisioning_profile_id == 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076'
        assert account.magic == 123456
        assert account.application == 'MetaApi'
        assert account.connection_status == 'DISCONNECTED'
        assert account.state == 'DEPLOYED'
        assert account.type == 'cloud'
        assert account.access_token == '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        assert isinstance(account, MetatraderAccount)
        client.get_account_by_token.assert_called_with()

    @pytest.mark.asyncio
    async def test_create_mt_account(self):
        """Should create MT account."""
        client.create_account = AsyncMock(return_value={'id': 'id'})
        client.get_account = AsyncMock(return_value={
          '_id': 'id',
          'login': '50194988',
          'name': 'mt5a',
          'server': 'ICMarketsSC-Demo',
          'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
          'magic': 123456,
          'application': 'MetaApi',
          'connectionStatus': 'DISCONNECTED',
          'state': 'DEPLOYED',
          'type': 'cloud',
          'accessToken': '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        })
        new_account_data = {
            'login': '50194988',
            'password': 'Test1234',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'type': 'cloud',
            'accessToken': 'NyV5no9TMffJyUts2FjI80wly0so3rVCz4xOqiDx'
        }
        account = await api.create_account(new_account_data)
        assert account.id == 'id'
        assert account.login == '50194988'
        assert account.name == 'mt5a'
        assert account.server == 'ICMarketsSC-Demo'
        assert account.provisioning_profile_id == 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076'
        assert account.magic == 123456
        assert account.application == 'MetaApi'
        assert account.connection_status == 'DISCONNECTED'
        assert account.state == 'DEPLOYED'
        assert account.type == 'cloud'
        assert account.access_token == '2RUnoH1ldGbnEneCoqRTgI4QO1XOmVzbH5EVoQsA'
        assert isinstance(account, MetatraderAccount)
        client.create_account.assert_called_with(new_account_data)
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_reload_mt_account(self):
        """Should reload MT account."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYING',
            'type': 'cloud'
          },
            {
                '_id': 'id',
                'login': '50194988',
                'name': 'mt5a',
                'server': 'ICMarketsSC-Demo',
                'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                'magic': 123456,
                'application': 'MetaApi',
                'connectionStatus': 'CONNECTED',
                'state': 'DEPLOYED',
                'type': 'cloud'
            }])
        account = await api.get_account('id')
        await account.reload()
        assert account.connection_status == 'CONNECTED'
        assert account.state == 'DEPLOYED'
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_remove_mt_account(self):
        """Should remove MT account."""
        with patch('lib.metaApi.metatraderAccount.FilesystemHistoryDatabase.clear',
                   new_callable=AsyncMock) as delete_mock:
            client.get_account = AsyncMock(side_effect=[{
                '_id': 'id',
                'login': '50194988',
                'name': 'mt5a',
                'server': 'ICMarketsSC-Demo',
                'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                'magic': 123456,
                'application': 'MetaApi',
                'connectionStatus': 'CONNECTED',
                'state': 'DEPLOYED',
                'type': 'cloud'
              },
                {
                    '_id': 'id',
                    'login': '50194988',
                    'name': 'mt5a',
                    'server': 'ICMarketsSC-Demo',
                    'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                    'magic': 123456,
                    'application': 'MetaApi',
                    'connectionStatus': 'CONNECTED',
                    'state': 'DELETING',
                    'type': 'cloud'
                }
            ])
            client.delete_account = AsyncMock()
            account = await api.get_account('id')
            await account.remove()
            delete_mock.assert_called_with('id', 'MetaApi')
            registry.remove.assert_called_with('id')
            assert account.state == 'DELETING'
            client.delete_account.assert_called_with('id')
            client.get_account.assert_called_with('id')
            assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_deploy_mt_account(self):
        """Should deploy MT account."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'UNDEPLOYED',
            'type': 'cloud'
          }, {
                '_id': 'id',
                'login': '50194988',
                'name': 'mt5a',
                'server': 'ICMarketsSC-Demo',
                'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                'magic': 123456,
                'application': 'MetaApi',
                'connectionStatus': 'CONNECTED',
                'state': 'DEPLOYING',
                'type': 'cloud'
        }])
        client.deploy_account = AsyncMock()
        account = await api.get_account('id')
        await account.deploy()
        assert account.state == 'DEPLOYING'
        client.deploy_account.assert_called_with('id')
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_undeploy_mt_account(self):
        """Should undeploy MT account."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
          }, {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'CONNECTED',
            'state': 'UNDEPLOYING',
            'type': 'cloud'
        }])
        client.undeploy_account = AsyncMock()
        account = await api.get_account('id')
        await account.undeploy()
        registry.remove.assert_called_with('id')
        assert account.state == 'UNDEPLOYING'
        client.undeploy_account.assert_called_with('id')
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_redeploy_mt_account(self):
        """Should redeploy MT account."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
          }, {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'CONNECTED',
            'state': 'UNDEPLOYING',
            'type': 'cloud'
          }])
        client.redeploy_account = AsyncMock()
        account = await api.get_account('id')
        await account.redeploy()
        assert account.state == 'UNDEPLOYING'
        client.redeploy_account.assert_called_with('id')
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_increase_reliability(self):
        """Should increase MT account reliability."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
        }, {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'CONNECTED',
            'state': 'UNDEPLOYING',
            'type': 'cloud',
            'reliability': 'high'
        }])
        client.increase_reliability = AsyncMock()
        account = await api.get_account('id')
        await account.increase_reliability()
        assert account.reliability == 'high'
        client.increase_reliability.assert_called_with('id')
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_deployment(self):
        """Should wait for deployment."""
        deploying_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYING',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(side_effect=[deploying_account, deploying_account,
                                                    {
                                                        '_id': 'id',
                                                        'login': '50194988',
                                                        'name': 'mt5a',
                                                        'server': 'ICMarketsSC-Demo',
                                                        'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                                                        'magic': 123456,
                                                        'application': 'MetaApi',
                                                        'connectionStatus': 'CONNECTED',
                                                        'state': 'DEPLOYED',
                                                        'type': 'cloud'
                                                    }
                                                    ])
        account = await api.get_account('id')
        await account.wait_deployed(1, 50)
        assert account.state == 'DEPLOYED'
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 3

    @pytest.mark.asyncio
    async def test_time_out_deployment(self):
        """Should time out waiting for deployment."""
        deploying_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYING',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(return_value=deploying_account)
        account = await api.get_account('id')
        try:
            await account.wait_deployed(1, 50)
            raise Exception('TimeoutError is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            assert account.state == 'DEPLOYING'
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_wait_for_undeployment(self):
        """Should wait for undeployment."""
        undeploying_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'UNDEPLOYING',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(side_effect=[undeploying_account, undeploying_account,
                                                    {
                                                        '_id': 'id',
                                                        'login': '50194988',
                                                        'name': 'mt5a',
                                                        'server': 'ICMarketsSC-Demo',
                                                        'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                                                        'magic': 123456,
                                                        'application': 'MetaApi',
                                                        'connectionStatus': 'CONNECTED',
                                                        'state': 'UNDEPLOYED',
                                                        'type': 'cloud'
                                                    }
                                                    ])
        account = await api.get_account('id')
        await account.wait_undeployed(1, 50)
        assert account.state == 'UNDEPLOYED'
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 3

    @pytest.mark.asyncio
    async def test_time_out_undeployment(self):
        """Should wait for undeployment."""
        undeploying_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'UNDEPLOYING',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(return_value=undeploying_account)
        account = await api.get_account('id')
        try:
            await account.wait_undeployed(1, 50)
            raise Exception('TimeoutException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            assert account.state == 'UNDEPLOYING'
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_wait_until_removed(self):
        """Should wait until removed."""
        deleting_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DELETING',
            'type': 'cloud'
          }
        client.get_account = AsyncMock(side_effect=[deleting_account, deleting_account, NotFoundException('')])
        account = await api.get_account('id')
        await account.wait_removed(1, 50)
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 3

    @pytest.mark.asyncio
    async def test_time_out_waiting_until_removed(self):
        """Should wait until removed."""
        deleting_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DELETING',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(return_value=deleting_account)
        account = await api.get_account('id')
        try:
            await account.wait_removed(1, 50)
            raise Exception('TimeoutException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_wait_until_broker_connection(self):
        """Should wait util broker connection."""
        disconnected_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(side_effect=[disconnected_account, disconnected_account,
                                                    {
                                                        '_id': 'id',
                                                        'login': '50194988',
                                                        'name': 'mt5a',
                                                        'server': 'ICMarketsSC-Demo',
                                                        'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
                                                        'magic': 123456,
                                                        'application': 'MetaApi',
                                                        'connectionStatus': 'CONNECTED',
                                                        'state': 'DEPLOYED',
                                                        'type': 'cloud'
                                                    }])
        account = await api.get_account('id')
        await account.wait_connected(1, 50)
        assert account.connection_status == 'CONNECTED'
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 3

    @pytest.mark.asyncio
    async def test_time_out_waiting_for_broker_connection(self):
        """Should time out waiting for broker connection."""
        disconnected_account = {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'DISCONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
        }
        client.get_account = AsyncMock(return_value=disconnected_account)
        account = await api.get_account('id')
        try:
            await account.wait_connected(1, 50)
            raise Exception('TimeoutException is expected')
        except Exception as err:
            assert err.__class__.__name__ == 'TimeoutException'
            assert account.connection_status == 'DISCONNECTED'
        client.get_account.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_connect_to_mt_terminal(self):
        """Should connect to an MT terminal."""
        with patch('lib.metaApi.streamingMetaApiConnection.StreamingMetaApiConnection.initialize', AsyncMock()):
            websocket_client.add_synchronization_listener = MagicMock()
            websocket_client.subscribe = AsyncMock()
            client.get_account = AsyncMock(return_value={'_id': 'id'})
            account = await api.get_account('id')
            storage = MockStorage()
            account.get_streaming_connection(storage)
            registry.connect.assert_called_with(account, storage, None)

    @pytest.mark.asyncio
    async def test_connect_to_terminal_if_in_specified_region(self):
        """Should connect to an MT terminal if in specified region."""
        websocket_client._region = 'vint-hill'
        client.get_account = AsyncMock(return_value={'_id': 'id', 'region': 'vint-hill'})
        account = await api.get_account('accountId')
        storage = MockStorage()
        connect_mock = MagicMock()
        registry.connect = connect_mock
        account.get_streaming_connection(storage)
        connect_mock.assert_called_with(account, storage, None)

    @pytest.mark.asyncio
    async def test_not_connect_to_terminal_if_in_different_region(self):
        """Should not connect to an MT terminal if in different region."""
        websocket_client._region = 'vint-hill'
        client.get_account = AsyncMock(return_value={'_id': 'id', 'region': 'new-york'})
        account = await api.get_account('accountId')
        storage = MockStorage()
        connect_mock = MagicMock()
        registry.connect = connect_mock
        try:
            account.get_streaming_connection(storage)
            pytest.fail()
        except Exception as err:
            assert err.args[0] == \
                   'Account id is not on specified region vint-hill, check error.details for more information'

    @pytest.mark.asyncio
    async def test_create_rpc_connection(self):
        """Should create RPC connection."""
        websocket_client._region = None
        client.get_account = AsyncMock(return_value={'_id': 'id', 'region': 'vint-hill'})
        account = await api.get_account('accountId')
        connect_mock = MagicMock()
        registry.connect = connect_mock
        account.get_rpc_connection()

    @pytest.mark.asyncio
    async def test_create_rpc_connection_if_in_specified_region(self):
        """Should create RPC connection if in specified region."""
        websocket_client._region = 'vint-hill'
        client.get_account = AsyncMock(return_value={'_id': 'id', 'region': 'vint-hill'})
        account = await api.get_account('accountId')
        connect_mock = MagicMock()
        registry.connect = connect_mock
        account.get_rpc_connection()

    @pytest.mark.asyncio
    async def test_not_create_rpc_connection_if_in_different_region(self):
        """Should not create RPC connection if in different region."""
        websocket_client._region = 'vint-hill'
        client.get_account = AsyncMock(return_value={'_id': 'id', 'region': 'new-york'})
        account = await api.get_account('accountId')
        connect_mock = MagicMock()
        registry.connect = connect_mock
        try:
            account.get_rpc_connection()
            pytest.fail()
        except Exception as err:
            assert err.args[0] == 'Account id is not on specified region vint-hill, check error.details for ' +\
                'more information'

    @pytest.mark.asyncio
    async def test_update_mt_account(self):
        """Should update MT account."""
        client.get_account = AsyncMock(side_effect=[{
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a',
            'server': 'ICMarketsSC-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'CONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
          }, {
            '_id': 'id',
            'login': '50194988',
            'name': 'mt5a__',
            'server': 'OtherMarkets-Demo',
            'provisioningProfileId': 'f9ce1f12-e720-4b9a-9477-c2d4cb25f076',
            'magic': 123456,
            'application': 'MetaApi',
            'connectionStatus': 'CONNECTED',
            'state': 'DEPLOYED',
            'type': 'cloud'
          }])
        client.update_account = AsyncMock()
        account = await api.get_account('id')
        await account.update({
          'name': 'mt5a__',
          'password': 'moreSecurePass',
          'server': 'OtherMarkets-Demo',
        })
        assert account.name == 'mt5a__'
        assert account.server == 'OtherMarkets-Demo'
        client.update_account.assert_called_with('id', {
          'name': 'mt5a__',
          'password': 'moreSecurePass',
          'server': 'OtherMarkets-Demo',
        })
        client.get_account.assert_called_with('id')
        assert client.get_account.call_count == 2

    @pytest.mark.asyncio
    async def test_retrieve_expert_advisors(self):
        """Should retrieve expert advisors."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisors = AsyncMock(return_value=[{'expertId': 'ea'}])
        account = await api.get_account('id')
        experts = await account.get_expert_advisors()
        assert list(map(lambda e: e.expert_id, experts)) == ['ea']
        for ea in experts:
            assert isinstance(ea, ExpertAdvisor)
        ea_client.get_expert_advisors.assert_called_with('id')

    @pytest.mark.asyncio
    async def test_retrieve_expert_advisor(self):
        """Should retrieve expert advisor by expert id."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisor = AsyncMock(return_value={
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        })
        account = await api.get_account('id')
        expert = await account.get_expert_advisor('ea')
        assert expert.expert_id == 'ea'
        assert expert.period == '1H'
        assert expert.symbol == 'EURUSD'
        assert not expert.file_uploaded
        assert isinstance(expert, ExpertAdvisor)
        ea_client.get_expert_advisor.assert_called_with('id', 'ea')

    @pytest.mark.asyncio
    async def test_validate_account_version(self):
        """Should validate account version."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 5,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisors = AsyncMock(return_value=[{
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }])
        ea_client.get_expert_advisor = AsyncMock(return_value={
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        })
        ea_client.update_expert_advisor = AsyncMock()
        new_expert_advisor = {
            'period': '1H',
            'symbol': 'EURUSD',
            'preset': 'preset'
        }
        account = await api.get_account('id')
        try:
            await account.get_expert_advisors()
            pytest.fail()
        except Exception:
            pass
        try:
            await account.get_expert_advisor('ea')
            pytest.fail()
        except Exception:
            pass
        try:
            await account.create_expert_advisor('ea', new_expert_advisor)
            pytest.fail()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_validate_account_type(self):
        """Should validate account type."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g2'
        })
        ea_client.get_expert_advisors = AsyncMock(return_value=[{
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }])
        ea_client.get_expert_advisor = AsyncMock(return_value={
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        })
        ea_client.update_expert_advisor = AsyncMock()
        new_expert_advisor = {
            'period': '1H',
            'symbol': 'EURUSD',
            'preset': 'preset'
        }
        account = await api.get_account('id')
        try:
            await account.get_expert_advisors()
            pytest.fail()
        except Exception:
            pass
        try:
            await account.get_expert_advisor('ea')
            pytest.fail()
        except Exception:
            pass
        try:
            await account.create_expert_advisor('ea', new_expert_advisor)
            pytest.fail()
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_create_expert_advisor(self):
        """Should create expert advisor."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.update_expert_advisor = AsyncMock()
        ea_client.get_expert_advisor = AsyncMock(return_value={
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        })
        new_expert_advisor = {
          'period': '1H',
          'symbol': 'EURUSD',
          'preset': 'preset'
        }
        account = await api.get_account('id')
        expert = await account.create_expert_advisor('ea', new_expert_advisor)
        assert expert.expert_id == 'ea'
        assert expert.period == '1H'
        assert expert.symbol == 'EURUSD'
        assert not expert.file_uploaded
        assert isinstance(expert, ExpertAdvisor)
        ea_client.update_expert_advisor.assert_called_with('id', 'ea', new_expert_advisor)
        ea_client.get_expert_advisor.assert_called_with('id', 'ea')

    @pytest.mark.asyncio
    async def test_reload_expert_advisor(self):
        """Should reload expert advisor."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisor = AsyncMock(side_effect=[{
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }, {
            'expertId': 'ea',
            'period': '4H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }])
        account = await api.get_account('id')
        expert = await account.get_expert_advisor('ea')
        await expert.reload()
        assert expert.period == '4H'
        ea_client.get_expert_advisor.assert_called_with('id', 'ea')
        assert ea_client.get_expert_advisor.call_count == 2

    @pytest.mark.asyncio
    async def test_update_expert_advisor(self):
        """Should update expert advisor."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisor = AsyncMock(side_effect=[{
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }, {
            'expertId': 'ea',
            'period': '4H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }])
        new_expert_advisor = {
            'period': '4H',
            'symbol': 'EURUSD',
            'preset': 'preset'
        }
        ea_client.update_expert_advisor = AsyncMock()
        account = await api.get_account('id')
        expert = await account.get_expert_advisor('ea')
        await expert.update(new_expert_advisor)
        assert expert.period == '4H'
        ea_client.update_expert_advisor.assert_called_with('id', 'ea', new_expert_advisor)
        assert ea_client.get_expert_advisor.call_count == 2
        ea_client.get_expert_advisor.assert_called_with('id', 'ea')

    @pytest.mark.asyncio
    async def test_upload_expert_advisor_file(self):
        """Should upload expert advisor file."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisor = AsyncMock(side_effect=[{
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        }, {
            'expertId': 'ea',
            'period': '4H',
            'symbol': 'EURUSD',
            'fileUploaded': True
        }])
        ea_client.upload_expert_advisor_file = AsyncMock()
        account = await api.get_account('id')
        expert = await account.get_expert_advisor('ea')
        await expert.upload_file('/path/to/file')
        assert expert.file_uploaded
        ea_client.upload_expert_advisor_file.assert_called_with('id', 'ea', '/path/to/file')
        assert ea_client.get_expert_advisor.call_count == 2
        ea_client.get_expert_advisor.assert_called_with('id', 'ea')

    @pytest.mark.asyncio
    async def test_remove_expert_advisor(self):
        """Should remove expert advisor."""
        client.get_account = AsyncMock(return_value={
            '_id': 'id',
            'version': 4,
            'type': 'cloud-g1'
        })
        ea_client.get_expert_advisor = AsyncMock(return_value={
            'expertId': 'ea',
            'period': '1H',
            'symbol': 'EURUSD',
            'fileUploaded': False
        })
        ea_client.delete_expert_advisor = AsyncMock(return_value={'_id': 'id'})
        account = await api.get_account('id')
        expert = await account.get_expert_advisor('ea')
        await expert.remove()
        ea_client.delete_expert_advisor.assert_called_with('id', 'ea')
