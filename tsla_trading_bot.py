"""Very small example trading bot for TSLA.

The goal of this module is to demonstrate how the different building blocks of
the project interact.  It wires together the data fetcher, strategy engine,
terminal monitor and trade logger.  The implementation is intentionally tiny –
it fetches a single bar, generates a signal and records any resulting order.

This file is not meant to be feature complete or production ready but offers a
concise starting point for experiments and unit tests.
"""

from __future__ import annotations

import pandas as pd

from ibkr_interface import IBKRInterface
from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine
from terminal_monitor import TerminalMonitor
from trade_logging import CSVLogger, TradeRecord


class TSLATradingBot:
    """Glue component tying together fetcher, strategy, monitor and logger."""

    def __init__(self, api_key: str = "", symbol: str = "TSLA") -> None:
        self.symbol = symbol
        self.fetcher = DataManager(api_key, symbol)
        self.strategy = LiveStrategyEngine()
        self.monitor = TerminalMonitor()
        self.logger = CSVLogger()
        self.ibkr = IBKRInterface("127.0.0.1", 7496, 1)

    def run_once(self) -> None:
        """Fetch one bar, evaluate the strategy and log any trade."""

        bar = self.fetcher.get_latest_bar(self.symbol)
        if not bar:
            return

        # Append the latest bar to our data set
        if self.fetcher.historical_data.empty:
            self.fetcher.historical_data = pd.DataFrame(
                columns=["Open", "High", "Low", "Close", "Volume"]
            )
        self.fetcher.historical_data.loc[bar.timestamp] = [
            bar.open,
            bar.high,
            bar.low,
            bar.close,
            bar.volume,
        ]

        # Generate a trading signal from the updated history
        df = self.strategy.compute_indicators(self.fetcher.historical_data)
        signal = self.strategy.generate_signal(df, bar.close)
        self.monitor.market_status["current_price"] = bar.close

        if signal:
            order_id = self.ibkr.execute_signal(signal, self.symbol)
            if order_id:
                record = TradeRecord(
                    ts_utc="",
                    ts_local="",
                    session_id=self.logger.session_id,
                    symbol=self.symbol,
                    side=signal.signal_type.name,
                    qty=signal.quantity,
                    price=signal.price,
                    order_id=str(order_id),
                    reason=signal.reason,
                )
                self.logger.log_trade(record)
                self.monitor.recent_trades.append(record)


if __name__ == "__main__":  # pragma: no cover - manual execution only
    bot = TSLATradingBot()
    bot.run_once()

