from ..metaApi.filesystemHistoryDatabase import FilesystemHistoryDatabase
from .memoryHistoryStorageModel import MemoryHistoryStorageModel
import pytest
import json
import os
from datetime import datetime
from .models import MetatraderDeal, MetatraderOrder
from typing import List
import shutil
db: FilesystemHistoryDatabase or None = FilesystemHistoryDatabase()
storage = None
test_deal = None
test_deal2 = None
test_deal3 = None
test_order = None
test_order2 = None
test_order3 = None
test_config = None


class MockStorage(MemoryHistoryStorageModel):

    def __init__(self):
        super().__init__()
        self._deals = []
        self._historyOrders = []
        self._lastDealTimeByInstanceIndex = {}
        self._lastHistoryOrderTimeByInstanceIndex = {}

    @property
    def deals(self):
        return self._deals

    @property
    def history_orders(self):
        return self._historyOrders

    @property
    def last_deal_time_by_instance_index(self) -> dict:
        return self._lastDealTimeByInstanceIndex

    @property
    def last_history_order_time_by_instance_index(self) -> dict:
        return self._lastHistoryOrderTimeByInstanceIndex

    async def clear(self):
        pass

    def last_deal_time(self):
        pass

    def last_history_order_time(self):
        pass

    def on_deal_added(self, deal):
        pass

    def on_history_order_added(self, order):
        pass

    def get_deals_by_position(self, position_id: str) -> List[MetatraderDeal]:
        pass

    def get_deals_by_ticket(self, id: str) -> List[MetatraderDeal]:
        pass

    def get_deals_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderDeal]:
        pass

    def get_history_orders_by_position(self, position_id: str) -> List[MetatraderOrder]:
        pass

    def get_history_orders_by_ticket(self, id: str) -> List[MetatraderOrder]:
        pass

    def get_history_orders_by_time_range(self, start_time: datetime, end_time: datetime) -> List[MetatraderOrder]:
        pass

    def on_deals_synchronized(self, instance_index, synchronization_id):
        pass


async def read_history_storage_file():
    """Helper function to read saved history storage."""
    history = {
        'deals': [],
        'historyOrders': [],
        'lastDealTimeByInstanceIndex': {},
        'lastHistoryOrderTimeByInstanceIndex': {}
    }
    if os.path.isfile('.metaapi/accountId-application-config.bin'):
        config = json.loads(open('.metaapi/accountId-application-config.bin').read())
        history['lastDealTimeByInstanceIndex'] = config['lastDealTimeByInstanceIndex']
        history['lastHistoryOrderTimeByInstanceIndex'] = config['lastHistoryOrderTimeByInstanceIndex']
    if os.path.isfile('.metaapi/accountId-application-deals.bin'):
        history['deals'] = json.loads(open('.metaapi/accountId-application-deals.bin').read())
    if os.path.isfile('.metaapi/accountId-application-historyOrders.bin'):
        history['historyOrders'] = json.loads(open('.metaapi/accountId-application-historyOrders.bin').read())
    return history


@pytest.fixture(scope="module", autouse=True)
def run_around_module():
    if not os.path.exists('.metaapi'):
        os.mkdir('.metaapi')
    yield
    shutil.rmtree('.metaapi')


