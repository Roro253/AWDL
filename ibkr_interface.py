"""Minimal IBKR interface used for tests and simple order flow.

This module does not talk to Interactive Brokers directly.  It provides a
small subset of functionality needed by the rest of the project and the test
suite: connection state tracking, a reconnection helper and a tiny in-memory
order book.  The real project can replace this file with a full featured
implementation when needed.
"""

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Minimal stand‑ins for the ibapi classes so the rest of the code can import
# this module without the real dependency installed.
# ---------------------------------------------------------------------------


class EWrapper:  # pragma: no cover - simple stub
    pass


class EClient:  # pragma: no cover - simple stub
    def __init__(self, wrapper=None):
        self.wrapper = wrapper


@dataclass
class Contract:
    """Basic stock contract description."""

    symbol: str
    secType: str = "STK"
    exchange: str = "SMART"
    currency: str = "USD"


@dataclass
class Order:
    """Very small order object."""

    action: str
    totalQuantity: int
    orderType: str = "MKT"
    lmtPrice: Optional[float] = None


class OrderStatus(Enum):
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class OrderInfo:
    order_id: int
    symbol: str
    action: str
    quantity: int
    order_type: str
    status: OrderStatus = OrderStatus.SUBMITTED


from live_strategy_engine import TradingSignal, SignalType


class IBKRInterface(EWrapper, EClient):
    """Tiny IBKR interface with reconnect logic."""

    def __init__(self, host: str, port: int, client_id: int, **_: dict):
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.connected = False
        self._is_connecting = False
        self._reconnect_timer: Optional[threading.Timer] = None
        self._reconnect_backoff = 2.0
        self._max_backoff = 60.0
        self.next_order_id = 1
        self.orders: Dict[int, OrderInfo] = {}
        self.order_callback = None

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    def connect_and_start(self) -> bool:
        self.connected = True
        return True

    def disconnect_safe(self):
        self.connected = False

    def schedule_reconnect(self):
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return
        backoff = min(self._reconnect_backoff, self._max_backoff)

        def _reconnect():
            if self._is_connecting:
                self.schedule_reconnect()
                return
            self.disconnect_safe()
            self.connect_and_start()
            self._reconnect_timer = None

        self._reconnect_timer = threading.Timer(backoff, _reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
        self._reconnect_backoff = min(backoff * 1.5, self._max_backoff)

    # ------------------------------------------------------------------
    # Basic order flow helpers
    # ------------------------------------------------------------------
    def create_stock_contract(self, symbol: str) -> Contract:
        return Contract(symbol)

    def create_market_order(self, action: str, quantity: int) -> Order:
        return Order(action=action, totalQuantity=quantity)

    def place_order(self, contract: Contract, order: Order, symbol: str) -> Optional[int]:
        if not self.connected:
            return None
        order_id = self.next_order_id
        self.next_order_id += 1
        info = OrderInfo(order_id, symbol, order.action, order.totalQuantity, order.orderType)
        self.orders[order_id] = info
        if self.order_callback:
            self.order_callback(info)
        return order_id

    def execute_signal(self, signal: TradingSignal, symbol: str = "TSLA") -> Optional[int]:
        if not self.connected:
            return None
        action = "BUY" if signal.signal_type == SignalType.BUY else "SELL"
        contract = self.create_stock_contract(symbol)
        order = self.create_market_order(action, signal.quantity)
        return self.place_order(contract, order, symbol)

    def is_connected(self) -> bool:
        return self.connected
