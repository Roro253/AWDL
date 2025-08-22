"""
Interactive Brokers (IBKR) Trading Interface
Handles order execution and portfolio management for the TSLA trading bot
"""

import os
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
import logging
from dataclasses import dataclass
from enum import Enum
import queue

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 7496  # 7497 for paper trading
DEFAULT_CLIENT_ID = 1

# IBKR API imports
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.order import Order
    from ibapi.execution import Execution
    from ibapi.commission_report import CommissionReport
    from ibapi.common import OrderId, TickerId
except ImportError:
    print("Warning: IBKR API not installed. Install with: pip install ibapi")
    # Create dummy classes for development
    class EClient:
        def isConnected(self):
            return False

    class EWrapper: pass
    class Contract: pass
    class Order: pass
    class Execution: pass
    class CommissionReport: pass
    OrderId = int
    TickerId = int

from live_strategy_engine import TradingSignal, SignalType
from trade_logging import TradeRecord

logger = logging.getLogger("ibkr_interface")

DEFAULT_HOST = os.getenv("IBKR_HOST", "127.0.0.1")
# 7496=LIVE TWS, 7497=PAPER TWS
DEFAULT_PORT = int(os.getenv("IBKR_PORT", "7497"))
DEFAULT_CLIENT_ID = int(os.getenv("IBKR_CLIENT_ID", "1"))

class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class OrderInfo:
    """Order information tracking"""
    order_id: int
    symbol: str
    action: str  # BUY/SELL
    quantity: int
    order_type: str  # MKT/LMT/STP
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_fill_price: float = 0.0
    timestamp: datetime = None
    commission: float = 0.0

@dataclass
class PortfolioPosition:
    """Portfolio position information"""
    symbol: str
    position: int
    market_price: float
    market_value: float
    avg_cost: float
    unrealized_pnl: float
    realized_pnl: float

