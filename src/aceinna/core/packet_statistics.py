import collections
import time


def calculate_collect(last_statistics, success_collection, failure_collection, key, current_time):
    ''' Calculate collect data as statistics
    '''
    received = 0
    crc_failures = 0
    rate = 0
    event_time = current_time

    if key in success_collection:
        received = success_collection[key]['received']

    if key in failure_collection:
        crc_failures = failure_collection[key]

    if last_statistics and key in last_statistics:
        last_received = last_statistics[key]['received']
        diff_received = received - last_received

        event_time = last_statistics[key]['event_time']
        duration = current_time - event_time

        if diff_received == 0 or duration == 0:
            rate = last_statistics[key]['rate']

        if diff_received > 0 and duration > 0:
            rate = round(1 / duration * diff_received, 2)
            event_time = current_time

    calculate_result = {
        'received': received,
        'failures': crc_failures,
        'rate': rate,
        'event_time': event_time
    }

    return calculate_result


class PacketStatistics:
    ''' Packet Statistics Service
    '''
    # {
    #   'z1': Freeze sized Queue,
    #   'pos': Freeze sized Queue,
    # }
    _success_collect_dict = {}
    _failure_collect_dict = {}
    _last_statistics = None
    _last_time = None

    def _get_collect_dict(self, collect_type):
        if collect_type == 'success':
            return self._success_collect_dict

        if collect_type == 'fail':
            return self._failure_collect_dict

        return None

    def _get_packet_types(self):
        packet_types_in_success = self._success_collect_dict.keys()
        packet_types_in_failure = self._failure_collect_dict.keys()
        packet_types = packet_types_in_success

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
            if packet_type not in self._success_collect_dict:
                self._success_collect_dict[packet_type] = {
                    'received': 0,
                    'sampling': collections.deque(maxlen=10)
                }

            self._success_collect_dict[packet_type]['received'] += 1
            self._success_collect_dict[packet_type]['sampling'].append(
                event_time
            )

        if collect_type == 'fail':
            if packet_type not in self._failure_collect_dict:
                self._failure_collect_dict[packet_type] = 0

            self._failure_collect_dict[packet_type] += 1

    def reset(self):
        ''' Reset statistics
        '''
        self._success_collect_dict = {}
        self._failure_collect_dict = {}
        self._last_time = None
    # {
    #   'z1': {'received': 10, 'crc_failures': 1, 'rate': 50},
    #   'z2': {'received': 10, 'crc_failures': 1, 'rate': 50}
    # }

    def get_result(self):
        ''' Get statistics result
        '''
        packet_types = self._get_packet_types()

        if not packet_types:
            return None

        result = {}
        current_time = time.time()
        for key in packet_types:
            statistics_result = calculate_collect(
                self._last_statistics,
                self._success_collect_dict,
                self._failure_collect_dict,
                key,
                current_time
            )
            result[key] = statistics_result

        # diff the last statistics, if no change, return None
        if self._last_statistics == result:
            return None

        self._last_statistics = result

        return result
