import os
from typing import Dict, List, Optional
from typing_extensions import TypedDict
import json
import math
from datetime import datetime
import asyncio
import functools
import shutil
from copy import deepcopy
from ...metaApi.models import date, string_format_error
from ..optionsValidator import OptionsValidator
from ...logger import LoggerManager


class PacketLoggerOpts(TypedDict, total=False):
    """Packet logger options."""

    enabled: Optional[bool]
    """Whether packet logger is enabled."""
    fileNumberLimit: Optional[int]
    """Maximum amount of files per account. Default is 12."""
    logFileSizeInHours: Optional[float]
    """Amount of logged hours per account file. Default is 4."""
    compressSpecifications: Optional[bool]
    """Whether to compress specifications packets. Default is true."""
    compressPrices: Optional[bool]
    """Whether to compress price packets. Default is true."""


class PacketLogger:
    """A class which records packets into log files."""

    def __init__(self, opts: PacketLoggerOpts = None):
        """Inits the class.

        Args:
            opts: Packet logger options.
        """
        validator = OptionsValidator()
        opts = opts or {}
        self._fileNumberLimit = validator.validate_non_zero(
            opts['fileNumberLimit'] if 'fileNumberLimit' in opts else None, 12, 'packetLogger.fileNumberLimit')
        self._logFileSizeInHours = validator.validate_non_zero(
            opts['logFileSizeInHours'] if 'logFileSizeInHours' in opts else None, 4, 'packetLogger.logFileSizeInHours')
        self._compressSpecifications = validator.validate_boolean(
            opts['compressSpecifications'] if 'compressSpecifications' in opts else None, True,
            'packetLogger.compressSpecifications')
        self._compressPrices = validator.validate_boolean(
            opts['compressPrices'] if 'compressPrices' in opts else None, True, 'packetLogger.compressPrices')
        self._previousPrices = {}
        self._lastSNPacket = {}
        self._writeQueue = {}
        self._root = './.metaapi/logs'
        self._logger = LoggerManager.get_logger('PacketLogger')
        self._recordInterval: asyncio.Task or None = None
        self._deleteOldLogsInterval: asyncio.Task or None = None
        if not os.path.exists('./.metaapi'):
            os.mkdir('./.metaapi')

        if not os.path.exists(self._root):
            os.mkdir(self._root)

    def _ensure_previous_price_object(self, account_id: str):
        if account_id not in self._previousPrices:
            self._previousPrices[account_id] = {}

    def log_packet(self, packet: Dict):
        """Processes packets and pushes them into save queue.

        Args:
            packet: Packet to log.
        """
        instance_index = packet['instanceIndex'] if 'instanceIndex' in packet else 0
        packet = deepcopy(packet)
        if packet['accountId'] not in self._writeQueue:
            self._writeQueue[packet['accountId']] = {'isWriting': False, 'queue': []}
        if packet['type'] == 'status':
            return
        if packet['accountId'] not in self._lastSNPacket:
            self._lastSNPacket[packet['accountId']] = {}
        if packet['type'] in ['keepalive', 'noop']:
            self._lastSNPacket[packet['accountId']][instance_index] = packet
            return
        queue: List = self._writeQueue[packet['accountId']]['queue']
        if packet['accountId'] not in self._previousPrices:
            self._previousPrices[packet['accountId']] = {}
        prev_price = self._previousPrices[packet['accountId']][instance_index] if \
            instance_index in self._previousPrices[packet['accountId']] else None
        if packet['type'] != 'prices':
            if prev_price is not None:
                self._record_prices(packet['accountId'], instance_index)
            if packet['type'] == 'specifications' and self._compressSpecifications:
                queue.append(json.dumps({'type': packet['type'], 'sequenceNumber': packet['sequenceNumber'] if
                                         'sequenceNumber' in packet else None, 'sequenceTimestamp':
                                         packet['sequenceTimestamp'] if 'sequenceTimestamp' in packet else None,
                                         'instanceIndex': instance_index}))
            else:
                queue.append(json.dumps(packet))
        else:
            if not self._compressPrices:
                queue.append(json.dumps(packet))
            else:
                if prev_price is not None:
                    valid_sequence_numbers = [prev_price['last']['sequenceNumber'],
                                              prev_price['last']['sequenceNumber'] + 1]
                    if instance_index in self._lastSNPacket[packet['accountId']] and 'sequenceNumber' in \
                            self._lastSNPacket[packet['accountId']][instance_index]:
                        valid_sequence_numbers.append(
                            self._lastSNPacket[packet['accountId']][instance_index]['sequenceNumber'] + 1)
                    if packet['sequenceNumber'] not in valid_sequence_numbers:
                        self._record_prices(packet['accountId'], instance_index)
                        self._ensure_previous_price_object(packet['accountId'])
                        self._previousPrices[packet['accountId']][instance_index] = {'first': packet, 'last': packet}
                        queue.append(json.dumps(packet))
                    else:
                        self._previousPrices[packet['accountId']][instance_index]['last'] = packet
                else:
                    if 'sequenceNumber' in packet:
                        self._ensure_previous_price_object(packet['accountId'])
                        self._previousPrices[packet['accountId']][instance_index] = {'first': packet, 'last': packet}
                    queue.append(json.dumps(packet))

    async def read_logs(self, account_id: str, date_after: datetime = None, date_before: datetime = None):
        """Returns log messages within date bounds as an array of objects.

        Args:
            account_id: Account id.
            date_after: Date to get logs after.
            date_before: Date to get logs before.
        """
        folders = os.listdir(self._root)
        folders.sort()
        packets = []
        for folder in folders:
            file_path = f'{self._root}/{folder}/{account_id}.log'
            if os.path.exists(file_path):
                contents = open(file_path, "r").readlines()
                messages = list(map(lambda message: {'date': date(message[1:24]), 'message':
                                    message[26:].replace('\n', '')}, contents))
                if date_after:
                    messages = list(filter(lambda message: message['date'] > date_after, messages))
                if date_before:
                    messages = list(filter(lambda message: message['date'] < date_before, messages))
                packets += messages
        return packets

    def get_file_path(self, account_id) -> str:
        """Returns path for account log file.

        Args:
            account_id: Account id.

        Returns:
            File path.
        """
        file_index = math.floor(datetime.now().hour / self._logFileSizeInHours)
        folder_name = f'{datetime.now().strftime("%Y-%m-%d")}-{file_index if file_index > 9 else "0" + str(file_index)}'
        if not os.path.exists(f'{self._root}/{folder_name}'):
            os.mkdir(f'{self._root}/{folder_name}')
        return f'{self._root}/{folder_name}/{account_id}.log'

    def start(self):
        """Initializes the packet logger."""
        self._previousPrices = {}

        async def record_job():
            while True:
                await asyncio.sleep(1)
                await self._append_logs()

        async def delete_old_data_job():
            while True:
                await asyncio.sleep(10)
                await self._delete_old_data()

        if not self._recordInterval:
            self._recordInterval = asyncio.create_task(record_job())
            self._deleteOldLogsInterval = asyncio.create_task(delete_old_data_job())

    def stop(self):
        """Deinitializes the packet logger."""
        self._recordInterval.cancel()
        self._recordInterval = None
        self._deleteOldLogsInterval.cancel()
        self._deleteOldLogsInterval = None

    def _record_prices(self, account_id: str, instance_number: int):
        """Records price packet messages to log files.

        Args:
            account_id: Account id.
        """
        prev_price = self._previousPrices[account_id][instance_number] if instance_number \
            in self._previousPrices[account_id] else {'first': {}, 'last': {}}
        queue = self._writeQueue[account_id]['queue']
        del self._previousPrices[account_id][instance_number]
        if not len(self._previousPrices[account_id].keys()):
            del self._previousPrices[account_id]
        if prev_price['first']['sequenceNumber'] != prev_price['last']['sequenceNumber']:
            queue.append(json.dumps(prev_price['last']))
            queue.append(f'Recorded price packets {prev_price["first"]["sequenceNumber"]}'
                         f'-{prev_price["last"]["sequenceNumber"]}, instanceIndex: {instance_number}')

    async def _append_logs(self):
        """Writes logs to files."""
        for account_id in self._writeQueue:
            queue = self._writeQueue[account_id]
            if (not queue['isWriting']) and len(queue['queue']):
                queue['isWriting'] = True
                try:
                    file_path = self.get_file_path(account_id)
                    write_string = functools.reduce(
                        lambda a, b: a + f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}] {b}\r',
                        queue['queue'], '')
                    queue['queue'] = []
                    f = open(file_path, "a+")
                    f.write(write_string)
                    f.close()
                except Exception as err:
                    self._logger.error(f'{account_id}: Failed to record packet log ' + string_format_error(err))
                queue['isWriting'] = False

    async def _delete_old_data(self):
        """Deletes folders when the folder limit is exceeded."""
        contents = os.listdir(self._root)
        contents.sort()
        for folder_name in list(reversed(contents))[self._fileNumberLimit:]:
            shutil.rmtree(f'{self._root}/{folder_name}')
