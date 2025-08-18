"""
Live Strategy Engine for TSLA Trading Bot
Real-time implementation of the trading strategy
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
import logging
from enum import Enum

# Import indicator functions from backtest
from tsla_backtest_relaxed import (
    rma, true_range, atr, manual_adx, macd_hist, vwap_intraday, resample_htf
)

logger = logging.getLogger(__name__)

class SignalType(Enum):
    NONE = "NONE"
    BUY = "BUY"
    SELL = "SELL"
    PARTIAL_SELL = "PARTIAL_SELL"

class PositionStatus(Enum):
    FLAT = "FLAT"
    LONG = "LONG"
    PARTIAL = "PARTIAL"

@dataclass
class TradingSignal:
    """Trading signal with all relevant information"""
    signal_type: SignalType
    timestamp: datetime
    price: float
    quantity: int
    reason: str
    confidence: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class Position:
    """Current position information"""
    status: PositionStatus
    entry_time: datetime
    entry_price: float
    quantity: int
    current_price: float
    unrealized_pnl: float
    stop_loss: float
    take_profit: float
    tp1_hit: bool = False
    bars_in_trade: int = 0

@dataclass
class StrategyParams:
    """Live trading strategy parameters (relaxed for real trading)"""
    # Position sizing
    shares_per_trade: int = 10
    max_position_size: int = 10
    
    # Risk management
    commission_rate: float = 0.001  # 0.1%
    slippage_ticks: int = 1
    tick_size: float = 0.01
    
    # Strategy parameters (relaxed for live trading)
    adx_min: float = 15.0
    atr_min_pct: float = 0.0005  # 0.05%
    bb_width_min: float = 0.0005
    rsi_threshold: float = 30
    min_confirmations: int = 1
    
    # Entry/Exit parameters
    tp1_atr: float = 1.5
    tp1_qty_pct: int = 50
    stop_atr: float = 1.0
    be_trig_atr: float = 0.5
    be_offset_ticks: int = 1
    trail_atr: float = 1.5
    max_bars_in_trade: int = 200
    
    # UT Bot parameters
    ut_key_value: float = 2.0
    ut_atr_period: int = 10
    
    # Indicator periods
    atr_len: int = 14
    adx_len: int = 14
    rsi_len: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_sig: int = 9
    pb_ema_len: int = 20
    don_len: int = 20
    bb_len: int = 20
    bb_mult: float = 2.0

class LiveStrategyEngine:
    """Real-time strategy engine for live trading"""
    
    def __init__(self, params: Optional[StrategyParams] = None):
        self.params = params or StrategyParams()
        self.position: Optional[Position] = None
        self.last_signal: Optional[TradingSignal] = None
        self.indicators_cache = {}
        self.signal_history: List[TradingSignal] = []
        
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all technical indicators for the strategy"""
        if df.empty or len(df) < 100:
            logger.warning("Insufficient data for indicator calculation")
            return df
        
        out = df.copy()
        
        try:
            # ATR and ATR%
            out['ATR'] = atr(out, self.params.atr_len)
            out['ATR%'] = out['ATR'] / out['Close']
            
            # Bollinger Bands width
            basis = out['Close'].rolling(self.params.bb_len).mean()
            dev = out['Close'].rolling(self.params.bb_len).std(ddof=0) * self.params.bb_mult
            out['BBWidthFrac'] = ((basis + dev) - (basis - dev)) / basis.replace(0, np.nan)
            
            # ADX
            out['ADX'] = manual_adx(out, self.params.adx_len)
            
            # RSI
            delta = out['Close'].diff()
            up = delta.clip(lower=0)
            down = -delta.clip(upper=0)
            rs = rma(up, self.params.rsi_len) / rma(down, self.params.rsi_len).replace(0, np.nan)
            out['RSI'] = 100 - (100 / (1 + rs))
            
            # MACD
            _, _, hist = macd_hist(out['Close'], self.params.macd_fast, self.params.macd_slow, self.params.macd_sig)
            out['MACD_H'] = hist
            
            # EMAs
            out['EMA_PB'] = out['Close'].ewm(span=self.params.pb_ema_len, adjust=False).mean()
            
            # Donchian channels
            out['DonHi'] = out['High'].rolling(self.params.don_len).max()
            out['DonLo'] = out['Low'].rolling(self.params.don_len).min()
            
            # UT Bot
            out = self._compute_ut_bot(out)
            
            # VWAP (simplified for live trading)
            out['VWAP'] = vwap_intraday(out)
            
            logger.debug(f"Computed indicators for {len(out)} bars")
            return out
            
        except Exception as e:
            logger.error(f"Error computing indicators: {e}")
            return df
    
    def _compute_ut_bot(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute UT Bot indicator"""
        ut_stop = np.full(len(df), np.nan)
        src = df['Close'].values
        nLoss = self.params.ut_key_value * atr(df, self.params.ut_atr_period).values
        
        for i in range(len(df)):
            prev = ut_stop[i-1] if i > 0 else np.nan
            src_i = src[i]
            
            if not np.isnan(prev):
                if src_i > prev:
                    ut_stop[i] = max(prev, src_i - nLoss[i])
                else:
                    ut_stop[i] = src_i + nLoss[i]
            else:
                ut_stop[i] = src_i + nLoss[i] if not np.isnan(nLoss[i]) else np.nan
        
        df['UT_STOP'] = ut_stop
        df['UT_POS'] = 0
        
        # UT position signals
        cross_up = (df['Close'].shift(1) < df['UT_STOP'].shift(1)) & (df['Close'] > df['UT_STOP'])
        cross_dn = (df['Close'].shift(1) > df['UT_STOP'].shift(1)) & (df['Close'] < df['UT_STOP'])
        df.loc[cross_up, 'UT_POS'] = 1
        df.loc[cross_dn, 'UT_POS'] = -1
        df['UT_POS'] = df['UT_POS'].replace(0, np.nan).ffill().fillna(0)
        
        return df
    
    def analyze_market_conditions(self, df: pd.DataFrame) -> Dict[str, any]:
        """Analyze current market conditions"""
        if df.empty or len(df) < 50:
            return {'status': 'insufficient_data'}
        
        latest = df.iloc[-1]
        
        # Trend analysis
        trend_strength = latest.get('ADX', 0)
        volatility = latest.get('ATR%', 0)
        bb_width = latest.get('BBWidthFrac', 0)
        
        # Momentum analysis
        rsi = latest.get('RSI', 50)
        macd_hist = latest.get('MACD_H', 0)
        
        # Price action
        current_price = latest['Close']
        ema_pb = latest.get('EMA_PB', current_price)
        
        conditions = {
            'timestamp': df.index[-1],
            'current_price': current_price,
            'trend_strength': trend_strength,
            'volatility_pct': volatility * 100,
            'bb_width': bb_width,
            'rsi': rsi,
            'macd_hist': macd_hist,
            'price_vs_ema': (current_price - ema_pb) / ema_pb * 100,
            'trend_quality': 'Strong' if trend_strength > 25 else 'Weak' if trend_strength < 15 else 'Moderate',
            'volatility_level': 'High' if volatility > 0.002 else 'Low' if volatility < 0.0005 else 'Normal',
            'momentum': 'Bullish' if rsi > 50 and macd_hist > 0 else 'Bearish' if rsi < 50 and macd_hist < 0 else 'Neutral'
        }
        
        return conditions
    
    def generate_signal(self, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Generate trading signal based on current market conditions"""
        if df.empty or len(df) < 100:
            return None
        
        latest = df.iloc[-1]
        timestamp = df.index[-1]
        
        # Check if we're in a position
        if self.position:
            return self._check_exit_signals(latest, current_price, timestamp)
        else:
            return self._check_entry_signals(df, latest, current_price, timestamp)
    
    def _check_entry_signals(self, df: pd.DataFrame, latest: pd.Series, 
                           current_price: float, timestamp: datetime) -> Optional[TradingSignal]:
        """Check for entry signals"""
        
        # Basic filters
        if (latest.get('ADX', 0) < self.params.adx_min or
            latest.get('ATR%', 0) < self.params.atr_min_pct or
            latest.get('BBWidthFrac', 0) < self.params.bb_width_min):
            return None
        
        # Momentum confirmations
        rsi_ok = latest.get('RSI', 0) > self.params.rsi_threshold
        macd_ok = latest.get('MACD_H', 0) > -0.5
        
        confirmations = sum([rsi_ok, macd_ok])
        if confirmations < self.params.min_confirmations:
            return None
        
        # Entry signals
        signals = []
        
        # Pullback signal
        if len(df) >= 2:
            prev = df.iloc[-2]
            if (prev['Close'] <= prev.get('EMA_PB', prev['Close']) and 
                latest['Close'] > latest.get('EMA_PB', latest['Close'])):
                signals.append("Pullback")
        
        # Breakout signal
        if latest['Close'] > latest.get('DonHi', latest['Close']):
            signals.append("Breakout")
        
        # UT Bot signal
        if len(df) >= 2:
            prev = df.iloc[-2]
            if (prev['Close'] <= prev.get('UT_STOP', prev['Close']) and 
                latest['Close'] > latest.get('UT_STOP', latest['Close'])):
                signals.append("UT_Bot")
        
        if not signals:
            return None
        
        # Calculate stops and targets
        atr_value = latest.get('ATR', 1.0)
        stop_loss = current_price - (self.params.stop_atr * atr_value)
        take_profit = current_price + (self.params.tp1_atr * atr_value)
        
        # Calculate confidence based on number of signals and strength
        confidence = min(len(signals) * 0.3 + (latest.get('ADX', 0) / 50), 1.0)
        
        return TradingSignal(
            signal_type=SignalType.BUY,
            timestamp=timestamp,
            price=current_price,
            quantity=self.params.shares_per_trade,
            reason=f"Entry: {', '.join(signals)}",
            confidence=confidence,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
    
    def _check_exit_signals(self, latest: pd.Series, current_price: float, 
                          timestamp: datetime) -> Optional[TradingSignal]:
        """Check for exit signals when in position"""
        if not self.position:
            return None
        
        # Update position
        self.position.current_price = current_price
        self.position.unrealized_pnl = (current_price - self.position.entry_price) * self.position.quantity
        self.position.bars_in_trade += 1
        
        # Stop loss
        if current_price <= self.position.stop_loss:
            return TradingSignal(
                signal_type=SignalType.SELL,
                timestamp=timestamp,
                price=current_price,
                quantity=self.position.quantity,
                reason="Stop Loss"
            )
        
        # Take profit (partial)
        if (current_price >= self.position.take_profit and 
            not self.position.tp1_hit and 
            self.position.status == PositionStatus.LONG):
            
            partial_qty = int(self.position.quantity * self.params.tp1_qty_pct / 100)
            return TradingSignal(
                signal_type=SignalType.PARTIAL_SELL,
                timestamp=timestamp,
                price=current_price,
                quantity=partial_qty,
                reason="Partial Take Profit"
            )
        
        # Trail stop
        if self.position.tp1_hit:
            atr_value = latest.get('ATR', 1.0)
            trail_stop = current_price - (self.params.trail_atr * atr_value)
            self.position.stop_loss = max(self.position.stop_loss, trail_stop)
        
        # Max bars in trade
        if self.position.bars_in_trade >= self.params.max_bars_in_trade:
            return TradingSignal(
                signal_type=SignalType.SELL,
                timestamp=timestamp,
                price=current_price,
                quantity=self.position.quantity,
                reason="Max Time in Trade"
            )
        
        return None
    
    def update_position(self, signal: TradingSignal, executed_price: float) -> bool:
        """Update position based on executed signal"""
        try:
            if signal.signal_type == SignalType.BUY:
                if self.position is None:
                    atr_value = 1.0  # Default, should be passed from indicators
                    self.position = Position(
                        status=PositionStatus.LONG,
                        entry_time=signal.timestamp,
                        entry_price=executed_price,
                        quantity=signal.quantity,
                        current_price=executed_price,
                        unrealized_pnl=0.0,
                        stop_loss=signal.stop_loss or (executed_price - atr_value),
                        take_profit=signal.take_profit or (executed_price + atr_value * 1.5)
                    )
                    logger.info(f"Opened long position: {signal.quantity} shares at ${executed_price:.2f}")
                    return True
            
            elif signal.signal_type == SignalType.PARTIAL_SELL:
                if self.position and self.position.status == PositionStatus.LONG:
                    self.position.quantity -= signal.quantity
                    self.position.status = PositionStatus.PARTIAL
                    self.position.tp1_hit = True
                    
                    # Move stop to breakeven
                    self.position.stop_loss = max(
                        self.position.stop_loss,
                        self.position.entry_price + (self.params.be_offset_ticks * self.params.tick_size)
                    )
                    
                    logger.info(f"Partial exit: {signal.quantity} shares at ${executed_price:.2f}")
                    return True
            
            elif signal.signal_type == SignalType.SELL:
                if self.position:
                    logger.info(f"Closed position: {self.position.quantity} shares at ${executed_price:.2f}")
                    self.position = None
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error updating position: {e}")
            return False
    
    def get_position_summary(self) -> Dict[str, any]:
        """Get current position summary"""
        if not self.position:
            return {
                'status': 'FLAT',
                'quantity': 0,
                'unrealized_pnl': 0.0,
                'entry_price': 0.0,
                'current_price': 0.0
            }
        
        return {
            'status': self.position.status.value,
            'entry_time': self.position.entry_time,
            'entry_price': self.position.entry_price,
            'current_price': self.position.current_price,
            'quantity': self.position.quantity,
            'unrealized_pnl': self.position.unrealized_pnl,
            'stop_loss': self.position.stop_loss,
            'take_profit': self.position.take_profit,
            'bars_in_trade': self.position.bars_in_trade,
            'tp1_hit': self.position.tp1_hit
        }
    
    def get_strategy_status(self) -> Dict[str, any]:
        """Get overall strategy status"""
        return {
            'position': self.get_position_summary(),
            'last_signal': {
                'type': self.last_signal.signal_type.value if self.last_signal else 'NONE',
                'timestamp': self.last_signal.timestamp if self.last_signal else None,
                'reason': self.last_signal.reason if self.last_signal else None
            } if self.last_signal else None,
            'signal_count': len(self.signal_history),
            'parameters': {
                'shares_per_trade': self.params.shares_per_trade,
                'adx_min': self.params.adx_min,
                'atr_min_pct': self.params.atr_min_pct * 100,
                'rsi_threshold': self.params.rsi_threshold
            }
        }

