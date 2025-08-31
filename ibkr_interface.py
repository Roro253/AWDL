"""Minimal IBKR interface used for tests and simple order flow.

The real project contains a much more feature rich implementation but the
test-suite only requires a tiny subset of functionality:

* basic connection tracking with a reconnect helper
* the ability to place simple orders driven by strategy signals

This module intentionally keeps the code lightweight so it can be imported in
environments where the official `ibapi` package is not available.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Dict, Optional

from live_strategy_engine import TradingSignal, SignalType


logger = logging.getLogger(__name__)


@dataclass
class Order:
    """Minimal record representing an order sent to IBKR."""

    order_id: int
    symbol: str
    action: str
    quantity: int


class IBKRInterface:
    """Tiny stand in for the full IBKR trading interface.

    Only the pieces that are exercised in the unit tests are implemented.  The
    class tracks whether a connection is active, provides a reconnection helper
    and supports placing very small market orders based on strategy signals.
    """

    def __init__(self, host: str, port: int, client_id: int, **_: object) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id

        # connection state
        self.connected = False
        self._is_connecting = False

        # reconnect handling
        self._reconnect_backoff = 1.0
        self._max_backoff = 60.0
        self._reconnect_timer: Optional[threading.Timer] = None

        # very small order book
        self.next_order_id = 1
        self.orders: Dict[int, Order] = {}

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def connect_and_start(self) -> bool:
        """Pretend to establish a connection to IBKR.

        The real interface performs socket communication and waits for callbacks
        from the gateway.  For the purposes of the tests we simply mark the
        instance as connected.
        """

        if self.connected or self._is_connecting:
            return True

        self._is_connecting = True
        self.connected = True
        self._is_connecting = False
        logger.info("Connected to IBKR (mock)")
        return True

    def disconnect_safe(self) -> None:
        """Mark the interface as disconnected."""

        self.connected = False
        logger.info("Disconnected from IBKR (mock)")

    def schedule_reconnect(self) -> None:
        """Schedule a reconnect attempt with exponential backoff.

        The reconnect test exercises the behaviour where a reconnect request is
        triggered while a previous connection attempt is still in flight.  In
        that case we reschedule the reconnect instead of immediately attempting
        it again.
        """

        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return

        backoff = min(self._reconnect_backoff, self._max_backoff)

        def _reconnect() -> None:
            if self._is_connecting:
                # Still in the middle of a connection attempt; try again later.
                self.schedule_reconnect()
                return

            try:
                self.disconnect_safe()
            finally:
                self.connect_and_start()

        self._reconnect_timer = threading.Timer(backoff, _reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()

        self._reconnect_backoff = min(backoff * 1.5, self._max_backoff)

    # ------------------------------------------------------------------
    # Order handling
    # ------------------------------------------------------------------
    def place_order(self, symbol: str, action: str, quantity: int) -> int:
        """Record a basic market order.

        A real implementation would submit the order to IBKR and update it via
        callbacks.  Here we simply store it in memory and return the order id.
        """

        if not self.connected:
            raise RuntimeError("IBKR interface is not connected")

        order_id = self.next_order_id
        self.next_order_id += 1
        self.orders[order_id] = Order(order_id, symbol, action, quantity)
        logger.info("Placed order %s: %s %s x%s", order_id, action, symbol, quantity)
        return order_id

    def execute_signal(self, signal: TradingSignal, symbol: str = "TSLA") -> Optional[int]:
        """Translate a :class:`TradingSignal` into an order."""

        action_map = {
            SignalType.BUY: "BUY",
            SignalType.SELL: "SELL",
            SignalType.PARTIAL_SELL: "SELL",
        }
        action = action_map.get(signal.signal_type)
        if action is None or signal.quantity <= 0:
            return None
        return self.place_order(symbol, action, signal.quantity)


__all__ = ["IBKRInterface", "Order"]

