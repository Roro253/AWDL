"""Tiny TSLA trading bot tying the components together.

The script wires ``DataManager`` (data fetcher), ``LiveStrategyEngine``
(strategy), ``TerminalMonitor`` (UI), ``CSVLogger`` (logging) and the minimal
``IBKRInterface``.  It is intentionally lightweight and is meant only as an
illustration of how the pieces interact rather than a production ready bot.
"""

from __future__ import annotations

import os
import time

from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine, SignalType
from terminal_monitor import TerminalMonitor
from trade_logging import CSVLogger, TradeRecord
from ibkr_interface import IBKRInterface


def main() -> None:
    # ------------------------------------------------------------------
    # Instantiate components
    api_key = os.getenv("POLYGON_API_KEY", "")
    data = DataManager(api_key, "TSLA")
    data.initialize_historical_data(days_back=1)

    strategy = LiveStrategyEngine()

    ib = IBKRInterface(
        os.getenv("IBKR_HOST", "127.0.0.1"),
        int(os.getenv("IBKR_PORT", "7496")),
        int(os.getenv("IBKR_CLIENT_ID", "1")),
    )

    monitor = TerminalMonitor()
    logger = CSVLogger()

    monitor.update_bot_status("RUNNING")
    monitor.start_monitoring()
    ib.connect_and_start()

    # ------------------------------------------------------------------
    # Main loop
    try:
        while True:
            data.update_current_price()
            df = data.get_latest_complete_data()
            df = strategy.compute_indicators(df)
            signal = strategy.generate_signal(df, data.current_price)

            monitor.update_market_status(data.get_market_status())

            if signal:
                monitor.add_signal(signal.signal_type.value, signal.reason)
                action = "BUY" if signal.signal_type == SignalType.BUY else "SELL"
                oid = ib.submit_market_order("TSLA", action, signal.quantity)
                logger.log_trade(
                    TradeRecord(
                        ts_utc=None,
                        ts_local=None,
                        session_id="",
                        symbol="TSLA",
                        side=action,
                        qty=signal.quantity,
                        price=data.current_price,
                        order_id=str(oid),
                    )
                )
                monitor.add_trade(action, signal.quantity, data.current_price)

            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop_monitoring()
        ib.disconnect_safe()


if __name__ == "__main__":
    main()

