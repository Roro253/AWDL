"""
Terminal Monitor for TSLA Trading Bot
Provides real-time updates and human-readable status information
"""

import os
import time
import threading
from datetime import datetime, timedelta
import pytz
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
from colorama import init, Fore, Back, Style
import sys

# Initialize colorama for cross-platform colored output
init(autoreset=True)

logger = logging.getLogger(__name__)

@dataclass
class PerformanceStats:
    """Performance statistics tracking"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_drawdown: float = 0.0
    current_streak: int = 0
    max_win_streak: int = 0
    max_loss_streak: int = 0

class TerminalMonitor:
    """Terminal monitoring and display system"""
    
    def __init__(self):
        self.running = False
        self.monitor_thread = None
        self.update_interval = 60  # 60 seconds
        self.last_update = None
        
        # Status tracking
        self.bot_status = "INITIALIZING"
        self.market_status = {}
        self.position_status = {}
        self.strategy_status = {}
        self.performance_stats = PerformanceStats()
        self.recent_signals = []
        self.recent_trades = []
        self.alerts = []
        
        # Display settings
        self.terminal_width = 80
        self.clear_screen = True
        
    def start_monitoring(self):
        """Start the terminal monitoring system"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Terminal monitor started")
    
    def stop_monitoring(self):
        """Stop the terminal monitoring system"""
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
        logger.info("Terminal monitor stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._update_display()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(5)
    
    def _update_display(self):
        """Update the terminal display"""
        if self.clear_screen:
            os.system('clear' if os.name == 'posix' else 'cls')
        
        self._print_header()
        self._print_bot_status()
        self._print_market_conditions()
        self._print_position_status()
        self._print_performance_stats()
        self._print_recent_activity()
        self._print_alerts()
        self._print_footer()
        
        self.last_update = datetime.now()
    
    def _print_header(self):
        """Print header with title and timestamp"""
        now = datetime.now(pytz.timezone('US/Eastern'))
        
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*self.terminal_width}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'TSLA TRADING BOT - LIVE MONITOR':^{self.terminal_width}}")
        print(f"{Fore.CYAN}{Style.BRIGHT}{'='*self.terminal_width}")
        print(f"{Fore.WHITE}Last Update: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print()
    
    def _print_bot_status(self):
        """Print bot status section"""
        status_color = Fore.GREEN if self.bot_status == "RUNNING" else Fore.YELLOW if self.bot_status == "INITIALIZING" else Fore.RED
        
        print(f"{Fore.CYAN}{Style.BRIGHT}BOT STATUS")
        print(f"{Fore.CYAN}{'-'*20}")
        print(f"Status: {status_color}{Style.BRIGHT}{self.bot_status}")
        print(f"{Fore.WHITE}Update Interval: {self.update_interval} seconds")
        print(f"{Fore.WHITE}Next Update: {(datetime.now() + timedelta(seconds=self.update_interval)).strftime('%H:%M:%S')}")
        print()
    
    def _print_market_conditions(self):
        """Print market conditions section"""
        print(f"{Fore.CYAN}{Style.BRIGHT}MARKET CONDITIONS")
        print(f"{Fore.CYAN}{'-'*30}")
        
        if self.market_status:
            # Current price with color coding
            current_price = self.market_status.get('current_price', 0)
            price_color = Fore.GREEN if current_price > 0 else Fore.WHITE
            
            print(f"TSLA Price: {price_color}{Style.BRIGHT}${current_price:.2f}")
            
            # Market hours status
            is_market_hours = self.market_status.get('is_market_hours', False)
            market_color = Fore.GREEN if is_market_hours else Fore.RED
            market_text = "OPEN" if is_market_hours else "CLOSED"
            print(f"Market: {market_color}{Style.BRIGHT}{market_text}")
            
            # Market conditions
            trend_quality = self.market_status.get('trend_quality', 'Unknown')
            volatility = self.market_status.get('volatility_level', 'Unknown')
            momentum = self.market_status.get('momentum', 'Unknown')
            
            trend_color = Fore.GREEN if trend_quality == 'Strong' else Fore.YELLOW if trend_quality == 'Moderate' else Fore.RED
            vol_color = Fore.RED if volatility == 'High' else Fore.GREEN if volatility == 'Normal' else Fore.YELLOW
            mom_color = Fore.GREEN if momentum == 'Bullish' else Fore.RED if momentum == 'Bearish' else Fore.YELLOW
            
            print(f"Trend: {trend_color}{trend_quality}")
            print(f"Volatility: {vol_color}{volatility}")
            print(f"Momentum: {mom_color}{momentum}")
            
            # Technical indicators
            rsi = self.market_status.get('rsi', 0)
            rsi_color = Fore.RED if rsi > 70 else Fore.GREEN if rsi < 30 else Fore.WHITE
            print(f"RSI: {rsi_color}{rsi:.1f}")
            
            trend_strength = self.market_status.get('trend_strength', 0)
            adx_color = Fore.GREEN if trend_strength > 25 else Fore.YELLOW if trend_strength > 15 else Fore.RED
            print(f"ADX: {adx_color}{trend_strength:.1f}")
            
        else:
            print(f"{Fore.YELLOW}Market data not available")
        
        print()
    
    def _print_position_status(self):
        """Print position status section"""
        print(f"{Fore.CYAN}{Style.BRIGHT}POSITION STATUS")
        print(f"{Fore.CYAN}{'-'*25}")
        
        if self.position_status:
            status = self.position_status.get('status', 'FLAT')
            quantity = self.position_status.get('quantity', 0)
            
            if status == 'FLAT':
                print(f"Position: {Fore.WHITE}{Style.BRIGHT}FLAT (No Position)")
            else:
                entry_price = self.position_status.get('entry_price', 0)
                current_price = self.position_status.get('current_price', 0)
                unrealized_pnl = self.position_status.get('unrealized_pnl', 0)
                
                pnl_color = Fore.GREEN if unrealized_pnl > 0 else Fore.RED if unrealized_pnl < 0 else Fore.WHITE
                
                print(f"Position: {Fore.YELLOW}{Style.BRIGHT}{status}")
                print(f"Quantity: {Fore.WHITE}{quantity} shares")
                print(f"Entry Price: {Fore.WHITE}${entry_price:.2f}")
                print(f"Current Price: {Fore.WHITE}${current_price:.2f}")
                print(f"Unrealized P&L: {pnl_color}{Style.BRIGHT}${unrealized_pnl:.2f}")
                
                # Risk management levels
                stop_loss = self.position_status.get('stop_loss', 0)
                take_profit = self.position_status.get('take_profit', 0)
                
                print(f"Stop Loss: {Fore.RED}${stop_loss:.2f}")
                print(f"Take Profit: {Fore.GREEN}${take_profit:.2f}")
                
                # Time in trade
                bars_in_trade = self.position_status.get('bars_in_trade', 0)
                print(f"Time in Trade: {Fore.WHITE}{bars_in_trade} bars")
        else:
            print(f"{Fore.WHITE}Position data not available")
        
        print()
    
    def _print_performance_stats(self):
        """Print performance statistics section"""
        print(f"{Fore.CYAN}{Style.BRIGHT}PERFORMANCE STATISTICS")
        print(f"{Fore.CYAN}{'-'*35}")
        
        stats = self.performance_stats
        
        # Trade statistics
        print(f"Total Trades: {Fore.WHITE}{stats.total_trades}")
        
        if stats.total_trades > 0:
            win_rate_color = Fore.GREEN if stats.win_rate > 50 else Fore.RED if stats.win_rate < 40 else Fore.YELLOW
            print(f"Win Rate: {win_rate_color}{stats.win_rate:.1f}%")
            print(f"Winning Trades: {Fore.GREEN}{stats.winning_trades}")
            print(f"Losing Trades: {Fore.RED}{stats.losing_trades}")
            
            # P&L statistics
            total_pnl_color = Fore.GREEN if stats.total_pnl > 0 else Fore.RED if stats.total_pnl < 0 else Fore.WHITE
            print(f"Total P&L: {total_pnl_color}{Style.BRIGHT}${stats.total_pnl:.2f}")
            
            if stats.unrealized_pnl != 0:
                unrealized_color = Fore.GREEN if stats.unrealized_pnl > 0 else Fore.RED
                print(f"Unrealized P&L: {unrealized_color}${stats.unrealized_pnl:.2f}")
            
            # Win/Loss averages
            if stats.winning_trades > 0:
                print(f"Avg Win: {Fore.GREEN}${stats.avg_win:.2f}")
                print(f"Largest Win: {Fore.GREEN}${stats.largest_win:.2f}")
            
            if stats.losing_trades > 0:
                print(f"Avg Loss: {Fore.RED}${stats.avg_loss:.2f}")
                print(f"Largest Loss: {Fore.RED}${stats.largest_loss:.2f}")
            
            # Streaks
            streak_color = Fore.GREEN if stats.current_streak > 0 else Fore.RED if stats.current_streak < 0 else Fore.WHITE
            print(f"Current Streak: {streak_color}{stats.current_streak}")
            print(f"Max Win Streak: {Fore.GREEN}{stats.max_win_streak}")
            print(f"Max Loss Streak: {Fore.RED}{stats.max_loss_streak}")
            
            # Drawdown
            if stats.max_drawdown > 0:
                print(f"Max Drawdown: {Fore.RED}${stats.max_drawdown:.2f}")
        
        print()
    
    def _print_recent_activity(self):
        """Print recent signals and trades"""
        print(f"{Fore.CYAN}{Style.BRIGHT}RECENT ACTIVITY")
        print(f"{Fore.CYAN}{'-'*25}")
        
        # Recent signals
        if self.recent_signals:
            print(f"{Fore.YELLOW}Recent Signals:")
            for signal in self.recent_signals[-3:]:  # Show last 3 signals
                timestamp = signal.get('timestamp', datetime.now())
                signal_type = signal.get('type', 'UNKNOWN')
                reason = signal.get('reason', '')
                
                signal_color = Fore.GREEN if signal_type == 'BUY' else Fore.RED if signal_type == 'SELL' else Fore.YELLOW
                print(f"  {timestamp.strftime('%H:%M:%S')} - {signal_color}{signal_type}: {reason}")
        
        # Recent trades
        if self.recent_trades:
            print(f"{Fore.YELLOW}Recent Trades:")
            for trade in self.recent_trades[-3:]:  # Show last 3 trades
                timestamp = trade.get('timestamp', datetime.now())
                action = trade.get('action', 'UNKNOWN')
                quantity = trade.get('quantity', 0)
                price = trade.get('price', 0)
                pnl = trade.get('pnl', 0)
                
                action_color = Fore.GREEN if action == 'BUY' else Fore.RED
                pnl_color = Fore.GREEN if pnl > 0 else Fore.RED if pnl < 0 else Fore.WHITE
                
                print(f"  {timestamp.strftime('%H:%M:%S')} - {action_color}{action} {quantity} @ ${price:.2f} | P&L: {pnl_color}${pnl:.2f}")
        
        if not self.recent_signals and not self.recent_trades:
            print(f"{Fore.WHITE}No recent activity")
        
        print()
    
    def _print_alerts(self):
        """Print alerts and warnings"""
        if self.alerts:
            print(f"{Fore.RED}{Style.BRIGHT}ALERTS")
            print(f"{Fore.RED}{'-'*15}")
            
            for alert in self.alerts[-5:]:  # Show last 5 alerts
                timestamp = alert.get('timestamp', datetime.now())
                level = alert.get('level', 'INFO')
                message = alert.get('message', '')
                
                level_color = Fore.RED if level == 'ERROR' else Fore.YELLOW if level == 'WARNING' else Fore.WHITE
                print(f"{timestamp.strftime('%H:%M:%S')} - {level_color}{level}: {message}")
            
            print()
    
    def _print_footer(self):
        """Print footer with controls"""
        print(f"{Fore.CYAN}{'-'*self.terminal_width}")
        print(f"{Fore.WHITE}Controls: Ctrl+C to stop | Bot will update every {self.update_interval} seconds")
        print(f"{Fore.CYAN}{'='*self.terminal_width}")
    
    # Update methods for external components
    def update_bot_status(self, status: str):
        """Update bot status"""
        self.bot_status = status
    
    def update_market_status(self, market_data: Dict):
        """Update market conditions"""
        self.market_status = market_data
    
    def update_position_status(self, position_data: Dict):
        """Update position status"""
        self.position_status = position_data
    
    def update_strategy_status(self, strategy_data: Dict):
        """Update strategy status"""
        self.strategy_status = strategy_data
    
    def update_performance_stats(self, stats: PerformanceStats):
        """Update performance statistics"""
        self.performance_stats = stats
    
    def add_signal(self, signal_type: str, reason: str, timestamp: Optional[datetime] = None):
        """Add a new signal to recent activity"""
        signal = {
            'timestamp': timestamp or datetime.now(),
            'type': signal_type,
            'reason': reason
        }
        self.recent_signals.append(signal)
        
        # Keep only last 10 signals
        if len(self.recent_signals) > 10:
            self.recent_signals = self.recent_signals[-10:]
    
    def add_trade(self, action: str, quantity: int, price: float, pnl: float = 0, timestamp: Optional[datetime] = None):
        """Add a new trade to recent activity"""
        trade = {
            'timestamp': timestamp or datetime.now(),
            'action': action,
            'quantity': quantity,
            'price': price,
            'pnl': pnl
        }
        self.recent_trades.append(trade)
        
        # Keep only last 10 trades
        if len(self.recent_trades) > 10:
            self.recent_trades = self.recent_trades[-10:]
    
    def add_alert(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """Add an alert"""
        alert = {
            'timestamp': timestamp or datetime.now(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        
        # Keep only last 20 alerts
        if len(self.alerts) > 20:
            self.alerts = self.alerts[-20:]
    
    def force_update(self):
        """Force an immediate display update"""
        self._update_display()

def test_terminal_monitor():
    """Test the terminal monitor"""
    monitor = TerminalMonitor()
    
    # Set some test data
    monitor.update_bot_status("RUNNING")
    monitor.update_market_status({
        'current_price': 215.50,
        'is_market_hours': True,
        'trend_quality': 'Strong',
        'volatility_level': 'Normal',
        'momentum': 'Bullish',
        'rsi': 65.5,
        'trend_strength': 28.3
    })
    
    monitor.update_position_status({
        'status': 'LONG',
        'quantity': 3,
        'entry_price': 210.00,
        'current_price': 215.50,
        'unrealized_pnl': 16.50,
        'stop_loss': 205.00,
        'take_profit': 220.00,
        'bars_in_trade': 15
    })
    
    # Add some test activity
    monitor.add_signal("BUY", "Pullback + UT Bot signal")
    monitor.add_trade("BUY", 3, 210.00)
    monitor.add_alert("INFO", "Bot started successfully")
    
    # Update performance stats
    stats = PerformanceStats(
        total_trades=5,
        winning_trades=3,
        losing_trades=2,
        total_pnl=125.50,
        win_rate=60.0,
        avg_win=75.25,
        avg_loss=-37.50,
        current_streak=2,
        max_win_streak=3,
        max_loss_streak=1
    )
    monitor.update_performance_stats(stats)
    
    # Show the display
    monitor.force_update()
    
    print(f"\n{Fore.GREEN}Terminal monitor test completed!")

if __name__ == "__main__":
    test_terminal_monitor()