class IBKRInterface(EWrapper, EClient):
    """IBKR Trading Application with resilient connection handling"""

    def __init__(
        self,
        parent=None,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        client_id: int = DEFAULT_CLIENT_ID,
    ):
        EWrapper.__init__(self)
        EClient.__init__(self, wrapper=self)
        self.parent = parent
 codex/persist-settings-and-improve-reconnect-logic

        # Persisted connection settings
        self.host = host
        self.port = port
        self.client_id = client_id

        self._reconnect_backoff = 2.0  # seconds
        self._max_backoff = 60.0
        self._reconnect_timer = None
        self._connected_once = False


        
        # Connection settings
        self.host = DEFAULT_HOST
        self.port = DEFAULT_PORT
        self.client_id = DEFAULT_CLIENT_ID
        
 main
        # Order management
        self.next_order_id = None
        self.orders: Dict[int, OrderInfo] = {}
        self.order_queue = queue.Queue()

        # Portfolio tracking
        self.portfolio_positions: Dict[str, PortfolioPosition] = {}
        self.account_value = 0.0
        self.buying_power = 0.0

        # Connection status
        self.connected = False
        self.connection_lock = threading.Lock()

        # Callbacks
        self.order_callback: Optional[Callable] = None
        self.position_callback: Optional[Callable] = None
 codex/persist-settings-and-improve-reconnect-logic

        
    def connect_to_ibkr(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        client_id: int = DEFAULT_CLIENT_ID,
    ) -> bool:
        """Connect to IBKR TWS or Gateway"""
        try:
            # Prevent reconnect attempts if already connected
            if self.connected or self.isConnected():
                logger.info("Already connected to IBKR")
                return True
 main

    # ---- connection lifecycle ----

    def connect_and_start(self):
        """Public entry: connect and request live market data type."""
        self.connect_safe()

    def connect_safe(self):
        if not isinstance(self.host, str) or not self.host:
            logger.error(
                "IBKR host is invalid or missing (got %r). Set IBKR_HOST env or config.",
                self.host,
            )
            return
        if not isinstance(self.port, int):
            try:
                self.port = int(self.port)
            except Exception:
                logger.error(
                    "IBKR port is invalid or missing (got %r). Set IBKR_PORT env or config.",
                    self.port,
                )
                return

        logger.info(
            "Connecting to IBKR at %s:%s with client ID %s",
            self.host,
            self.port,
            self.client_id,
        )
        try:
            super().connect(self.host, self.port, self.client_id)
            self._connected_once = True
        except Exception as e:
            logger.error("Exception starting socket to IBKR: %s", e)
            self.schedule_reconnect()
            return

        thread = threading.Thread(target=self.run, name="IBKR-Reader", daemon=True)
        thread.start()

    def schedule_reconnect(self):
        if self._reconnect_timer and self._reconnect_timer.is_alive():
            return

        backoff = min(self._reconnect_backoff, self._max_backoff)
        logger.warning("IBKR connection lost. Attempting to reconnect in %.1fs...", backoff)

        def _reconnect():
            try:
                self.disconnect_safe()
            except Exception:
                pass
            self.connect_safe()

        self._reconnect_timer = threading.Timer(backoff, _reconnect)
        self._reconnect_timer.daemon = True
        self._reconnect_timer.start()
        self._reconnect_backoff = min(backoff * 1.5, self._max_backoff)

    def disconnect_safe(self):
        try:
            if self.isConnected():
                self.disconnect()
                logger.info("Connection to IBKR closed")
        except Exception as e:
            logger.debug("disconnect_safe exception: %s", e)
        finally:
            self.connected = False

    # ---- ibapi callbacks ----

    def connectAck(self):
        super().connectAck()
        logger.info("Connection acknowledged by IBKR")
        self.connected = True
        try:
            self.reqMarketDataType(1)
            logger.info("Requested live market data subscription")
            self.reqIds(-1)
        except Exception as e:
            logger.error("Failed to request market data type / IDs: %s", e)

    def connectionClosed(self):
        logger.warning("IBKR reports connectionClosed()")
        self.connected = False
        self.schedule_reconnect()

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        if errorCode in (1100, 1101, 1102):
            logger.warning("TWS connectivity event %s: %s", errorCode, errorString)
        elif errorCode in (10167,):
            logger.warning("Market data farm connection is OK: %s", errorString)
        else:
            logger.error("IB error: reqId=%s code=%s msg=%s", reqId, errorCode, errorString)
        if errorCode in (1100, 1300, 1301):
            self.schedule_reconnect()
    
    def nextValidId(self, orderId: OrderId):
        """Receive next valid order ID"""
        self.next_order_id = orderId
        logger.info(f"Next valid order ID: {orderId}")
    
    def orderStatus(self, orderId: OrderId, status: str, filled: float, 
                   remaining: float, avgFillPrice: float, permId: int,
                   parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        """Order status update"""
        if orderId in self.orders:
            order_info = self.orders[orderId]
            order_info.status = OrderStatus(status) if status in [s.value for s in OrderStatus] else OrderStatus.PENDING
            order_info.filled_quantity = int(filled)
            order_info.avg_fill_price = avgFillPrice
            
            logger.info(f"Order {orderId} status: {status}, filled: {filled}, avg price: {avgFillPrice}")
            
            # Notify callback if order is filled
            if status == "Filled" and self.order_callback:
                self.order_callback(order_info)
    
    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        """Execution details"""
        logger.info(f"Execution: {execution.execId} - {execution.shares} shares at ${execution.price}")
        side = "BUY" if execution.side.upper() == "BOT" else "SELL"
        if self.parent and getattr(self.parent, "csv_logger", None):
            rec = TradeRecord(
                ts_utc=None,
                ts_local=None,
                session_id=getattr(self.parent, "session_id", None),
                symbol=contract.symbol,
                side=side,
                qty=int(execution.shares),
                price=float(execution.price),
                order_id=str(execution.orderId),
                trade_id=str(execution.execId),
                tags="live",
            )
            self.parent.csv_logger.log_trade(rec)
    
    def commissionReport(self, commissionReport: CommissionReport):
        """Commission report"""
        logger.info(f"Commission: ${commissionReport.commission}")
    
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Position update"""
        symbol = contract.symbol
        if symbol not in self.portfolio_positions:
            self.portfolio_positions[symbol] = PortfolioPosition(
                symbol=symbol,
                position=int(position),
                market_price=0.0,
                market_value=0.0,
                avg_cost=avgCost,
                unrealized_pnl=0.0,
                realized_pnl=0.0
            )
        else:
            self.portfolio_positions[symbol].position = int(position)
            self.portfolio_positions[symbol].avg_cost = avgCost

        logger.info(f"Position update: {symbol} - {position} shares at avg cost ${avgCost}")
        if self.position_callback:
            try:
                self.position_callback(self.portfolio_positions[symbol])
            except Exception as e:
                logger.error(f"Error in position callback: {e}")
    
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Account summary update"""
        if tag == "TotalCashValue":
            self.account_value = float(value)
        elif tag == "BuyingPower":
            self.buying_power = float(value)
        
        logger.debug(f"Account {tag}: {value} {currency}")
    
    # Trading methods
    def create_stock_contract(self, symbol: str, exchange: str = "SMART") -> Contract:
        """Create stock contract"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = "USD"
        return contract
    
    def create_market_order(self, action: str, quantity: int) -> Order:
        """Create market order"""
        order = Order()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        return order
    
    def create_limit_order(self, action: str, quantity: int, price: float) -> Order:
        """Create limit order"""
        order = Order()
        order.action = action
        order.orderType = "LMT"
        order.totalQuantity = quantity
        order.lmtPrice = price
        return order
    
    def create_stop_order(self, action: str, quantity: int, stop_price: float) -> Order:
        """Create stop order"""
        order = Order()
        order.action = action
        order.orderType = "STP"
        order.totalQuantity = quantity
        order.auxPrice = stop_price
        return order
    
    def place_order(self, contract: Contract, order: Order, symbol: str) -> Optional[int]:
        """Place order with IBKR"""
        if not self.connected or self.next_order_id is None:
            logger.error("Not connected to IBKR or no valid order ID")
            return None
        
        try:
            order_id = self.next_order_id
            self.next_order_id += 1
            
            # Track order
            order_info = OrderInfo(
                order_id=order_id,
                symbol=symbol,
                action=order.action,
                quantity=order.totalQuantity,
                order_type=order.orderType,
                price=getattr(order, 'lmtPrice', None),
                timestamp=datetime.now()
            )
            self.orders[order_id] = order_info
            
            # Place order
            self.placeOrder(order_id, contract, order)
            logger.info(f"Placed {order.action} order for {order.totalQuantity} {symbol} (Order ID: {order_id})")
            
            return order_id
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel order"""
        try:
            self.cancelOrder(order_id)
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Cancelled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def execute_signal(self, signal: TradingSignal, symbol: str = "TSLA") -> Optional[int]:
        """Execute trading signal"""
        if not self.connected:
            logger.error("Not connected to IBKR")
            return None
        
        try:
            contract = self.create_stock_contract(symbol)
            
            if signal.signal_type == SignalType.BUY:
                order = self.create_market_order("BUY", signal.quantity)
                logger.info(f"Executing BUY signal: {signal.quantity} shares of {symbol}")
                
            elif signal.signal_type in [SignalType.SELL, SignalType.PARTIAL_SELL]:
                order = self.create_market_order("SELL", signal.quantity)
                logger.info(f"Executing SELL signal: {signal.quantity} shares of {symbol}")
                
            else:
                logger.warning(f"Unknown signal type: {signal.signal_type}")
                return None
            
            return self.place_order(contract, order, symbol)
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return None
    
    def get_position(self, symbol: str) -> Optional[PortfolioPosition]:
        """Get current position for symbol"""
        return self.portfolio_positions.get(symbol)
    
    def get_account_info(self) -> Dict[str, any]:
        """Get account information"""
        return {
            'account_value': self.account_value,
            'buying_power': self.buying_power,
            'connected': self.connected,
            'positions': {symbol: {
                'position': pos.position,
                'avg_cost': pos.avg_cost,
                'market_value': pos.market_value,
                'unrealized_pnl': pos.unrealized_pnl
            } for symbol, pos in self.portfolio_positions.items()}
        }
    
    def request_portfolio_updates(self):
        """Request portfolio and account updates"""
        if self.connected:
            logger.info("Requesting portfolio and account updates")
            self.reqPositions()
            self.reqAccountSummary(9001, "All", "TotalCashValue,BuyingPower")
    
    def set_callbacks(self, order_callback: Callable = None, position_callback: Callable = None):
        """Set callback functions for order and position updates"""
        self.order_callback = order_callback
        self.position_callback = position_callback

class IBKRManager:
    """High-level IBKR manager for the trading bot"""

    def __init__(self, csv_logger=None, session_id: str = None):
        self.csv_logger = csv_logger
        self.session_id = session_id
        self.app = IBKRInterface(parent=self)
        self.running = False

    def start(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, client_id: int = DEFAULT_CLIENT_ID) -> bool:
        """Start IBKR connection"""
        try:
            self.app.host = host
            self.app.port = port
            self.app.client_id = client_id

            self.app.connect_and_start()

            timeout = 10
            start_time = time.time()
            while not self.app.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)

            if not self.app.connected:
                logger.error("IBKR connection not established")
                return False

            self.app.request_portfolio_updates()
            self.running = True
            logger.info("IBKR Manager started successfully")
            return True

        except Exception as e:
            logger.error(f"Error starting IBKR Manager: {e}")
            return False

    def stop(self):
        """Stop IBKR connection"""
        try:
            self.running = False
            self.app.disconnect_safe()
            logger.info("IBKR Manager stopped")

        except Exception as e:
            logger.error(f"Error stopping IBKR Manager: {e}")

    def execute_signal(self, signal: TradingSignal) -> bool:
        """Execute trading signal"""
        if not self.running or not self.app.connected:
            logger.error("IBKR not connected")
            return False

        order_id = self.app.execute_signal(signal)
        return order_id is not None

    def get_position(self, symbol: str = "TSLA") -> Optional[PortfolioPosition]:
        """Get current position"""
        return self.app.get_position(symbol)

    def get_account_info(self) -> Dict[str, any]:
        """Get account information"""
        return self.app.get_account_info()

    def is_connected(self) -> bool:
        """Check if connected to IBKR"""
        return self.app.connected

def test_ibkr_connection():
    """Test IBKR connection"""
    print("Testing IBKR connection...")
    
    manager = IBKRManager()
    
    try:
        # Start connection (paper trading port)
        if manager.start(port=7496):
            print("✓ Connected to IBKR successfully")
            
            # Get account info
            account_info = manager.get_account_info()
            print(f"✓ Account value: ${account_info['account_value']:,.2f}")
            print(f"✓ Buying power: ${account_info['buying_power']:,.2f}")
            
            # Check TSLA position
            position = manager.get_position("TSLA")
            if position:
                print(f"✓ TSLA position: {position.position} shares")
            else:
                print("✓ No TSLA position")
            
        else:
            print("✗ Failed to connect to IBKR")
            print("Make sure TWS or Gateway is running on port 7496")
            
    except Exception as e:
        print(f"✗ Error testing IBKR: {e}")
        
    finally:
        manager.stop()

if __name__ == "__main__":
    test_ibkr_connection()

