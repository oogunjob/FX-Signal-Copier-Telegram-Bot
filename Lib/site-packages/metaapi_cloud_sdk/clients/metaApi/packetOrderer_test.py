from .packetOrderer import PacketOrderer
import pytest
import asyncio
from mock import MagicMock, patch
from datetime import datetime

out_of_order_listener = MagicMock()
packet_orderer = PacketOrderer(out_of_order_listener, 0.5)
date = datetime.fromtimestamp(1000000000)


@pytest.fixture(autouse=True)
async def run_around_tests():
    global packet_orderer
    packet_orderer = PacketOrderer(out_of_order_listener, 0.5)
    packet_orderer.start()
    yield
    packet_orderer.stop()


class TestPacketOrderer:
    @pytest.mark.asyncio
    async def test_no_sequence_number(self):
        """Should return packets without a sequence number out immediately."""
        packet_without_sn = {
            'type': 'authenticated',
            'connectionId': 'accountId',
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(packet_without_sn) == [packet_without_sn]

    @pytest.mark.asyncio
    async def test_restore(self):
        """Should restore packet order."""
        first_packet = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267178,
            'sequenceNumber': 13,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124267180,
            'sequenceNumber': 14,
            'accountId': 'accountId'
        }
        third_packet = {
            'type': 'accountInformation',
            'sequenceTimestamp': 1603124267187,
            'sequenceNumber': 15,
            'accountId': 'accountId'
        }
        fourth_packet = {
            'type': 'positions',
            'sequenceTimestamp': 1603124267188,
            'sequenceNumber': 16,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(second_packet) == []
        assert packet_orderer.restore_order(first_packet) == [first_packet, second_packet]
        assert packet_orderer.restore_order(fourth_packet) == []
        assert packet_orderer.restore_order(third_packet) == [third_packet, fourth_packet]

    @pytest.mark.asyncio
    async def test_filter_prev_sync_packets_with_specifications(self):
        """Should filter out packets from previous synchronization attempt that includes synchronization start."""
        previous_start = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267178,
            'sequenceNumber': 13,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        one_of_previous_packets = {
            'type': 'positions',
            'sequenceTimestamp': 1603124267188,
            'sequenceNumber': 15,
            'accountId': 'accountId'
        }
        this_specifications = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267198,
            'sequenceNumber': 1,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        this_second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124268198,
            'sequenceNumber': 2,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(previous_start) == [previous_start]
        assert packet_orderer.restore_order(one_of_previous_packets) == []
        assert packet_orderer.restore_order(this_second_packet) == []
        assert packet_orderer.restore_order(this_specifications) == [this_specifications, this_second_packet]

    @pytest.mark.asyncio
    async def test_filter_prev_sync_packets_without_specifications(self):
        """Should filter out packets from previous synchronization attempt that does not includes the start."""
        one_of_previous_packets = {
            'type': 'positions',
            'sequenceTimestamp': 1603124267188,
            'sequenceNumber': 15,
            'accountId': 'accountId'
        }
        this_start = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267198,
            'sequenceNumber': 1,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        this_second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124268198,
            'sequenceNumber': 2,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(one_of_previous_packets) == []
        assert packet_orderer.restore_order(this_second_packet) == []
        assert packet_orderer.restore_order(this_start) == [this_start, this_second_packet]

    @pytest.mark.asyncio
    async def test_duplicate(self):
        """Should pass through duplicate packets."""
        specifications_packet = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267198,
            'sequenceNumber': 16,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124268198,
            'sequenceNumber': 17,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(specifications_packet) == [specifications_packet]
        assert packet_orderer.restore_order(second_packet) == [second_packet]
        assert packet_orderer.restore_order(second_packet) == [second_packet]

    @pytest.mark.asyncio
    async def test_return_in_order(self):
        """Should return in-order packets immediately."""
        first_packet = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267178,
            'sequenceNumber': 13,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124267180,
            'sequenceNumber': 14,
            'accountId': 'accountId'
        }
        third_packet = {
            'type': 'accountInformation',
            'sequenceTimestamp': 1603124267187,
            'sequenceNumber': 15,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(first_packet) == [first_packet]
        assert packet_orderer.restore_order(second_packet) == [second_packet]
        assert packet_orderer.restore_order(third_packet) == [third_packet]

    @pytest.mark.asyncio
    async def test_call_out_of_order_once(self):
        """Should call on-out-of-order listener only once per synchronization attempt."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        first_packet = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267178,
            'sequenceNumber': 13,
            'synchronizationId': 'synchronizationId',
            'accountId': 'accountId'
        }
        third_packet = {
            'type': 'orders',
            'sequenceTimestamp': 1603124267193,
            'sequenceNumber': 15,
            'accountId': 'accountId'
        }
        assert packet_orderer.restore_order(first_packet) == [first_packet]
        assert packet_orderer.restore_order(third_packet) == []
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_called_once()
        args_list = out_of_order_listener.on_out_of_order_packet.call_args_list[0].args
        assert args_list[0] == 'accountId'
        assert args_list[1] == 0
        assert args_list[2] == 14
        assert args_list[3] == 15
        assert args_list[4] == third_packet
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_out_of_order_if_timeout(self):
        """Should call on-out-of-order listener if the first packet in wait list is timed out."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 11,
            'packet': {},
            'receivedAt': date
        }
        not_timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 15,
            'packet': {},
            'receivedAt': datetime.fromtimestamp(10000000000)
        }
        packet_orderer._sequenceNumberByInstance['accountId:0:ps-mpa-1'] = 1
        packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'] = [
            timed_out_packet,
            not_timed_out_packet
        ]
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_called_once()
        args_list = out_of_order_listener.on_out_of_order_packet.call_args_list[0].args
        assert args_list[0] == 'accountId'
        assert args_list[1] == 0
        assert args_list[2] == 2
        assert args_list[3] == 11
        assert args_list[4] == timed_out_packet['packet']
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_called_once()

    @pytest.mark.asyncio
    async def test_not_call_out_of_order_if_not_timeout(self):
        """Should not call on-out-of-order listener if the first packet in wait list is not timed out."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        timed_out_packet = {
            'accountId': 'accountId',
            'sequenceNumber': 11,
            'packet': {},
            'receivedAt': date
        }
        not_timed_out_packet = {
            'accountId': 'accountId',
            'sequenceNumber': 15,
            'packet': {},
            'receivedAt': datetime.fromtimestamp(10000000000)
        }
        packet_orderer._sequenceNumberByInstance['accountId:0'] = 1
        packet_orderer._packetsByInstance['accountId:0'] = [
            not_timed_out_packet,
            timed_out_packet
        ]
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_call_out_of_order_if_before_sync_start(self):
        """Should not call on-out-of-order listener for packets that come before synchronization start."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        out_of_order_packet = {
            'accountId': 'accountId',
            'sequenceNumber': 11,
            'packet': {},
            'receivedAt': date
        }

        # There were no synchronization start packets
        if 'accountId' in packet_orderer._sequenceNumberByInstance:
            del packet_orderer._sequenceNumberByInstance['accountId:0']

        packet_orderer._packetsByInstance['accountId:0'] = [out_of_order_packet]
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_not_called()

    @pytest.mark.asyncio
    async def test_maintain_fixed_queue(self):
        """Should maintain a fixed queue of wait list."""
        packet_orderer._waitListSizeLimit = 1
        second_packet = {
            'type': 'prices',
            'sequenceTimestamp': 1603124267180,
            'sequenceNumber': 14,
            'accountId': 'accountId',
            'host': 'ps-mpa-1'
        }
        third_packet = {
            'type': 'accountInformation',
            'sequenceTimestamp': 1603124267187,
            'sequenceNumber': 15,
            'accountId': 'accountId',
            'host': 'ps-mpa-1'
        }
        packet_orderer.restore_order(second_packet)
        assert len(packet_orderer._packetsByInstance['accountId:0:ps-mpa-1']) == 1
        assert packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'][0]['packet'] == second_packet
        packet_orderer.restore_order(third_packet)
        assert len(packet_orderer._packetsByInstance['accountId:0:ps-mpa-1']) == 1
        assert packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'][0]['packet'] == third_packet

    @pytest.mark.asyncio
    async def test_count_start_packets_with_no_sync_id_as_out_of_order(self):
        """Should count start packets with undefined synchronziationId as out-of-order."""
        start_packet = {
            'type': 'synchronizationStarted',
            'sequenceTimestamp': 1603124267198,
            'sequenceNumber': 16,
            'accountId': 'accountId',
            'host': 'ps-mpa-1'
        }
        assert packet_orderer.restore_order(start_packet) == []
        assert len(packet_orderer._packetsByInstance['accountId:0:ps-mpa-1']) == 1
        assert packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'][0]['packet'] == start_packet

    @pytest.mark.asyncio
    async def test_reset_on_reconnected(self):
        """Should reset state on reconnected event."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 11,
            'packet': {},
            'receivedAt': date
        }
        not_timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 15,
            'packet': {},
            'receivedAt': datetime.fromtimestamp(10000000000)
        }
        packet_orderer._sequenceNumberByInstance['accountId:0:ps-mpa-1'] = 1
        packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'] = [
            timed_out_packet,
            not_timed_out_packet
        ]
        packet_orderer.on_reconnected(['accountId'])
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_not_called()

    @pytest.mark.asyncio
    async def test_reset_on_stream_closed(self):
        """Should reset state for an instance on stream closed event."""
        out_of_order_listener.on_out_of_order_packet = MagicMock()
        timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 11,
            'packet': {},
            'receivedAt': date
        }
        not_timed_out_packet = {
            'accountId': 'accountId',
            'instanceId': 'accountId:0:ps-mpa-1',
            'host': 'ps-mpa-1',
            'instanceIndex': 0,
            'sequenceNumber': 15,
            'packet': {},
            'receivedAt': datetime.fromtimestamp(10000000000)
        }
        packet_orderer._sequenceNumberByInstance['accountId:0:ps-mpa-1'] = 1
        packet_orderer._packetsByInstance['accountId:0:ps-mpa-1'] = [
            timed_out_packet,
            not_timed_out_packet
        ]
        packet_orderer.on_stream_closed('accountId:0:ps-mpa-1')
        await asyncio.sleep(1)
        out_of_order_listener.on_out_of_order_packet.assert_not_called()
