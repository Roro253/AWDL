"""Minimal IBKR trading interface.

This module provides a very small subset of functionality required by the
unit tests in this kata.  It offers connection state tracking, a simple
reconnect mechanism and a tiny order handling API.  The goal is to mimic the
parts of the real IBKR API that the rest of the project interacts with while
remaining completely self contained – no network connection to Trader Workstation
is attempted during tests.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Optional import of the official IBKR API.  The tests run without a real
# TWS/Gateway connection so dummy stand‑ins are provided when the package is not
# installed.  Only the attributes referenced in this file are created.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - exercised indirectly in CI when ibapi is present
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
except Exception:  # pragma: no cover - handled in environments without ibapi
    class EWrapper:  # type: ignore
        pass

    class EClient:  # type: ignore
        def __init__(self, wrapper: Optional[EWrapper] = None) -> None:
            self.wrapper = wrapper

        def connect(self, host: str, port: int, clientId: int) -> None:
            pass

        def disconnect(self) -> None:
            pass

        def placeOrder(self, orderId: int, contract: "Contract", order: "Order") -> None:
            pass

    class Contract:  # type: ignore
        pass

    class Order:  # type: ignore
        pass


logger = logging.getLogger(__name__)


class IBKRInterface(EWrapper, EClient):
    """Light‑weight wrapper around the IBKR API used in tests.

    Only a fraction of the real interface is implemented.  The focus is on the
    reconnection logic exercised in the test-suite and a minimal order pipeline
    for demonstration purposes.
    """

    def __init__(self, host: str, port: int, client_id: int, **_: object) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)

        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)

        # Connection state ---------------------------------------------------
        self.connected = False
        self._is_connecting = False
        self._reconnect_backoff = 2.0
        self._max_backoff = 60.0
        self._reconnect_timer: Optional[threading.Timer] = None

        # Order tracking -----------------------------------------------------
        self.next_order_id = 1
        self.orders: Dict[int, Dict[str, object]] = {}

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def connect_and_start(self) -> bool:
        """Simulate establishing a connection to TWS/Gateway.

        The real API call is intentionally omitted; tests only require the
        state flags to toggle.  ``True`` is returned to indicate success.
        """

        self._is_connecting = True
        try:
            # In a production environment ``super().connect(...)`` would be
            # called here followed by reader thread start-up.
            self.connected = True
            return True
        finally:
            self._is_connecting = False

    def disconnect_safe(self) -> None:
        """Disconnect from TWS/Gateway if currently connected."""

        if not self.connected:
            return

        try:
            # ``super().disconnect()`` would be called in real usage.
            pass
        finally:
            self.connected = False

    # Reconnection ----------------------------------------------------------
    def schedule_reconnect(self) -> None:
        """Schedule a reconnect attempt with exponential back‑off."""

        # Avoid scheduling multiple timers at once.
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return

        def attempt() -> None:
            # Clear reference so a new timer can be scheduled if required.
            self._reconnect_timer = None

            if self._is_connecting:
                # Connection attempt in progress – try again later.
                self.schedule_reconnect()
                return

            self.disconnect_safe()
            self.connect_and_start()

        self._reconnect_timer = threading.Timer(self._reconnect_backoff, attempt)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()

        # Exponential back‑off with a ceiling.
        self._reconnect_backoff = min(self._reconnect_backoff * 2, self._max_backoff)

    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------
    def nextValidId(self, order_id: int) -> None:  # pragma: no cover - trivial
        """Callback from IBKR supplying the next available order id."""

        self.next_order_id = order_id

    def place_order(self, contract: Contract, order: Order) -> int:
        """Submit an order and return the assigned order id.

        The order is not actually transmitted anywhere but stored locally so
        tests or higher level components can verify that the call happened.
        """

        oid = self.next_order_id
        self.next_order_id += 1
        self.orders[oid] = {"contract": contract, "order": order}

        try:
            # ``super().placeOrder(oid, contract, order)`` would be executed in
            # a fully fledged implementation.  It is deliberately omitted here
            # to keep the module self contained.
            pass
        finally:
            return oid

