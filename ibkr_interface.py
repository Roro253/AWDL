"""
Interactive Brokers (IBKR) Trading Interface
Handles order execution and portfolio management for the TSLA trading bot
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Callable
import logging
from dataclasses import dataclass
from enum import Enum
import queue

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
    class EClient: pass
    class EWrapper: pass
    class Contract: pass
    class Order: pass
    class Execution: pass
    class CommissionReport: pass
    OrderId = int
    TickerId = int

from live_strategy_engine import TradingSignal, SignalType
from trade_logging import TradeRecord

logger = logging.getLogger(__name__)

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

class IBKRTradingApp(EWrapper, EClient):
    """IBKR Trading Application"""

    def __init__(self, parent=None):
        EClient.__init__(self, self)
        self.parent = parent
        
        # Connection settings
        self.host = "127.0.0.1"
        self.port = 7496  # TWS Live Trading port (7497 for paper)
        self.client_id = 1
        
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
        
    def connect_to_ibkr(self, host: str = "127.0.0.1", port: int = 7496, client_id: int = 1) -> bool:
        """Connect to IBKR TWS or Gateway"""
        try:
            self.host = host
            self.port = port
            self.client_id = client_id
            
            logger.info(f"Connecting to IBKR at {host}:{port} with client ID {client_id}")
            self.connect(host, port, client_id)
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("Successfully connected to IBKR")
                # Request next valid order ID
                self.reqIds(-1)
                time.sleep(1)  # Wait for order ID
                return True
            else:
                logger.error("Failed to connect to IBKR within timeout")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to IBKR: {e}")
            return False
    
    def disconnect_from_ibkr(self):
        """Disconnect from IBKR"""
        try:
            if self.connected:
                self.disconnect()
                self.connected = False
                logger.info("Disconnected from IBKR")
        except Exception as e:
            logger.error(f"Error disconnecting from IBKR: {e}")
    
    # EWrapper callback methods
    def connectAck(self):
        """Connection acknowledgment"""
        logger.info("Connection acknowledged by IBKR")
        self.connected = True
    
    def connectionClosed(self):
        """Connection closed"""
        logger.info("Connection to IBKR closed")
        self.connected = False
    
    def error(self, reqId: TickerId, errorCode: int, errorString: str):
        """Error handling"""
        if errorCode in [2104, 2106, 2158]:  # Informational messages
            logger.info(f"IBKR Info [{errorCode}]: {errorString}")
        else:
            logger.error(f"IBKR Error [{errorCode}]: {errorString}")
    
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
        self.app = IBKRTradingApp(parent=self)
        self.api_thread = None
        self.running = False
        
    def start(self, host: str = "127.0.0.1", port: int = 7496, client_id: int = 1) -> bool:
        """Start IBKR connection"""
        try:
            # Connect to IBKR
            if not self.app.connect_to_ibkr(host, port, client_id):
                return False
            
            # Start API thread
            self.api_thread = threading.Thread(target=self.app.run, daemon=True)
            self.api_thread.start()
            self.running = True
            
            # Wait for connection to stabilize
            time.sleep(2)
            
            # Request initial portfolio updates
            self.app.request_portfolio_updates()
            
            logger.info("IBKR Manager started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting IBKR Manager: {e}")
            return False
    
    def stop(self):
        """Stop IBKR connection"""
        try:
            self.running = False
            if self.app.connected:
                self.app.disconnect_from_ibkr()
            
            if self.api_thread and self.api_thread.is_alive():
                self.api_thread.join(timeout=5)
            
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

