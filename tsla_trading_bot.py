
"""Small end-to-end trading bot example.

The real project contains feature rich modules for fetching market data,
running the trading strategy, monitoring the terminal and logging trades.  The
class below wires these components together in a minimal fashion so unit tests
or examples can drive the whole stack without requiring the heavy production
script that normally orchestrates everything.
"""

from __future__ import annotations

import os
import time
from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine, SignalType, StrategyParams
from terminal_monitor import TerminalMonitor
from trade_logging import CSVLogger, TradeRecord


class TSLATradingBot:
    """Glue code joining fetcher, strategy, monitor and logger."""

    def __init__(self, polygon_api_key: str, symbol: str = "TSLA") -> None:
        self.symbol = symbol
        self.data = DataManager(polygon_api_key, symbol)
        self.strategy = LiveStrategyEngine(StrategyParams())
        self.monitor = TerminalMonitor()
        self.logger = CSVLogger()

    # ------------------------------------------------------------------
    def initialize(self) -> bool:
        """Initialise data and start the terminal monitor."""

        if not self.data.initialize_historical_data():
            return False
        self.monitor.start_monitoring()
        return True

    # ------------------------------------------------------------------
    def run_once(self) -> None:
        """Fetch latest data, produce a signal and log/monitor the result."""

        if not self.data.update_current_price():
            return

        df = self.strategy.compute_indicators(self.data.historical_data)
        signal = self.strategy.generate_signal(df, self.data.current_price)

        if signal and signal.signal_type != SignalType.NONE:
            record = TradeRecord(
                ts_utc="",
                ts_local="",
                session_id="",
                symbol=self.symbol,
                side=signal.signal_type.value,
                qty=signal.quantity,
                price=signal.price,
                reason=signal.reason,
            )
            self.logger.log_trade(record)

        # Update monitor with the latest price; the monitoring thread will pick
        # it up on the next refresh cycle.
        self.monitor.market_status["current_price"] = self.data.current_price

    # ------------------------------------------------------------------
    def run(self, interval: int = 60) -> None:
        if not self.initialize():
            raise RuntimeError("initialisation failed")
        while True:
            self.run_once()
            time.sleep(interval)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    api_key = os.getenv("POLYGON_API_KEY", "")
    bot = TSLATradingBot(api_key)
    bot.run()

