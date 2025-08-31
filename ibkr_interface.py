"""
IBKR interface: real implementation if ibapi is available, with a
graceful fallback minimal stub to satisfy tests and offline runs.
"""

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional

from live_strategy_engine import TradingSignal, SignalType

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "PENDING"
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
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    timestamp: datetime = None


# Try to import the real IB API
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    IBAPI_AVAILABLE = True
except Exception:
    IBAPI_AVAILABLE = False


class _MinimalInterface:
    """Minimal interface with reconnect scheduling and in-memory orders."""

    def __init__(self, host: str, port: int, client_id: int, **_):
        self.host = host
        self.port = int(port)
        self.client_id = int(client_id)
        self.connected = False
        self._is_connecting = False
        self._reconnect_timer: Optional[threading.Timer] = None
        self.reconnect_delay = 1.0
        self.next_order_id: int = 1
        self.orders: Dict[int, OrderInfo] = {}
        self.order_callback: Optional[Callable[[OrderInfo], None]] = None

    def connect_and_start(self) -> bool:
        if self.connected or self._is_connecting:
            return False
        self._is_connecting = True
        try:
            self.connected = True
            logger.info("[Stub] Marked as connected (no real TWS connection)")
            return True
        finally:
            self._is_connecting = False

    def disconnect_safe(self):
        self.connected = False
        logger.info("[Stub] Disconnected")

    def schedule_reconnect(self):
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return

        def _reconnect():
            if self._is_connecting:
                self.schedule_reconnect()
                return
            self.disconnect_safe()
            self.connect_and_start()

        self._reconnect_timer = threading.Timer(self.reconnect_delay, _reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()

    def create_market_order(self, action: str, quantity: int, symbol: str) -> int:
        oid = self.next_order_id
        self.next_order_id += 1
        info = OrderInfo(
            order_id=oid,
            symbol=symbol,
            action=action,
            quantity=quantity,
            order_type="MKT",
            timestamp=datetime.now(),
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
        )
        self.orders[oid] = info
        if self.order_callback:
            try:
                self.order_callback(info)
            except Exception:
                pass
        return oid

    def execute_signal(self, signal: TradingSignal, symbol: str = "TSLA") -> Optional[int]:
        if not self.connected:
            return None
        if signal.signal_type == SignalType.BUY:
            return self.create_market_order("BUY", signal.quantity, symbol)
        if signal.signal_type in (SignalType.SELL, SignalType.PARTIAL_SELL):
            return self.create_market_order("SELL", signal.quantity, symbol)
        return None


if IBAPI_AVAILABLE:
    class _RealInterface(EWrapper, EClient):
        """Real IBKR interface backed by ibapi."""

        def __init__(self, host: str, port: int, client_id: int, **_):
            EWrapper.__init__(self)
            EClient.__init__(self, wrapper=self)
            self.host = host
            self.port = int(port)
            self.client_id = int(client_id)
            self.connected = False
            self._is_connecting = False
            self._reconnect_timer: Optional[threading.Timer] = None
            self.reconnect_delay = 1.0
            self.next_order_id = 1
            self.order_callback: Optional[Callable[[OrderInfo], None]] = None
            self._reader_thread: Optional[threading.Thread] = None

        # ---------- Connection ----------
        def connect_and_start(self) -> bool:
            if self.connected or self._is_connecting:
                return False
            self._is_connecting = True
            try:
                logger.info("Connecting to IBKR TWS/Gateway at %s:%s (clientId=%s)",
                            self.host, self.port, self.client_id)
                super().connect(self.host, self.port, clientId=self.client_id)
                # Start network reader thread
                if not self._reader_thread or not self._reader_thread.is_alive():
                    self._reader_thread = threading.Thread(target=self.run, daemon=True, name="IBAPI-Reader")
                    self._reader_thread.start()
                self.connected = True
                return True
            except Exception as e:
                logger.error("IBKR connect failed: %s", e)
                self.connected = False
                return False
            finally:
                self._is_connecting = False

        def disconnect_safe(self):
            try:
                if self.isConnected():
                    self.disconnect()
            except Exception:
                pass
            finally:
                self.connected = False

        def schedule_reconnect(self):
            if self._reconnect_timer and self._reconnect_timer.is_alive():
                return

            def _reconnect():
                if self._is_connecting:
                    self.schedule_reconnect()
                    return
                self.disconnect_safe()
                self.connect_and_start()

            self._reconnect_timer = threading.Timer(self.reconnect_delay, _reconnect)
            self._reconnect_timer.daemon = True
            self._reconnect_timer.start()

        # ---------- Orders ----------
        def _stock_contract(self, symbol: str) -> Contract:
            c = Contract()
            c.symbol = symbol
            c.secType = "STK"
            c.exchange = "SMART"
            c.currency = "USD"
            return c

        def _market_order(self, action: str, qty: int) -> Order:
            o = Order()
            o.action = action
            o.orderType = "MKT"
            o.totalQuantity = qty
            return o

        def execute_signal(self, signal: TradingSignal, symbol: str = "TSLA") -> Optional[int]:
            if not self.connected:
                return None
            try:
                oid = self.next_order_id
                self.next_order_id += 1
                action = "BUY" if signal.signal_type == SignalType.BUY else "SELL"
                self.placeOrder(oid, self._stock_contract(symbol), self._market_order(action, signal.quantity))
                return oid
            except Exception as e:
                logger.error("placeOrder failed: %s", e)
                return None

    # Alias to real implementation when ibapi is present
    IBKRInterface = _RealInterface
else:
    # Alias to stub implementation when ibapi is missing
    IBKRInterface = _MinimalInterface
