from .memoryHistoryStorage import MemoryHistoryStorage
from .models import date
from mock import AsyncMock, patch
import pytest
from asyncio import sleep
start_time = '2020-10-10 00:00:01.000'
storage: MemoryHistoryStorage = None
db = AsyncMock()


@pytest.fixture(autouse=True)
async def run_around_tests(mocker):
    global storage
    storage = MemoryHistoryStorage()
    storage._historyDatabase = db
    await storage.initialize('accountId', 'MetaApi')
    await storage.clear()
    await storage.on_connected('1:ps-mpa-1', 1)


class TestMemoryHistoryStorage:
    @pytest.mark.asyncio
    async def test_load_data_from_file_manager(self):
        """Should load data from the file manager."""
        test_deal = {'id': '37863643', 'type': 'DEAL_TYPE_BALANCE', 'magic': 0, 'time':
                     date(1000000), 'entryType': 'DEAL_ENTRY_IN',
                     'commission': 0, 'swap': 0, 'profit': 10000, 'platform': 'mt5', 'comment': 'Demo deposit 1'}
        test_order = {'id': '61210463', 'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED', 'symbol': 'AUDNZD',
                      'magic': 0, 'time': date(5000000), 'doneTime': date(1000000), 'currentPrice': 1, 'volume': 0.01,
                      'currentVolume': 0,
                      'positionId': '61206630', 'platform': 'mt5', 'comment': 'AS_AUDNZD_5YyM6KS7Fv:'}
        db.load_history = AsyncMock(return_value={'deals': [test_deal], 'historyOrders': [test_order]})
        await storage.initialize('accountId', 'MetaApi')
        assert storage.deals == [test_deal]
        assert storage.history_orders == [test_order]

    @pytest.mark.asyncio
    async def test_clear_storage(self):
        """Should clear db storage."""

        db.clear = AsyncMock()
        await storage.on_deal_added('1:ps-mpa-1', {'id': '3', 'time': date('2020-01-02T00:00:00.000Z'),
                                                   'entryType': 'DEAL_ENTRY_IN', 'type': 'DEAL_TYPE_SELL'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '3', 'doneTime': date('2020-01-02T00:00:00.000Z'),
                                                            'state': 'ORDER_STATE_FILLED', 'type': 'ORDER_TYPE_SELL'})
        await storage.clear()
        assert storage.deals == []
        assert storage.history_orders == []
        db.clear.assert_called_with('accountId', 'MetaApi')

    @pytest.mark.asyncio
    async def test_return_last_history_order_time(self):
        """Should return last history order time."""

        await storage.on_history_order_added('1:ps-mpa-1', {'id': '1', 'state': 'ORDER_STATE_FILLED',
                                                            'type': 'ORDER_TYPE_SELL'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '2', 'state': 'ORDER_STATE_FILLED',
                                                            'type': 'ORDER_TYPE_SELL',
                                                            'doneTime': date('2020-01-01T00:00:00.000Z')})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '3', 'state': 'ORDER_STATE_FILLED',
                                                            'type': 'ORDER_TYPE_SELL',
                                                            'doneTime': date('2020-01-02T00:00:00.000Z')})
        assert await storage.last_history_order_time() == date('2020-01-02T00:00:00.000Z')

    @pytest.mark.asyncio
    async def test_return_last_deal_time(self):
        """Should return last deal time."""

        await storage.on_deal_added('1:ps-mpa-1', {'id': '1', 'entryType': 'DEAL_ENTRY_IN',
                                                   'time': date('2019-01-01T00:00:00.000Z')})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '2', 'entryType': 'DEAL_ENTRY_IN',
                                                   'time': date('2020-01-01T00:00:00.000Z')})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '3', 'entryType': 'DEAL_ENTRY_IN',
                                                   'time': date('2020-01-02T00:00:00.000Z')})
        assert await storage.last_deal_time() == date('2020-01-02T00:00:00.000Z')

    @pytest.mark.asyncio
    async def test_return_saved_deals(self):
        """Should return saved deals."""

        await storage.on_deal_added('1:ps-mpa-1', {'id': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                                                   'positionId': '1',
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '7', 'time': date('2020-05-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '8', 'time': date('2020-02-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '6', 'time': date('2020-10-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '4', 'time': date('2020-02-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '5', 'time': date('2020-06-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '11', 'time': date('2019-09-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '3', 'time': date('2020-09-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '5', 'time': date('2020-06-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '2', 'time': date('2020-08-01T00:00:00.000Z'),
                                                   'positionId': '1',
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '10', 'time': date('2019-09-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '12', 'time': date('2019-09-01T00:00:00.000Z'),
                                                   'type': 'DEAL_TYPE_BUY', 'entryType': 'DEAL_ENTRY_IN'})

        assert storage.deals == [
            {'id': '10', 'time': date('2019-09-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '11', 'time': date('2019-09-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '12', 'time': date('2019-09-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '1', 'time': date('2020-01-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL', 'positionId': '1',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '4', 'time': date('2020-02-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '8', 'time': date('2020-02-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '7', 'time': date('2020-05-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '5', 'time': date('2020-06-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '2', 'time': date('2020-08-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL', 'positionId': '1',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '3', 'time': date('2020-09-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
             'entryType': 'DEAL_ENTRY_IN'},
            {'id': '6', 'time': date('2020-10-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
             'entryType': 'DEAL_ENTRY_IN'}
        ]
        assert storage.get_deals_by_ticket('1') == [{'id': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                                                     'type': 'DEAL_TYPE_SELL', 'positionId': '1',
                                                     'entryType': 'DEAL_ENTRY_IN'}]
        assert storage.get_deals_by_position('1') == [{'id': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                                                       'type': 'DEAL_TYPE_SELL', 'positionId': '1',
                                                       'entryType': 'DEAL_ENTRY_IN'},
                                                      {'id': '2', 'time': date('2020-08-01T00:00:00.000Z'),
                                                       'type': 'DEAL_TYPE_SELL', 'positionId': '1',
                                                       'entryType': 'DEAL_ENTRY_IN'}]
        assert storage.get_deals_by_time_range(date('2020-08-01T00:00:00.000Z'), date('2020-09-01T00:00:00.000Z')) == \
            [{'id': '2', 'time': date('2020-08-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_SELL', 'positionId': '1',
             'entryType': 'DEAL_ENTRY_IN'},
             {'id': '3', 'time': date('2020-09-01T00:00:00.000Z'), 'type': 'DEAL_TYPE_BUY',
              'entryType': 'DEAL_ENTRY_IN'}]

    @pytest.mark.asyncio
    async def test_return_saved_history_orders(self):
        """Should return saved historyOrders."""

        await storage.on_history_order_added('1:ps-mpa-1', {'id': '1', 'positionId': '1',
                                                            'doneTime': date('2020-01-01T00:00:00.000Z'),
                                                            'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '7', 'doneTime': date('2020-05-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '8', 'doneTime': date('2020-02-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '6', 'doneTime': date('2020-10-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '4', 'doneTime': date('2020-02-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '5', 'doneTime': date('2020-06-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '11', 'type': 'ORDER_TYPE_SELL',
                                                            'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '3', 'doneTime': date('2020-09-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '5', 'doneTime': date('2020-06-01T00:00:00.000Z'),
                                             'type': 'ORDER_TYPE_BUY', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '2', 'positionId': '1',
                                                            'doneTime': date('2020-08-01T00:00:00.000Z'),
                                                            'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '10', 'type': 'ORDER_TYPE_SELL',
                                                            'state': 'ORDER_STATE_FILLED'})
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '12', 'type': 'ORDER_TYPE_BUY',
                                                            'state': 'ORDER_STATE_FILLED'})

        assert storage.history_orders == [
            {'id': '10', 'state': 'ORDER_STATE_FILLED', 'type': 'ORDER_TYPE_SELL'},
            {'id': '11', 'state': 'ORDER_STATE_FILLED', 'type': 'ORDER_TYPE_SELL'},
            {'id': '12', 'state': 'ORDER_STATE_FILLED', 'type': 'ORDER_TYPE_BUY'},
            {'id': '1', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-01-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_SELL', 'positionId': '1'},
            {'id': '4', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-02-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_SELL'},
            {'id': '8', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-02-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_SELL'},
            {'id': '7', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-05-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_BUY'},
            {'id': '5', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-06-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_BUY'},
            {'id': '2', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-08-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_SELL', 'positionId': '1'},
            {'id': '3', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-09-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_BUY'},
            {'id': '6', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-10-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_BUY'}]
        assert storage.get_history_orders_by_ticket('1') == [{'id': '1', 'state': 'ORDER_STATE_FILLED',
                                                              'doneTime': date('2020-01-01T00:00:00.000Z'),
                                                              'type': 'ORDER_TYPE_SELL', 'positionId': '1'}]
        assert storage.get_history_orders_by_position('1') == [{'id': '1', 'state': 'ORDER_STATE_FILLED',
                                                                'doneTime': date('2020-01-01T00:00:00.000Z'),
                                                                'type': 'ORDER_TYPE_SELL', 'positionId': '1'},
                                                               {'id': '2', 'state': 'ORDER_STATE_FILLED',
                                                                'doneTime': date('2020-08-01T00:00:00.000Z'),
                                                                'type': 'ORDER_TYPE_SELL', 'positionId': '1'}]
        assert storage.get_history_orders_by_time_range(date('2020-08-01T00:00:00.000Z'),
                                                        date('2020-09-01T00:00:00.000Z')) == [
            {'id': '2', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-08-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_SELL', 'positionId': '1'},
            {'id': '3', 'state': 'ORDER_STATE_FILLED', 'doneTime': date('2020-09-01T00:00:00.000Z'),
             'type': 'ORDER_TYPE_BUY'}]

    @pytest.mark.asyncio
    async def test_return_saved_order_sync_status(self):
        """Should return saved order synchronization status."""

        assert not storage.order_synchronization_finished
        await storage.on_history_orders_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert storage.order_synchronization_finished

    @pytest.mark.asyncio
    async def test_return_saved_deal_sync_status(self):
        """Should return saved deal synchronization status."""

        assert not storage.deal_synchronization_finished
        await storage.on_deals_synchronized('1:ps-mpa-1', 'synchronizationId')
        assert storage.deal_synchronization_finished

    @pytest.mark.asyncio
    async def test_flush_db_when_sync_ends(self):
        """Should flush db when synchronization ends."""
        db.flush = AsyncMock()
        await storage.on_history_order_added('1:ps-mpa-1', {'id': '1', 'positionId': '1',
                                                            'time': date('2020-01-01T00:00:00.000Z'),
                                                            'doneTime': date('2020-01-01T00:00:00.000Z'),
                                                            'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
        await storage.on_deal_added('1:ps-mpa-1', {'id': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                                                   'positionId': '1',
                                                   'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'})
        await storage.on_deals_synchronized('1:ps-mpa-1', 'synchronizationId')
        db.flush.assert_called_with('accountId', 'MetaApi', [
            {'id': '1', 'positionId': '1', 'time': '2020-01-01T00:00:00.000Z',
             'doneTime': '2020-01-01T00:00:00.000Z',
             'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'}], [
            {'id': '1', 'time': '2020-01-01T00:00:00.000Z', 'positionId': '1',
             'type': 'DEAL_TYPE_SELL', 'entryType': 'DEAL_ENTRY_IN'}])

    @pytest.mark.asyncio
    async def test_flush_db(self):
        """Should flush db when new record arrives."""
        with patch('lib.metaApi.memoryHistoryStorage.asyncio.sleep', new=lambda x: sleep(x / 60)):
            await storage.on_deals_synchronized('1:ps-mpa-1', 'synchronizationId')
            db.flush = AsyncMock()
            await storage.on_history_order_added('1:ps-mpa-1', {
                'id': '1', 'positionId': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                'doneTime': date('2020-01-01T00:00:00.000Z'),
                'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
            await sleep(0.1)
            db.flush.assert_called_with('accountId', 'MetaApi', [{
                'id': '1', 'positionId': '1', 'time': '2020-01-01T00:00:00.000Z',
                'doneTime': '2020-01-01T00:00:00.000Z', 'type': 'ORDER_TYPE_SELL',
                'state': 'ORDER_STATE_FILLED'}], [])

    @pytest.mark.asyncio
    async def test_throttle_db_flush(self):
        """Should throttle db flush."""
        with patch('lib.metaApi.memoryHistoryStorage.asyncio.sleep', new=lambda x: sleep(x / 50)):
            await storage.on_deals_synchronized('1:ps-mpa-1', 'synchronizationId')
            db.flush = AsyncMock()
            await storage.on_history_order_added('1:ps-mpa-1', {
                'id': '1', 'positionId': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                'doneTime': date('2020-01-01T00:00:00.000Z'),
                'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
            await sleep(0.1)
            await storage.on_history_order_added('1:ps-mpa-1', {
                'id': '2', 'positionId': '1', 'time': date('2020-01-01T00:00:00.000Z'),
                'doneTime': date('2020-01-01T00:00:00.000Z'),
                'type': 'ORDER_TYPE_SELL', 'state': 'ORDER_STATE_FILLED'})
            await sleep(0.1)
            db.flush.assert_not_called()
