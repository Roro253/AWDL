"""
TSLA Live Trading Bot
Main application that integrates all components for real-time trading
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime, timedelta, timezone
import pytz
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
import json
from trade_logging import CSVLogger, TradeRecord, PerfSnapshot

# Import our custom modules
from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine, StrategyParams, SignalType
from ibkr_interface import IBKRManager
from terminal_monitor import TerminalMonitor, PerformanceStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tsla_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BotConfig:
    """Bot configuration settings"""
    # API Keys
    polygon_api_key: str = ""
    
    # IBKR Settings
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7496  # Live trading port
    ibkr_client_id: int = 1
    
    # Trading Settings
    symbol: str = "TSLA"
    max_position_size: int = 3
    enable_trading: bool = True  # Set to False for paper/simulation mode
    
    # Monitoring Settings
    update_interval: int = 60  # seconds
    log_level: str = "INFO"

    # CSV logging
    log_dir: str = "./logs"
    log_prefix: str = "tsla_bot"
    session_id: str = ""
    
    # Risk Management
    max_daily_trades: int = 5
    max_daily_loss: float = 500.0
    emergency_stop_loss: float = 1000.0

class TSLATradingBot:
    """Main TSLA trading bot class"""
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Initialize components
        self.data_manager = None
        self.strategy_engine = None
        self.ibkr_manager = None
        self.terminal_monitor = None
        
        # Trading state
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.trade_history = []
        self.last_bar_time = None

        # Performance tracking
        self.performance_stats = PerformanceStats()

        # CSV logging
        self.session_id = self.config.session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.csv_logger = CSVLogger(
            base_dir=self.config.log_dir,
            prefix=self.config.log_prefix,
            session_id=self.session_id,
        )
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def initialize(self) -> bool:
        """Initialize all bot components"""
        try:
            logger.info("Initializing TSLA Trading Bot...")
            
            # Validate configuration
            if not self._validate_config():
                return False
            
            # Initialize data manager
            logger.info("Initializing data manager...")
            self.data_manager = DataManager(self.config.polygon_api_key, self.config.symbol)
            if not self.data_manager.initialize_historical_data():
                logger.error("Failed to initialize historical data")
                return False
            
            # Initialize strategy engine
            logger.info("Initializing strategy engine...")
            strategy_params = StrategyParams(
                shares_per_trade=self.config.max_position_size,
                max_position_size=self.config.max_position_size
            )
            self.strategy_engine = LiveStrategyEngine(strategy_params)
            
            # Initialize IBKR manager
            if self.config.enable_trading:
                logger.info("Initializing IBKR connection...")
                self.ibkr_manager = IBKRManager(csv_logger=self.csv_logger, session_id=self.session_id)
                if not self.ibkr_manager.start(
                    host=self.config.ibkr_host,
                    port=self.config.ibkr_port,
                    client_id=self.config.ibkr_client_id
                ):
                    logger.error("Failed to connect to IBKR")
                    return False
            else:
                logger.info("Trading disabled - running in simulation mode")
            
            # Initialize terminal monitor
            logger.info("Initializing terminal monitor...")
            self.terminal_monitor = TerminalMonitor()
            self.terminal_monitor.update_interval = self.config.update_interval
            self.terminal_monitor.start_monitoring()
            
            logger.info("Bot initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return False
    
    def _validate_config(self) -> bool:
        """Validate bot configuration"""
        if not self.config.polygon_api_key:
            logger.error("Polygon API key not provided")
            return False
        
        if self.config.max_position_size <= 0:
            logger.error("Invalid max position size")
            return False
        
        if self.config.update_interval < 10:
            logger.error("Update interval too short (minimum 10 seconds)")
            return False
        
        return True
    
    def start(self):
        """Start the trading bot"""
        if not self.initialize():
            logger.error("Failed to initialize bot")
            return False
        
        logger.info("Starting TSLA Trading Bot...")
        self.running = True
        
        # Update terminal status
        self.terminal_monitor.update_bot_status("RUNNING")
        self.terminal_monitor.add_alert("INFO", "Trading bot started successfully")
        
        try:
            self._main_loop()
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            self.terminal_monitor.add_alert("ERROR", f"Main loop error: {e}")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Stop the trading bot"""
        if not self.running:
            return
        
        logger.info("Stopping TSLA Trading Bot...")
        self.running = False
        self.shutdown_event.set()
        
        # Update terminal status
        if self.terminal_monitor:
            self.terminal_monitor.update_bot_status("STOPPING")
            self.terminal_monitor.add_alert("INFO", "Trading bot shutting down...")
        
        # Close IBKR connection
        if self.ibkr_manager:
            self.ibkr_manager.stop()
        
        # Stop terminal monitor
        if self.terminal_monitor:
            time.sleep(2)  # Allow final update
            self.terminal_monitor.stop_monitoring()
        
        # Save final state
        self._save_session_data()
        
        logger.info("Trading bot stopped")
    
    def _main_loop(self):
        """Main trading loop"""
        logger.info("Entering main trading loop...")
        
        while self.running and not self.shutdown_event.is_set():
            try:
                # Update current price
                self.data_manager.update_current_price()
                
                # Get latest market data
                market_data = self.data_manager.get_latest_complete_data()
                
                if market_data.empty:
                    logger.warning("No market data available")
                    time.sleep(30)
                    continue
                
                # Check if we have a new bar
                latest_bar_time = market_data.index[-1]
                if self.last_bar_time != latest_bar_time:
                    self.last_bar_time = latest_bar_time
                    logger.info(f"Processing new bar: {latest_bar_time}")
                    
                    # Process the new data
                    self._process_market_data(market_data)
                
                # Sleep until next update
                self.shutdown_event.wait(self.config.update_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop iteration: {e}")
                self.terminal_monitor.add_alert("ERROR", f"Loop error: {e}")
                time.sleep(30)
    
    def _process_market_data(self, market_data):
        """Process new market data and generate signals"""
        try:
            # Compute indicators
            data_with_indicators = self.strategy_engine.compute_indicators(market_data)
            
            # Analyze market conditions
            market_conditions = self.strategy_engine.analyze_market_conditions(data_with_indicators)

            # Combine with market status (e.g., market hours) from data manager
            market_status = self.data_manager.get_market_status()
            market_status.update(market_conditions)

            # Update terminal with combined market status
            self.terminal_monitor.update_market_status(market_status)
            
            # Get current price
            current_price = self.data_manager.current_price or market_conditions.get('current_price', 0)
            
            # Check for trading signals
            signal = self.strategy_engine.generate_signal(data_with_indicators, current_price)
            
            if signal:
                self._handle_trading_signal(signal)
            
            # Update position status
            position_summary = self.strategy_engine.get_position_summary()
            self.terminal_monitor.update_position_status(position_summary)
            
            # Update performance stats
            self._update_performance_stats()
            
            # Check risk management
            self._check_risk_management()
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
            self.terminal_monitor.add_alert("ERROR", f"Data processing error: {e}")
    
    def _handle_trading_signal(self, signal):
        """Handle a trading signal"""
        try:
            logger.info(f"Trading signal generated: {signal.signal_type.value} - {signal.reason}")
            
            # Add signal to terminal monitor
            self.terminal_monitor.add_signal(
                signal.signal_type.value,
                signal.reason,
                signal.timestamp
            )
            
            # Check daily limits
            if not self._check_daily_limits(signal):
                return
            
            # Execute trade if trading is enabled
            if self.config.enable_trading and self.ibkr_manager:
                success = self._execute_trade(signal)
                if success:
                    self.daily_trades += 1
                    logger.info(f"Trade executed successfully (Daily trades: {self.daily_trades})")
                else:
                    logger.error("Failed to execute trade")
                    self.terminal_monitor.add_alert("ERROR", "Trade execution failed")
            else:
                # Simulation mode
                self._simulate_trade(signal)
                logger.info(f"Simulated trade: {signal.signal_type.value} {signal.quantity} shares at ${signal.price:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling trading signal: {e}")
            self.terminal_monitor.add_alert("ERROR", f"Signal handling error: {e}")
    
    def _execute_trade(self, signal) -> bool:
        """Execute actual trade through IBKR"""
        try:
            # Execute the signal
            success = self.ibkr_manager.execute_signal(signal)

            if success:
                # Capture entry price before update for PnL calculation
                entry_price = self.strategy_engine.position.entry_price if self.strategy_engine.position else None

                # Update strategy engine position
                executed_price = signal.price  # In real implementation, get actual fill price
                self.strategy_engine.update_position(signal, executed_price)

                # Record trade
                self._record_trade(signal, executed_price, real_trade=True, entry_price=entry_price)

                return True

            return False
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return False
    
    def _simulate_trade(self, signal):
        """Simulate trade execution"""
        try:
            # Capture entry price before update for PnL calculation
            entry_price = self.strategy_engine.position.entry_price if self.strategy_engine.position else None

            # Update strategy engine position
            self.strategy_engine.update_position(signal, signal.price)

            # Record simulated trade
            self._record_trade(signal, signal.price, real_trade=False, entry_price=entry_price)

        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
    
    def _record_trade(self, signal, executed_price: float, real_trade: bool = True, entry_price: float = None):
        """Record trade in history and CSV logs"""
        trade_record = {
            'timestamp': signal.timestamp,
            'signal_type': signal.signal_type.value,
            'quantity': signal.quantity,
            'price': executed_price,
            'reason': signal.reason,
            'real_trade': real_trade
        }

        self.trade_history.append(trade_record)

        # Add to terminal monitor
        self.terminal_monitor.add_trade(
            signal.signal_type.value,
            signal.quantity,
            executed_price,
            timestamp=signal.timestamp
        )

        # Determine trade side
        side_map = {
            SignalType.BUY: "BUY",
            SignalType.SELL: "SELL",
            SignalType.PARTIAL_SELL: "PARTIAL_SELL",
        }
        side = side_map.get(signal.signal_type, "BUY")

        # Calculate P&L for exits
        pnl_realized = None
        if entry_price is not None and signal.signal_type in [SignalType.SELL, SignalType.PARTIAL_SELL]:
            pnl_realized = round((executed_price - entry_price) * signal.quantity, 2)

        position_after = self.strategy_engine.position.quantity if self.strategy_engine.position else 0

        record = TradeRecord(
            ts_utc=None,
            ts_local=None,
            session_id=self.session_id,
            symbol=self.config.symbol,
            side=side,
            qty=signal.quantity,
            price=executed_price,
            reason=signal.reason,
            pnl_realized=pnl_realized,
            position_after=position_after,
            tags="live" if real_trade else "paper",
        )
        self.csv_logger.log_trade(record)

        # Immediately update position display after recording trade
        self.terminal_monitor.update_position_status(
            self.strategy_engine.get_position_summary()
        )
    
    def _check_daily_limits(self, signal) -> bool:
        """Check if daily trading limits allow this trade"""
        if self.daily_trades >= self.config.max_daily_trades:
            logger.warning(f"Daily trade limit reached ({self.config.max_daily_trades})")
            self.terminal_monitor.add_alert("WARNING", "Daily trade limit reached")
            return False
        
        if self.daily_pnl <= -self.config.max_daily_loss:
            logger.warning(f"Daily loss limit reached (${self.config.max_daily_loss})")
            self.terminal_monitor.add_alert("WARNING", "Daily loss limit reached")
            return False
        
        return True
    
    def _check_risk_management(self):
        """Check risk management rules"""
        try:
            # Check emergency stop loss
            if self.total_pnl <= -self.config.emergency_stop_loss:
                logger.error(f"Emergency stop loss triggered (${self.config.emergency_stop_loss})")
                self.terminal_monitor.add_alert("ERROR", "Emergency stop loss triggered - shutting down")
                self.stop()
                return
            
            # Reset daily counters at market open
            now = datetime.now(pytz.timezone('US/Eastern'))
            if now.hour == 9 and now.minute == 30 and now.second < 60:
                self.daily_trades = 0
                self.daily_pnl = 0.0
                logger.info("Daily counters reset")
                self.terminal_monitor.add_alert("INFO", "Daily counters reset")
            
        except Exception as e:
            logger.error(f"Error in risk management check: {e}")
    
    def _update_performance_stats(self):
        """Update performance statistics"""
        try:
            # Calculate stats from trade history
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0.0
            wins = []
            losses = []
            
            for trade in self.trade_history:
                # This is simplified - in real implementation, calculate actual P&L
                pnl = 0.0  # Would calculate based on entry/exit prices
                
                if pnl > 0:
                    winning_trades += 1
                    wins.append(pnl)
                elif pnl < 0:
                    losing_trades += 1
                    losses.append(pnl)
                
                total_pnl += pnl
            
            # Update performance stats
            self.performance_stats.total_trades = len(self.trade_history)
            self.performance_stats.winning_trades = winning_trades
            self.performance_stats.losing_trades = losing_trades
            self.performance_stats.total_pnl = total_pnl
            
            if self.performance_stats.total_trades > 0:
                self.performance_stats.win_rate = (winning_trades / self.performance_stats.total_trades) * 100
            
            if wins:
                self.performance_stats.avg_win = sum(wins) / len(wins)
                self.performance_stats.largest_win = max(wins)
            
            if losses:
                self.performance_stats.avg_loss = sum(losses) / len(losses)
                self.performance_stats.largest_loss = min(losses)
            
            # Update terminal monitor
            self.terminal_monitor.update_performance_stats(self.performance_stats)

            # Log performance snapshot
            snapshot = PerfSnapshot(
                ts_utc=None,
                ts_local=None,
                session_id=self.session_id,
                symbol=self.config.symbol,
                total_trades=self.performance_stats.total_trades,
                wins=self.performance_stats.winning_trades,
                losses=self.performance_stats.losing_trades,
                flat_trades=self.performance_stats.total_trades - self.performance_stats.winning_trades - self.performance_stats.losing_trades,
                win_rate=(self.performance_stats.win_rate / 100) if self.performance_stats.total_trades > 0 else 0.0,
                gross_pnl=self.performance_stats.total_pnl,
                net_pnl=self.performance_stats.total_pnl,
                max_drawdown=self.performance_stats.max_drawdown,
                open_position=self.strategy_engine.position.quantity if self.strategy_engine.position else 0,
                open_unrealized=self.strategy_engine.position.unrealized_pnl if self.strategy_engine.position else 0.0,
                notes=None,
            )
            self.csv_logger.log_performance(snapshot)
            
        except Exception as e:
            logger.error(f"Error updating performance stats: {e}")
    
    def _save_session_data(self):
        """Save session data to file"""
        try:
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'trade_history': self.trade_history,
                'performance_stats': {
                    'total_trades': self.performance_stats.total_trades,
                    'winning_trades': self.performance_stats.winning_trades,
                    'losing_trades': self.performance_stats.losing_trades,
                    'total_pnl': self.performance_stats.total_pnl,
                    'win_rate': self.performance_stats.win_rate
                },
                'daily_stats': {
                    'daily_trades': self.daily_trades,
                    'daily_pnl': self.daily_pnl
                }
            }
            
            filename = f"session_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            logger.info(f"Session data saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving session data: {e}")

