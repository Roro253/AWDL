import os
import sys
import threading

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ibkr_interface import IBKRInterface


def test_reconnect_defers_during_connect():
    interface = IBKRInterface('host', 1, 1)
    calls = {'disconnect': 0, 'connect': 0}

    def fake_disconnect():
        calls['disconnect'] += 1

    def fake_connect():
        calls['connect'] += 1

    interface.disconnect_safe = fake_disconnect
    interface.connect_and_start = fake_connect

    callbacks = []

    class FakeTimer:
        def __init__(self, interval, func):
            self.interval = interval
            self.func = func
            self.daemon = True
        def start(self):
            callbacks.append(self.func)
        def is_alive(self):
            return False

    original_timer = threading.Timer
    threading.Timer = FakeTimer
    try:
        interface._is_connecting = True
        interface.schedule_reconnect()
        # first scheduled reconnect while still connecting
        callbacks.pop(0)()
        assert calls['connect'] == 0
        assert calls['disconnect'] == 0
        # simulate connection attempt finished
        interface._is_connecting = False
        callbacks.pop(0)()
        assert calls['connect'] == 1
        assert calls['disconnect'] == 1
        assert callbacks == []
    finally:
        threading.Timer = original_timer