@pytest.fixture(autouse=True)
async def run_around_tests():
    global storage
    storage = MockStorage()
    global db
    db = FilesystemHistoryDatabase()
    global test_deal
    test_deal = {'id': '37863643', 'type': 'DEAL_TYPE_BALANCE', 'magic': 0, 'time':
                 datetime.fromtimestamp(100).isoformat(),
                 'commission': 0, 'swap': 0, 'profit': 10000, 'platform': 'mt5', 'comment': 'Demo deposit 1'}
    global test_deal2
    test_deal2 = {'id': '37863644', 'type': 'DEAL_TYPE_SELL', 'magic': 1, 'time':
                  datetime.fromtimestamp(200).isoformat(),
                  'commission': 0, 'swap': 0, 'profit': 10000, 'platform': 'mt5', 'comment': 'Demo deposit 2'}
    global test_deal3
    test_deal3 = {'id': '37863645', 'type': 'DEAL_TYPE_BUY', 'magic': 2, 'time':
                  datetime.fromtimestamp(300).isoformat(),
                  'commission': 0, 'swap': 0, 'profit': 10000, 'platform': 'mt5', 'comment': 'Demo deposit 3'}
    global test_order
    test_order = {'id': '61210463', 'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED', 'symbol': 'AUDNZD',
                  'magic': 0, 'time': datetime.fromtimestamp(50).isoformat(), 'doneTime':
                  datetime.fromtimestamp(100).isoformat(), 'currentPrice': 1, 'volume': 0.01, 'currentVolume': 0,
                  'positionId': '61206630', 'platform': 'mt5', 'comment': 'AS_AUDNZD_5YyM6KS7Fv:'}
    global test_order2
    test_order2 = {'id': '61210464', 'type': 'ORDER_TYPE_BUY_LIMIT', 'state': 'ORDER_STATE_FILLED', 'symbol': 'AUDNZD',
                   'magic': 1, 'time': datetime.fromtimestamp(75).isoformat(), 'doneTime':
                   datetime.fromtimestamp(200).isoformat(), 'currentPrice': 1, 'volume': 0.01, 'currentVolume': 0,
                   'positionId': '61206631', 'platform': 'mt5', 'comment': 'AS_AUDNZD_5YyM6KS7Fv:'}
    global test_order3
    test_order3 = {'id': '61210465', 'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED', 'symbol': 'AUDNZD',
                   'magic': 2, 'time': datetime.fromtimestamp(100).isoformat(), 'doneTime':
                   datetime.fromtimestamp(300).isoformat(), 'currentPrice': 1, 'volume': 0.01, 'currentVolume': 0,
                   'positionId': '61206632', 'platform': 'mt5', 'comment': 'AS_AUDNZD_5YyM6KS7Fv:'}
    global test_config
    test_config = {
        'lastDealTimeByInstanceIndex': {'0': 1000000000000},
        'lastHistoryOrderTimeByInstanceIndex': {'0': 1000000000010}
    }
    yield
    if os.path.isfile('.metaapi/accountId-application-deals.bin'):
        os.remove('.metaapi/accountId-application-deals.bin')
    if os.path.isfile('.metaapi/accountId-application-historyOrders.bin'):
        os.remove('.metaapi/accountId-application-historyOrders.bin')


class TestHistoryFileManager:

    @pytest.mark.asyncio
    async def test_read_db(self):
        """Should read db contents."""
        deals_data = '{"id":"1"}\n{"id":"2"}\n'
        history_orders_data = '{"id":"2"}\n{"id":"3"}\n'
        f = open('.metaapi/accountId-MetaApi-deals.bin', "w+")
        f.write(deals_data)
        f.close()

        f = open('.metaapi/accountId-MetaApi-historyOrders.bin', "w+")
        f.write(history_orders_data)
        f.close()

        data = await db.load_history('accountId', 'MetaApi')
        assert data['deals'] == [{'id': '1'}, {'id': '2'}]
        assert data['historyOrders'] == [{'id': '2'}, {'id': '3'}]

    @pytest.mark.asyncio
    async def test_clear_db(self):
        """Should clear db."""
        deals_data = '{"id":"1"}\n{"id":"2"}\n'
        history_orders_data = '{"id":"2"}\n{"id":"3"}\n'
        f = open('.metaapi/accountId-MetaApi-deals.bin', "w+")
        f.write(deals_data)
        f.close()

        f = open('.metaapi/accountId-MetaApi-historyOrders.bin', "w+")
        f.write(history_orders_data)
        f.close()

        await db.clear('accountId', 'MetaApi')
        data = await db.load_history('accountId', 'MetaApi')
        assert data['deals'] == []
        assert data['historyOrders'] == []

    @pytest.mark.asyncio
    async def test_flush_to_db(self):
        """Should flush to db."""
        await db.flush('accountId', 'MetaApi', [{'id': '2'}], [{'id': '1'}])
        await db.flush('accountId', 'MetaApi', [{'id': '3'}], [{'id': '2'}])

        data = await db.load_history('accountId', 'MetaApi')
        assert data['deals'] == [{'id': '1'}, {'id': '2'}]
        assert data['historyOrders'] == [{'id': '2'}, {'id': '3'}]