def load_config() -> BotConfig:
    """Load configuration from environment variables or config file"""
    config = BotConfig()
    
    # Load from environment variables
    config.polygon_api_key = os.getenv('POLYGON_API_KEY', 'JlAQap9qJ8F8VrfChiPmYpticVo6SMPO')
    config.ibkr_host = os.getenv('IBKR_HOST', '127.0.0.1')
    config.ibkr_port = int(os.getenv('IBKR_PORT', '7496'))
    config.enable_trading = os.getenv('ENABLE_TRADING', 'true').lower() == 'true'
    config.max_position_size = int(os.getenv('MAX_POSITION_SIZE', str(config.max_position_size)))

    # CSV logging
    config.log_dir = os.getenv('LOG_DIR', './logs')
    config.log_prefix = os.getenv('LOG_PREFIX', 'tsla_bot')
    config.session_id = os.getenv('SESSION_ID', '')

    return config

def main():
    """Main entry point"""
    print("TSLA Live Trading Bot")
    print("====================")
    
    # Load configuration
    config = load_config()
    
    if not config.polygon_api_key:
        print("Error: Polygon API key not set")
        return 1
    
    # Create and start bot
    bot = TSLATradingBot(config)
    
    try:
        bot.start()
        return 0
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        bot.stop()
        return 0
    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

