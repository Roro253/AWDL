"""Tiny example trading bot for TSLA.

The goal of this script is to demonstrate how the different building blocks
of the project fit together: data fetching, strategy generation, broker
interaction and logging/monitoring.  It intentionally keeps the logic very
simple and is not meant for production trading.
"""

import os
from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine
from ibkr_interface import IBKRInterface
from terminal_monitor import TerminalMonitor
from trade_logging import CSVLogger, TradeRecord


def main():
    symbol = "TSLA"

    # Set up core components
    data = DataManager(os.getenv("POLYGON_API_KEY", ""), symbol)
    data.initialize_historical_data(days_back=1)

    strategy = LiveStrategyEngine()
    ibkr = IBKRInterface(
        os.getenv("IBKR_HOST", "127.0.0.1"),
        int(os.getenv("IBKR_PORT", "7496")),
        int(os.getenv("IBKR_CLIENT_ID", "1")),
    )
    monitor = TerminalMonitor()
    logger = CSVLogger()

    monitor.start_monitoring()
    ibkr.connect_and_start()

    # Single analysis/decision cycle
    data.update_current_price()
    df = strategy.compute_indicators(data.historical_data)
    price = data.current_price or 0
    signal = strategy.generate_signal(df, price)

    if signal:
        order_id = ibkr.execute_signal(signal, symbol=symbol)
        if order_id:
            record = TradeRecord(
                ts_utc="",
                ts_local="",
                session_id="",
                symbol=symbol,
                side=signal.signal_type.name,
                qty=signal.quantity,
                price=signal.price,
            )
            logger.log_trade(record)

    monitor.stop_monitoring()
    ibkr.disconnect_safe()


if __name__ == "__main__":
    main()
