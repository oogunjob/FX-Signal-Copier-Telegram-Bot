import asyncio
from typing import Dict, List
from datetime import datetime


class PacketOrderer:
    """Class which orders the synchronization packets."""

    def __init__(self, out_of_order_listener, ordering_timeout_in_seconds: float):
        """Inits the class.

        Args:
            out_of_order_listener: A function which will receive out of order packet events.
            ordering_timeout_in_seconds: Packet ordering timeout.
        """
        self._outOfOrderListener = out_of_order_listener
        self._orderingTimeoutInSeconds = ordering_timeout_in_seconds
        self._isOutOfOrderEmitted = {}
        self._waitListSizeLimit = 100
        self._outOfOrderInterval = None
        self._sequenceNumberByInstance = {}
        self._lastSessionStartTimestamp = {}
        self._packetsByInstance = {}

    def start(self):
        """Initializes the packet orderer"""
        self._sequenceNumberByInstance = {}
        self._lastSessionStartTimestamp = {}
        self._packetsByInstance = {}

        async def emit_events():
            while True:
                await asyncio.sleep(1)
                self._emit_out_of_order_events()

        if not self._outOfOrderInterval:
            self._outOfOrderInterval = asyncio.create_task(emit_events())

    def stop(self):
        """Deinitializes the packet orderer."""
        if self._outOfOrderInterval is not None:
            self._outOfOrderInterval.cancel()
            self._outOfOrderInterval = None

    def restore_order(self, packet: Dict) -> List[Dict]:
        """Processes the packet and resolves in the order of packet sequence number.

        Args:
            packet: Packet to process.

        """
        instance_id = packet['accountId'] + ':' + str(packet['instanceIndex'] if 'instanceIndex' in packet else 0) + \
            ':' + (packet['host'] if 'host' in packet else '0')
        if 'sequenceNumber' not in packet:
            return [packet]
        if packet['type'] == 'synchronizationStarted' and 'synchronizationId' in packet and (
                instance_id not in self._lastSessionStartTimestamp or self._lastSessionStartTimestamp[instance_id] <
                packet['sequenceTimestamp']):
            # synchronization packet sequence just started
            self._isOutOfOrderEmitted[instance_id] = False
            self._sequenceNumberByInstance[instance_id] = packet['sequenceNumber']
            self._lastSessionStartTimestamp[instance_id] = packet['sequenceTimestamp']
            self._packetsByInstance[instance_id] = \
                list(filter(lambda wait_packet: wait_packet['packet']['sequenceTimestamp'] >=
                            packet['sequenceTimestamp'],
                            (self._packetsByInstance[instance_id] if instance_id in
                             self._packetsByInstance else [])))
            return [packet] + self._find_next_packets_from_wait_list(instance_id)
        elif instance_id in self._lastSessionStartTimestamp and \
                packet['sequenceTimestamp'] < self._lastSessionStartTimestamp[instance_id]:
            # filter out previous packets
            return []
        elif instance_id in self._sequenceNumberByInstance and \
                packet['sequenceNumber'] == self._sequenceNumberByInstance[instance_id]:
            # let the duplicate s/n packet to pass through
            return [packet]
        elif instance_id in self._sequenceNumberByInstance and \
                packet['sequenceNumber'] == self._sequenceNumberByInstance[instance_id] + 1:
            # in-order packet was received
            self._sequenceNumberByInstance[instance_id] += 1
            self._lastSessionStartTimestamp[instance_id] = packet['sequenceTimestamp'] if 'sequenceTimestamp' \
                in packet else self._lastSessionStartTimestamp[instance_id]
            return [packet] + self._find_next_packets_from_wait_list(instance_id)
        else:
            # out-of-order packet was received, add it to the wait list
            self._packetsByInstance[instance_id] = self._packetsByInstance[instance_id] \
                if instance_id in self._packetsByInstance else []
            wait_list = self._packetsByInstance[instance_id]
            wait_list.append({
                'instanceId': instance_id,
                'accountId': packet['accountId'],
                'instanceIndex': packet['instanceIndex'] if 'instanceIndex' in packet else 0,
                'sequenceNumber': packet['sequenceNumber'],
                'packet': packet,
                'receivedAt': datetime.now()
            })
            wait_list.sort(key=lambda i: i['sequenceNumber'])
            while len(wait_list) > self._waitListSizeLimit:
                wait_list.pop(0)
            return []

    def on_stream_closed(self, instance_id: str):
        """Resets state for instance id.

        Args:
            instance_id: Instance id to reset state for.
        """
        if instance_id in self._packetsByInstance.keys():
            del self._packetsByInstance[instance_id]
        if instance_id in self._lastSessionStartTimestamp.keys():
            del self._lastSessionStartTimestamp[instance_id]
        if instance_id in self._sequenceNumberByInstance.keys():
            del self._sequenceNumberByInstance[instance_id]

    def on_reconnected(self, reconnect_account_ids: List[str]):
        """Resets state for specified accounts on reconnect.

        Args:
            reconnect_account_ids: Reconnected account ids.
        """
        for instance_id in list(self._packetsByInstance.keys()):
            if self._get_account_id_from_instance(instance_id) in reconnect_account_ids:
                del self._packetsByInstance[instance_id]
        for instance_id in list(self._lastSessionStartTimestamp.keys()):
            if self._get_account_id_from_instance(instance_id) in reconnect_account_ids:
                del self._lastSessionStartTimestamp[instance_id]
        for instance_id in list(self._sequenceNumberByInstance.keys()):
            if self._get_account_id_from_instance(instance_id) in reconnect_account_ids:
                del self._sequenceNumberByInstance[instance_id]

    def _get_account_id_from_instance(self, instance_id: str) -> str:
        return instance_id.split(':')[0]

    def _find_next_packets_from_wait_list(self, instance_id) -> List:
        result = []
        wait_list = self._packetsByInstance[instance_id] if instance_id in self._packetsByInstance else []
        while len(wait_list) and (wait_list[0]['sequenceNumber'] in [
                self._sequenceNumberByInstance[instance_id], self._sequenceNumberByInstance[instance_id] + 1] or
                wait_list[0]['packet']['sequenceTimestamp'] < self._lastSessionStartTimestamp[instance_id]):
            if wait_list[0]['packet']['sequenceTimestamp'] >= self._lastSessionStartTimestamp[instance_id]:
                result.append(wait_list[0]['packet'])
                if wait_list[0]['packet']['sequenceNumber'] == self._sequenceNumberByInstance[instance_id] + 1:
                    self._sequenceNumberByInstance[instance_id] += 1
                    self._lastSessionStartTimestamp[instance_id] = wait_list[0]['packet']['sequenceTimestamp'] if \
                        'sequenceTimestamp' in wait_list[0]['packet'] else self._lastSessionStartTimestamp[instance_id]
            wait_list.pop(0)
        if not len(wait_list) and instance_id in self._packetsByInstance:
            del self._packetsByInstance[instance_id]
        return result

    def _emit_out_of_order_events(self):
        for key, wait_list in self._packetsByInstance.items():
            if len(wait_list) and \
                    (wait_list[0][
                         'receivedAt'].timestamp() + self._orderingTimeoutInSeconds) < datetime.now().timestamp():
                instance_id = wait_list[0]['instanceId']
                if instance_id not in self._isOutOfOrderEmitted or not self._isOutOfOrderEmitted[instance_id]:
                    self._isOutOfOrderEmitted[instance_id] = True
                    # Do not emit onOutOfOrderPacket for packets that come before synchronizationStarted
                    if instance_id in self._sequenceNumberByInstance:
                        asyncio.create_task(self._outOfOrderListener.on_out_of_order_packet(
                            wait_list[0]['accountId'], wait_list[0]['instanceIndex'],
                            self._sequenceNumberByInstance[instance_id] + 1,
                            wait_list[0]['sequenceNumber'], wait_list[0]['packet'], wait_list[0]['receivedAt']))
