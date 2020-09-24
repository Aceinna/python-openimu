import unittest
from src.aceinna.devices.base import EventBase


class TestEventBase(unittest.TestCase):
    def setUp(self):
        self.reset_event_trigger_flag()

    def reset_event_trigger_flag(self):
        self.event_triggered = 0

    def event_callback(self, *args):
        self.event_triggered = self.event_triggered+1

    def test_single_event(self):
        event_base = EventBase()
        event_base.on('event1', self.event_callback)
        event_base.emit('event1', 'event1')
        self.assertTrue(self.event_triggered == 1, 'Event triggered')

    def test_multi_event(self):
        event_base = EventBase()
        event_base.on('event1', self.event_callback)
        event_base.on('event2', self.event_callback)
        event_base.emit('event1', 'event1')
        event_base.emit('event2', 'event2')

        self.assertTrue(self.event_triggered == 2, 'Event triggered')

    def test_duplicate_bind_event(self):
        event_base = EventBase()
        event_base.on('event1', self.event_callback)
        event_base.on('event1', self.event_callback)

        event_base.emit('event1', 'event1')

        self.assertTrue(self.event_triggered == 2, 'Event triggered')

    def test_non_bind_event(self):
        event_base = EventBase()
        event_base.on('event1', self.event_callback)

        event_base.emit('event2', 'event1')

        self.assertTrue(self.event_triggered == 0, 'Event triggered')
