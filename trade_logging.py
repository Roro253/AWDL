from __future__ import annotations
import csv
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, Literal

TradeSide = Literal["BUY", "SELL", "PARTIAL_SELL", "SHORT", "COVER"]

@dataclass
class TradeRecord:
    # Always UTC timestamps; add ET string for human readability.
    ts_utc: str              # ISO8601, e.g. "2025-08-19T17:45:00Z"
    ts_local: str            # e.g. "2025-08-19 13:45:00 ET"
    session_id: str          # unique id per bot run, e.g. start_timestamp or UUID
    symbol: str              # "TSLA"
    side: TradeSide          # BUY/SELL/PARTIAL_SELL...
    qty: int
    price: float             # fill price
    order_id: Optional[str] = None
    trade_id: Optional[str] = None
    reason: Optional[str] = None     # "Entry: Breakout", "Exit: Stop Loss", etc.
    pnl_realized: Optional[float] = None     # only for exits/partials
    position_after: Optional[int] = None     # net shares after this fill
    tags: Optional[str] = None       # freeform: "live", "paper", "ATR=1.5", etc.

@dataclass
class PerfSnapshot:
    ts_utc: str
    ts_local: str
    session_id: str
    symbol: str
    total_trades: int
    wins: int
    losses: int
    flat_trades: int
    win_rate: float                # 0..1
    gross_pnl: float
    net_pnl: float                 # gross - commissions - fees
    max_drawdown: float            # (absolute $) or use negative number
    open_position: int             # current qty
    open_unrealized: float         # current P&L on open position
    notes: Optional[str] = None

class CSVLogger:
    """
    Thread-safe CSV logger for trades and performance snapshots.
    Files rotate daily by default. Safe to call from IBKR callbacks and main loop.
    """
    def __init__(self, base_dir: str = "./logs", prefix: str = "tsla_bot", session_id: Optional[str] = None):
        os.makedirs(base_dir, exist_ok=True)
        self.base_dir = base_dir
        self.prefix = prefix
        self.session_id = session_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self._lock = threading.Lock()

    def _date_stamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _trade_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.prefix}_trades_{self._date_stamp()}.csv")

    def _perf_path(self) -> str:
        return os.path.join(self.base_dir, f"{self.prefix}_performance_{self._date_stamp()}.csv")

    @staticmethod
    def _now_iso_utc() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _now_et_str() -> str:
        # keep it dependency-light; you can swap to pytz/zoneinfo if already in the repo
        try:
            from zoneinfo import ZoneInfo  # py3.9+
            et = ZoneInfo("America/New_York")
            return datetime.now(et).strftime("%Y-%m-%d %H:%M:%S ET")
        except Exception:
            return "N/A"

    def _ensure_headers(self, path: str, fieldnames: list[str]):
        new_file = not os.path.exists(path) or os.path.getsize(path) == 0
        if new_file:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

    def log_trade(self, record: TradeRecord):
        d = asdict(record)
        if not d.get("ts_utc"):
            d["ts_utc"] = self._now_iso_utc()
        if not d.get("ts_local") or d["ts_local"] == "N/A":
            d["ts_local"] = self._now_et_str()
        if not d.get("session_id"):
            d["session_id"] = self.session_id

        path = self._trade_path()
        fieldnames = list(d.keys())

        with self._lock:
            self._ensure_headers(path, fieldnames)
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(d)

    def log_performance(self, snap: PerfSnapshot):
        d = asdict(snap)
        if not d.get("ts_utc"):
            d["ts_utc"] = self._now_iso_utc()
        if not d.get("ts_local") or d["ts_local"] == "N/A":
            d["ts_local"] = self._now_et_str()
        if not d.get("session_id"):
            d["session_id"] = self.session_id

        path = self._perf_path()
        fieldnames = list(d.keys())

        with self._lock:
            self._ensure_headers(path, fieldnames)
            with open(path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(d)
