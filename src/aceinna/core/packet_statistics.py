import collections
import time


def calculate_collect(packet_collection, failure_collection, key):
    ''' Calculate collect data as statistics
    '''
    received = 0
    crc_failures = 0
    rate = 0

    if key in packet_collection:
        received = packet_collection[key]['received']
        rate = packet_collection[key]['rate']

    if key in failure_collection:
        crc_failures = failure_collection[key]

    calculate_result = {
        'received': received,
        'failures': crc_failures,
        'rate': rate,
        # 'event_time': event_time
    }

    return calculate_result


class PacketStatistics:
    ''' Packet Statistics Service
    '''
    # {
    #   'z1': Freeze sized Queue,
    #   'pos': Freeze sized Queue,
    # }
    _packet_collect_dict = {}
    _failure_collect_dict = {}
    _last_statistics = None
    _last_time = None

    def _get_packet_types(self):
        packet_types_in_success = self._packet_collect_dict.keys()
        packet_types_in_failure = self._failure_collect_dict.keys()
        packet_types = list(packet_types_in_success)

        for packet_type in packet_types_in_failure:
            if packet_type not in packet_types:
                packet_types.append(packet_type)

        if len(packet_types) == 0:
            return None

        return packet_types

    def collect(self, collect_type, packet_type, event_time):
        ''' Collect packet type
        '''
        if collect_type == 'success':
            if packet_type not in self._packet_collect_dict:
                self._packet_collect_dict[packet_type] = {
                    'received': 0,
                    # max calculate 500Hz
                    'sampling': collections.deque(maxlen=500),
                    'rate': 0,
                    'last_calculate_time': event_time,
                }

            self._packet_collect_dict[packet_type]['received'] += 1
            self._packet_collect_dict[packet_type]['sampling'].append(
                event_time
            )

            last_calculate_time = self._packet_collect_dict[packet_type]['last_calculate_time']
            duration = event_time - last_calculate_time

            if duration >= 1:
                count = 0

                try:
                    start = self._packet_collect_dict[packet_type]['sampling'].index(
                        last_calculate_time)
                    end = self._packet_collect_dict[packet_type]['sampling'].index(
                        event_time)
                    count = end - start
                except ValueError:
                    count = 0

                self._packet_collect_dict[packet_type]['rate'] = round(
                    count/duration, 1)

                self._packet_collect_dict[packet_type]['last_calculate_time'] = event_time

        if collect_type == 'fail':
            if packet_type not in self._failure_collect_dict:
                self._failure_collect_dict[packet_type] = 0

            self._failure_collect_dict[packet_type] += 1

    def reset(self):
        ''' Reset statistics
        '''
        for packet_type in self._packet_collect_dict:
            self._packet_collect_dict[packet_type]['received'] = 0
            self._packet_collect_dict[packet_type]['rate'] = 0

        for packet_type in self._failure_collect_dict:
            self._failure_collect_dict[packet_type] = 0

        self._last_time = None

    def get_result(self):
        ''' Get statistics result
        '''
        packet_types = self._get_packet_types()

        if not packet_types:
            return None

        result = {}
        for key in packet_types:
            statistics_result = calculate_collect(
                self._packet_collect_dict,
                self._failure_collect_dict,
                key
            )
            result[key] = statistics_result

        # diff the last statistics, if no change, return None
        if self._last_statistics == result:
            return None

        self._last_statistics = result

        return result
