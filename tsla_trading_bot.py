"""
Minimal TSLA trading bot glue script.
Wires together fetcher, strategy, monitor, logger, and IBKR interface.
"""

import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from live_data_fetcher import DataManager
from live_strategy_engine import LiveStrategyEngine, StrategyParams
from terminal_monitor import TerminalMonitor, PerformanceStats
from trade_logging import CSVLogger, TradeRecord, PerfSnapshot
from ibkr_interface import IBKRInterface


@dataclass
class BotConfig:
    polygon_api_key: str
    symbol: str = "TSLA"
    update_interval: int = 30
    enable_trading: bool = False
    ibkr_host: str = os.getenv("IBKR_HOST", "127.0.0.1")
    ibkr_port: int = int(os.getenv("IBKR_PORT", "7496"))
    ibkr_client_id: int = int(os.getenv("IBKR_CLIENT_ID", "1"))
    log_dir: str = "./logs"
    log_prefix: str = "tsla_bot"


class TSLATradingBot:
    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self.monitor = TerminalMonitor()
        self.monitor.update_interval = cfg.update_interval
        self.csv = CSVLogger(base_dir=cfg.log_dir, prefix=cfg.log_prefix,
                             session_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
        self.data = DataManager(cfg.polygon_api_key, cfg.symbol)
        self.strategy = LiveStrategyEngine(StrategyParams())
        self.ib: Optional[IBKRInterface] = None
        if cfg.enable_trading:
            self.ib = IBKRInterface(cfg.ibkr_host, cfg.ibkr_port, cfg.ibkr_client_id)
            self.ib.connect_and_start()

    def start(self):
        self.monitor.start_monitoring()
        # Initial historical load (safe no-op if API unavailable in this environment)
        self.data.initialize_historical_data(days_back=5)
        self.monitor.update_bot_status("RUNNING")

        while True:
            try:
                self.data.update_current_price()
                df = self.data.get_latest_complete_data()
                df = self.strategy.compute_indicators(df)

                status = self.strategy.analyze_market_conditions(df)
                market_status = self.data.get_market_status()
                market_status.update(status)
                self.monitor.update_market_status(market_status)

                price = self.data.current_price or status.get("current_price", 0)
                sig = self.strategy.generate_signal(df, price)
                if sig:
                    self.monitor.add_signal(sig.signal_type.value, sig.reason, sig.timestamp)
                    if self.ib and self.cfg.enable_trading:
                        self.ib.execute_signal(sig, self.cfg.symbol)
                    # Log trade (simulated if not enabled)
                    self.csv.log_trade(TradeRecord(
                        ts_utc=None,
                        ts_local=None,
                        session_id=self.csv.session_id,
                        symbol=self.cfg.symbol,
                        side=sig.signal_type.value if sig else "BUY",
                        qty=sig.quantity,
                        price=sig.price,
                        reason=sig.reason,
                        tags="live" if self.cfg.enable_trading else "paper",
                    ))

                # Update position/performance snapshots in monitor/logs (minimal)
                pos = self.strategy.get_position_summary()
                self.monitor.update_position_status(pos)
                self.csv.log_performance(PerfSnapshot(
                    ts_utc=None,
                    ts_local=None,
                    session_id=self.csv.session_id,
                    symbol=self.cfg.symbol,
                    total_trades=0,
                    wins=0,
                    losses=0,
                    flat_trades=0,
                    win_rate=0.0,
                    gross_pnl=0.0,
                    net_pnl=0.0,
                    max_drawdown=0.0,
                    open_position=pos.get("quantity", 0),
                    open_unrealized=pos.get("unrealized_pnl", 0.0),
                ))

                time.sleep(self.cfg.update_interval)
            except KeyboardInterrupt:
                break
            except Exception:
                # Keep minimal: ignore errors in this glue script
                time.sleep(self.cfg.update_interval)


def main():
    api_key = os.getenv("POLYGON_API_KEY", "")
    enable = os.getenv("ENABLE_TRADING", "false").lower() in ("1", "true", "yes", "y")
    cfg = BotConfig(polygon_api_key=api_key, enable_trading=enable)
    TSLATradingBot(cfg).start()


if __name__ == "__main__":
    main()
