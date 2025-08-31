"""Minimal IBKR interface used by the trading bot and tests.

This module provides a very small wrapper around the ``ibapi`` client that
supports reconnect logic and basic market order submission.  Only the features
required by the unit tests and the sample trading bot are implemented.
"""

from __future__ import annotations

import threading
from typing import Optional

try:  # pragma: no cover - the tests run without the real IB API installed
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
except Exception:  # pragma: no cover
    # Fallback stubs so the interface can be imported without ``ibapi``.
    class EWrapper:  # type: ignore
        pass

    class EClient:  # type: ignore
        def __init__(self, wrapper: EWrapper | None = None) -> None:
            pass

        def connect(self, host: str, port: int, client_id: int) -> None:
            pass

        def disconnect(self) -> None:
            pass

        def isConnected(self) -> bool:  # noqa: N802 - API matches ibapi
            return False

        def placeOrder(self, oid: int, contract: Contract, order: Order) -> None:
            pass

        def run(self) -> None:
            pass

    class Contract:  # type: ignore
        pass

    class Order:  # type: ignore
        pass


class IBKRInterface(EWrapper, EClient):
    """Very small Interactive Brokers interface.

    The class exposes ``connect_and_start`` and ``schedule_reconnect`` used by
    the unit tests as well as a ``submit_market_order`` helper for the example
    trading bot.  It intentionally omits the large amount of functionality the
    real trading system would normally contain.
    """

    def __init__(self, host: str, port: int, client_id: int, **_: object) -> None:
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)

        self._reader_thread: Optional[threading.Thread] = None
        self._reconnect_timer: Optional[threading.Timer] = None
        self._reconnect_backoff = 2.0
        self._max_backoff = 60.0
        self._is_connecting = False

        self.next_order_id = 1

    # ------------------------------------------------------------------
    # Connection handling
    def connect_and_start(self) -> bool:
        """Connect to TWS/Gateway and start the reader thread."""
        if self.isConnected():
            return True

        self._is_connecting = True
        try:
            self.connect(self.host, self.port, self.client_id)
            self._reader_thread = threading.Thread(target=self.run, daemon=True)
            self._reader_thread.start()
            return True
        finally:
            self._is_connecting = False

    def disconnect_safe(self) -> None:
        """Disconnect if currently connected."""
        if self.isConnected():
            self.disconnect()

    # ------------------------------------------------------------------
    # Reconnect logic used in the unit tests
    def schedule_reconnect(self) -> None:
        """Schedule a reconnect attempt with exponential backoff."""
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return

        backoff = min(self._reconnect_backoff, self._max_backoff)

        def _reconnect() -> None:
            if self._is_connecting:
                # Still connecting; try again later
                self.schedule_reconnect()
                return
            self.disconnect_safe()
            self.connect_and_start()

        self._reconnect_timer = threading.Timer(backoff, _reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
        self._reconnect_backoff = min(backoff * 1.5, self._max_backoff)

    # ibapi callback hooks that trigger reconnection when the network drops
    def connectionClosed(self) -> None:  # pragma: no cover - trivial
        self.schedule_reconnect()

    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson: str = "") -> None:  # noqa: D401,E501 - signature mandated by ibapi  # pragma: no cover
        if errorCode in (1100, 1300, 1301):
            self.schedule_reconnect()

    def nextValidId(self, orderId: int) -> None:  # pragma: no cover - thin wrapper
        self.next_order_id = orderId

    # ------------------------------------------------------------------
    # Basic order submission
    def submit_market_order(self, symbol: str, action: str, quantity: int) -> int:
        """Submit a simple market order and return the order id."""
        contract = Contract()
        setattr(contract, "symbol", symbol)
        setattr(contract, "secType", "STK")
        setattr(contract, "currency", "USD")
        setattr(contract, "exchange", "SMART")

        order = Order()
        setattr(order, "action", action)
        setattr(order, "totalQuantity", quantity)
        setattr(order, "orderType", "MKT")

        oid = self.next_order_id
        self.next_order_id += 1
        self.placeOrder(oid, contract, order)
        return oid


__all__ = ["IBKRInterface"]

