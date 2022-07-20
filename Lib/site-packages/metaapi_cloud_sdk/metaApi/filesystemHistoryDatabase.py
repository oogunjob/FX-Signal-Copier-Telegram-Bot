import json
import os
from .models import format_date, convert_iso_time_to_date, string_format_error, MetatraderOrder, MetatraderDeal
from typing import List
from datetime import datetime
from copy import deepcopy
from ..logger import LoggerManager


def stringify(obj: dict or List) -> str:
    """Helper function to convert an object to string and compress.

    Returns:
        Stringified and compressed object.
    """
    return json.dumps(obj).replace('": ', '":').replace('}, {', '},{').replace(', "', ',"')


class FilesystemHistoryDatabase:
    """Provides access to history database stored on filesystem."""

    def __init__(self):
        """Inits the class instance."""
        self._logger = LoggerManager.get_logger('FilesystemHistoryDatabase')

    @staticmethod
    def get_instance():
        """Returns history database instance.

        Returns:
            History database instance.
        """
        global instance
        if not instance:
            instance = FilesystemHistoryDatabase()
        return instance

    async def load_history(self, account_id: str, application: str):
        """Loads history from database.

        Args:
            account_id: Account id.
            application: Application name.

        Returns:
            Full account history.
        """
        paths = await self._get_db_location(account_id, application)
        deals = await self._read_db(account_id, paths['dealsFile'])
        if len(deals) and isinstance(deals[0], list):
            await self.clear(account_id, application)
            deals = []
        for deal in deals:
            convert_iso_time_to_date(deal)

        history_orders = await self._read_db(account_id, paths['historyOrdersFile'])
        if len(history_orders) and isinstance(history_orders[0], list):
            await self.clear(account_id, application)
            history_orders = []
        for history_order in history_orders:
            convert_iso_time_to_date(history_order)

        return {
            'deals': deals,
            'historyOrders': history_orders
        }

    async def clear(self, account_id, application):
        """Removes history from database.

        Args:
            account_id: Account id.
            application: Application name.

        Returns:
            A coroutine resolving when the history is removed.
        """
        paths = await self._get_db_location(account_id, application)
        if os.path.exists(paths['historyOrdersFile']):
            os.remove(paths['historyOrdersFile'])
        if os.path.exists(paths['dealsFile']):
            os.remove(paths['dealsFile'])

    async def flush(self, account_id: str, application: str, new_history_orders: List[MetatraderOrder],
                    new_deals: List[MetatraderDeal]):
        """Flushes the new history to db.

        Args:
            account_id: Account id.
            application: Application name.
            new_history_orders: History orders to save to db.
            new_deals: Deals to save to db.

        Returns:
            A coroutine resolving when the history is flushed.
        """
        paths = await self._get_db_location(account_id, application)
        await self._append_db(paths['historyOrdersFile'], self._prepare_save_data(new_history_orders))
        await self._append_db(paths['dealsFile'], self._prepare_save_data(new_deals))

    async def _get_db_location(self, account_id: str, application: str):
        path = '.metaapi'
        if not os.path.exists(path):
            os.mkdir(path)
        return {
            'dealsFile': path + f'/{account_id}-{application}-deals.bin',
            'historyOrdersFile': path + f'/{account_id}-{application}-historyOrders.bin'
        }

    async def _read_db(self, account_id: str, file: str):
        if not os.path.exists(file):
            return []
        try:
            data = open(file).read()
            lines = data.split('\n')
            result = []
            for line in lines:
                if len(line):
                    result.append(json.loads(line))
            return result
        except Exception as err:
            self._logger.warn(f'{account_id}: failed to read history db, will remove {file} now',
                              string_format_error(err))
            if os.path.exists(file):
                os.remove(file)
            return []

    async def _append_db(self, file, records):
        if records is not None and len(records):
            records = list(map(lambda record: stringify(record) + '\n', records))
            f = open(file, "a+")
            f.write(''.join(records))
            f.close()

    def _prepare_save_data(self, arr: List[dict]):
        arr = deepcopy(arr)

        def convert_dates(item):
            for key in item:
                if isinstance(item[key], datetime):
                    item[key] = format_date(item[key])
                elif isinstance(item[key], dict):
                    convert_dates(item[key])

        for item in arr:
            convert_dates(item)
        return arr


instance = None
