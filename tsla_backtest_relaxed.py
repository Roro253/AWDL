

import math
import os
from dataclasses import dataclass
from typing import Optional, Tuple, List
import numpy as np
import pandas as pd
import requests
import pytz

# =========================
# Helpers
# =========================

def rma(series: pd.Series, length: int) -> pd.Series:
    """Wilder's RMA via ewm."""
    return series.ewm(alpha=1/length, adjust=False, min_periods=length).mean()

def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df['Close'].shift(1)
    tr = pd.concat([
        (df['High'] - df['Low']).abs(),
        (df['High'] - prev_close).abs(),
        (df['Low'] - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr

def atr(df: pd.DataFrame, length: int) -> pd.Series:
    return rma(true_range(df), length)

def manual_adx(df: pd.DataFrame, length: int) -> pd.Series:
    up = df['High'].diff()
    dn = -df['Low'].diff()
    plusDM = np.where((up > dn) & (up > 0), up, 0.0)
    minusDM = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr_len = atr(df, length)
    plusDI = 100 * rma(pd.Series(plusDM, index=df.index), length) / atr_len.replace(0, np.nan)
    minusDI = 100 * rma(pd.Series(minusDM, index=df.index), length) / atr_len.replace(0, np.nan)
    dx = 100 * (plusDI.minus(minusDI).abs() / (plusDI + minusDI).replace(0, np.nan))
    return rma(dx.fillna(0), length)

def macd_hist(close: pd.Series, fast=12, slow=26, sig=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=sig, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist

def vwap_intraday(df: pd.DataFrame) -> pd.Series:
    """
    Session VWAP reset each day (US/Eastern). Assumes df index is timezone-aware Eastern.
    """
    tp = (df['High'] + df['Low'] + df['Close']) / 3.0
    # Group by session date
    g = df.groupby(df.index.date)
    cum_pv = g.apply(lambda x: (tp.loc[x.index] * x['Volume']).cumsum()).reset_index(level=0, drop=True)
    cum_v  = g['Volume'].cumsum()
    return (cum_pv / cum_v).reindex(df.index)

def resample_htf(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    o = df['Open'].resample(rule).first()
    h = df['High'].resample(rule).max()
    l = df['Low'].resample(rule).min()
    c = df['Close'].resample(rule).last()
    v = df['Volume'].resample(rule).sum()
    out = pd.concat([o, h, l, c, v], axis=1)
    out.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    return out.dropna()

def within_sessions(idx: pd.DatetimeIndex, sessions: List[Tuple[str, str]], tz='US/Eastern') -> pd.Series:
    """Return boolean mask if time (in tz) is within any session window like [("09:40","11:30"),("13:00","15:55")]."""
    tzidx = idx.tz_convert(tz)
    times = tzidx.strftime('%H:%M')
    mask = pd.Series(False, index=idx)
    for start, end in sessions:
        mask |= (times >= start) & (times <= end)
    return mask

def day_of_week(idx: pd.DatetimeIndex, tz='US/Eastern') -> pd.Series:
    return idx.tz_convert(tz).weekday  # Monday=0 ... Sunday=6

def week_number(idx: pd.DatetimeIndex, tz='US/Eastern') -> pd.Series:
    return idx.tz_convert(tz).isocalendar().week.astype(int)

def _parse_polygon_interval(interval: str) -> Tuple[int, str]:
    """Convert interval like '5m' to (multiplier, timespan) for Polygon API."""
    unit = interval[-1].lower()
    multiplier = int(interval[:-1])
    if unit == 'm':
        return multiplier, 'minute'
    if unit == 'h':
        return multiplier, 'hour'
    if unit == 'd':
        return multiplier, 'day'
    raise ValueError(f"Unsupported interval: {interval}")

# =========================
# Parameters
# =========================

@dataclass
class Params:
    symbol: str = "SPY"
    start: str = "2024-01-01"
    end: str = None  # None => today
    interval: str = "5m"
    initial_capital: float = 50_000.0
    commission_rate: float = 0.001   # 0.1%
    tick_size: float = 0.01
    slippage_ticks: int = 1

    # HTF gates
    htf1: str = "15min"     # for EMA-50
    htf2: str = "60min"     # for EMA-200
    emaLen15: int = 50
    emaLen60: int = 200
    slope_thr_ppm: float = 0.00  # per HTF bar, ‰

    # Regime filters
    adxLen: int = 14
    adxMin: float = 27.0
    atrLen: int = 14
    minATRperc: float = 0.0020  # 0.20%
    bbLen: int = 20
    bbMult: float = 2.0
    minBBwidth: float = 0.0012

    # Confirms (N-of-3)
    useRSI: bool = True
    rsiLen: int = 14
    useMACD: bool = True
    macdFast: int = 12
    macdSlow: int = 26
    macdSig: int = 9
    useVolConfirm: bool = True
    volLen: int = 20
    volMult: float = 1.10
    minConfirms: int = 2

    # Entries
    enableBreakout: bool = False
    donLen: int = 28
    enablePullback: bool = True
    pbEmaLen: int = 20
    pbMinATR: float = 0.25
    enableVWAP: bool = True
    vwapDevATR: float = 0.15
    enableORB: bool = True

    # UT Bot
    useUTasFilter: bool = True
    useUTasSignal: bool = True
    utKeyValue: float = 3.0
    utAtrPeriod: int = 10
    useUTtrailExit: bool = False

    # WADL breadth
    useWADLfilter: bool = True
    wadl_symbol: Optional[str] = "WADL"  # change to your breadth series; None disables
    wadl_tf: str = "60min"
    wadlEmaLen: int = 50
    wadlSlopeBars: int = 3
    wadlSlopeThr: float = 0.00

    # Frequency controls & governance
    longOnly: bool = True
    maxLongPerDay: int = 2
    maxLongPerWeek: int = 3
    maxBarsInTrade: int = 720  # 5m bars
    skipFridays: bool = True
    sessions: Tuple[Tuple[str, str], ...] = (("09:40", "11:30"), ("13:00", "15:55"))
    cooldownBars: int = 5
    pauseDD: bool = True
    ddLimitPct: float = 15.0  # closed-trade DD limit

    # Exits
    tp1ATR: float = 0.9
    tp1QtyPct: int = 75
    stopATR: float = 1.8
    beTrigATR: float = 0.8
    beOffsetTicks: int = 1
    trailATR: float = 2.4

# =========================
# Data loading
# =========================

def load_data(params: Params, csv_path: Optional[str] = None) -> pd.DataFrame:
    if csv_path:
        df = pd.read_csv(csv_path, parse_dates=['Datetime'])
        df = df.set_index('Datetime').sort_index()
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC').tz_convert('US/Eastern')
        else:
            df.index = df.index.tz_convert('US/Eastern')
        df = df[['Open','High','Low','Close','Volume']]
        return df
    # Polygon path
    end = pd.Timestamp.now(tz='US/Eastern') if params.end is None else pd.Timestamp(params.end, tz='US/Eastern')
    start = pd.Timestamp(params.start, tz='US/Eastern')
    multiplier, timespan = _parse_polygon_interval(params.interval)
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        raise RuntimeError("POLYGON_API_KEY environment variable not set")
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{params.symbol}/range/"
        f"{multiplier}/{timespan}/{int(start.tz_convert('UTC').timestamp() * 1000)}/"
        f"{int(end.tz_convert('UTC').timestamp() * 1000)}"
    )
    q = {'adjusted': 'true', 'sort': 'asc', 'limit': 50000, 'apiKey': api_key}
    resp = requests.get(url, params=q)
    resp.raise_for_status()
    data = resp.json()
    if data.get('status') != 'OK' or not data.get('results'):
        raise RuntimeError("Polygon returned no data. Try another date range or check API key.")
    records = []
    for r in data['results']:
        ts = pd.Timestamp(r['t'], unit='ms', tz='UTC').tz_convert('US/Eastern')
        records.append({'Datetime': ts, 'Open': r['o'], 'High': r['h'], 'Low': r['l'], 'Close': r['c'], 'Volume': r['v']})
    df = pd.DataFrame.from_records(records).set_index('Datetime')
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def load_wadl_series(params: Params, base_index: pd.DatetimeIndex) -> Optional[pd.Series]:
    if not params.useWADLfilter or not params.wadl_symbol:
        return None
    try:
        multiplier, timespan = _parse_polygon_interval(params.interval)
        api_key = os.getenv('POLYGON_API_KEY')
        if not api_key:
            print("POLYGON_API_KEY not set; breadth filter will be skipped.")
            return None
        start = base_index[0]
        end = base_index[-1]
        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{params.wadl_symbol}/range/"
            f"{multiplier}/{timespan}/{int(start.tz_convert('UTC').timestamp() * 1000)}/"
            f"{int(end.tz_convert('UTC').timestamp() * 1000)}"
        )
        q = {'adjusted': 'true', 'sort': 'asc', 'limit': 50000, 'apiKey': api_key}
        resp = requests.get(url, params=q)
        resp.raise_for_status()
        data = resp.json()
        if data.get('status') != 'OK' or not data.get('results'):
            print("WADL symbol not found on Polygon; breadth filter will be skipped.")
            return None
        records = []
        for r in data['results']:
            ts = pd.Timestamp(r['t'], unit='ms', tz='UTC').tz_convert('US/Eastern')
            records.append({'Datetime': ts, 'Close': r['c']})
        wadl = pd.DataFrame.from_records(records).set_index('Datetime')['Close'].rename('WADL')
        wadl_df = wadl.to_frame()
        wadl_htf = resample_htf(wadl_df.rename(columns={'WADL': 'Close'}), params.wadl_tf)
        wadl_htf = wadl_htf['Close']
        return wadl_htf.reindex(base_index, method='ffill')
    except Exception as e:
        print(f"WADL fetch error: {e}. Breadth filter will be skipped.")
        return None

# =========================
# Indicator calculations
# =========================

def compute_indicators(df: pd.DataFrame, params: Params, wadl_series: Optional[pd.Series]) -> pd.DataFrame:
    out = df.copy()

    # ATR / ATR%
    out['ATR'] = atr(out, params.atrLen)
    out['ATR%'] = out['ATR'] / out['Close']

    # BB width fraction
    basis = out['Close'].rolling(params.bbLen).mean()
    dev = out['Close'].rolling(params.bbLen).std(ddof=0) * params.bbMult
    out['BBWidthFrac'] = ((basis + dev) - (basis - dev)) / basis.replace(0, np.nan)

    # ADX (manual)
    out['ADX'] = manual_adx(out, params.adxLen)

    # RSI
    delta = out['Close'].diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    rs = rma(up, params.rsiLen) / rma(down, params.rsiLen).replace(0, np.nan)
    out['RSI'] = 100 - (100 / (1 + rs))

    # MACD hist
    _, _, hist = macd_hist(out['Close'], params.macdFast, params.macdSlow, params.macdSig)
    out['MACD_H'] = hist

    # Volume SMA
    out['VOL_SMA'] = out['Volume'].rolling(params.volLen).mean()

    # VWAP (intraday)
    out['VWAP'] = vwap_intraday(out)

    # Pullback EMA
    out['EMA_PB'] = out['Close'].ewm(span=params.pbEmaLen, adjust=False).mean()

    # HTF EMAs & slopes
    htf1 = resample_htf(out, params.htf1)
    htf2 = resample_htf(out, params.htf2)
    htf1_ema = htf1['Close'].ewm(span=params.emaLen15, adjust=False).mean().rename('EMA15')
    htf2_ema = htf2['Close'].ewm(span=params.emaLen60, adjust=False).mean().rename('EMA60')
    out['EMA15'] = htf1_ema.reindex(out.index, method='ffill')
    out['EMA60'] = htf2_ema.reindex(out.index, method='ffill')
    out['SLOPE15'] = (out['EMA15'] - out['EMA15'].shift(1)) / out['EMA15'].shift(1) * 1000.0
    out['SLOPE60'] = (out['EMA60'] - out['EMA60'].shift(1)) / out['EMA60'].shift(1) * 1000.0

    # Donchian
    out['DonHi'] = out['High'].rolling(params.donLen).max()
    out['DonLo'] = out['Low'].rolling(params.donLen).min()

    # UT-Bot trailing stop (sequential)
    ut_stop = np.full(len(out), np.nan)
    src = out['Close'].values
    nLoss = params.utKeyValue * out['ATR'].rolling(params.utAtrPeriod).mean().values  # slight proxy
    # Better: use ATR(utAtrPeriod)
    nLoss = params.utKeyValue * atr(out, params.utAtrPeriod).values
    for i in range(len(out)):
        prev = ut_stop[i-1] if i > 0 else np.nan
        src_i = src[i]
        src_prev = src[i-1] if i > 0 else np.nan
        if not np.isnan(prev) and not np.isnan(src_prev):
            if (src_i > prev) and (src_prev > prev):
                ut_stop[i] = max(prev, src_i - nLoss[i])
            elif (src_i < prev) and (src_prev < prev):
                ut_stop[i] = min(prev, src_i + nLoss[i])
            elif src_i > prev:
                ut_stop[i] = src_i - nLoss[i]
            else:
                ut_stop[i] = src_i + nLoss[i]
        else:
            ut_stop[i] = src_i + nLoss[i] if not np.isnan(nLoss[i]) else np.nan
    out['UT_STOP'] = ut_stop
    out['UT_POS'] = 0
    cross_up = (out['Close'].shift(1) < out['UT_STOP'].shift(1)) & (out['Close'] > out['UT_STOP'])
    cross_dn = (out['Close'].shift(1) > out['UT_STOP'].shift(1)) & (out['Close'] < out['UT_STOP'])
    out.loc[cross_up, 'UT_POS'] = 1
    out.loc[cross_dn, 'UT_POS'] = -1
    out['UT_POS'] = out['UT_POS'].replace(0, np.nan).ffill().fillna(0)

    # Breadth (WADL)
    if params.useWADLfilter and (wadl_series is not None) and (wadl_series.notna().any()):
        wadl_close = wadl_series.rename('WADL').reindex(out.index, method='ffill')
        wadl_htf = wadl_close.to_frame()
        wadl_ema = wadl_htf['WADL'].ewm(span=params.wadlEmaLen, adjust=False).mean()
        wadl_slope = (wadl_ema - wadl_ema.shift(params.wadlSlopeBars)) / wadl_ema.shift(params.wadlSlopeBars) * 1000.0
        out['WADL'] = wadl_close
        out['WADL_EMA'] = wadl_ema
        out['WADL_SLOPE'] = wadl_slope
    else:
        out['WADL'] = np.nan
        out['WADL_EMA'] = np.nan
        out['WADL_SLOPE'] = np.nan

    return out

# =========================
# Strategy/backtest
# =========================

@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    direction: str = "long"
    entry_price: float = 0.0
    exit_price: float = 0.0
    qty: int = 0
    pnl: float = 0.0
    reason: str = ""
    tp1_hit: bool = False

def simulate(df: pd.DataFrame, params: Params) -> Tuple[pd.DataFrame, List[Trade]]:
    tz = 'US/Eastern'
    idx = df.index

    # Precompute masks
    sess_mask = within_sessions(idx, list(params.sessions), tz) if params.sessions else pd.Series(True, index=idx)
    fri_mask = (day_of_week(idx, tz) == 4)
    week_no = week_number(idx, tz)
    date_only = idx.tz_convert(tz).date

    # ORB: compute per-day 09:30-10:00 high/low
    tstr = idx.tz_convert(tz).strftime('%H:%M')
    in_orb = (tstr >= "09:30") & (tstr <= "10:00")
    post_orb = (tstr > "10:00") & (tstr <= "16:00")
    orb_high = pd.Series(np.nan, index=idx)
    orb_low = pd.Series(np.nan, index=idx)
    for d, g in df.loc[in_orb].groupby(pd.Series(date_only, index=idx)[in_orb]):
        orb_high.loc[g.index[-1]:] = g['High'].max()
        orb_low.loc[g.index[-1]:] = g['Low'].min()

    # Derived signals
    trend_long = (df['Close'] > df['EMA15']) & (df['Close'] > df['EMA60']) \
                 & (df['SLOPE15'] > params.slope_thr_ppm) & (df['SLOPE60'] > params.slope_thr_ppm) \
                 & (df['ADX'] >= params.adxMin)

    vol_ok = df['ATR%'] >= params.minATRperc
    bb_ok = df['BBWidthFrac'] >= params.minBBwidth

    rsi_pass_L = (~df['RSI'].isna()) & (df['RSI'] > 50) if params.useRSI else pd.Series(True, index=idx)
    macd_pass_L = (~df['MACD_H'].isna()) & (df['MACD_H'] > 0) if params.useMACD else pd.Series(True, index=idx)
    vol_pass = (df['Volume'] >= (df['VOL_SMA'] * params.volMult)) if params.useVolConfirm else pd.Series(True, index=idx)

    confirms_met_L = (rsi_pass_L.astype(int) + macd_pass_L.astype(int) + vol_pass.astype(int)) >= min(params.minConfirms, (1 if params.useRSI else 0) + (1 if params.useMACD else 0) + (1 if params.useVolConfirm else 0))

    pulled_L = (df['Close'] < df['EMA_PB']) & (((df['EMA_PB'] - df['Low']) / df['ATR']) >= params.pbMinATR)
    cross_up_pb = (df['Close'].shift(1) <= df['EMA_PB'].shift(1)) & (df['Close'] > df['EMA_PB'])
    vwap_tag_L = ((df['VWAP'] - df['Low']) / df['ATR']) >= params.vwapDevATR
    vwap_ok_L = (~params.enableVWAP) | ((df['Close'] > df['VWAP']) & vwap_tag_L)
    long_pb = params.enablePullback & pulled_L & cross_up_pb & vwap_ok_L

    long_break = params.enableBreakout & (df['Close'] > df['DonHi'].shift(1))
    long_orb = params.enableORB & post_orb & orb_high.notna() & (df['Close'] > orb_high)

    ut_pos_long = (df['UT_POS'] == 1)
    ut_buy = (df['Close'].shift(1) <= df['UT_STOP'].shift(1)) & (df['Close'] > df['UT_STOP'])

    # WADL breadth gates
    breadth_ok_long = (~params.useWADLfilter) | df['WADL'].isna() | ((df['WADL'] > df['WADL_EMA']) & (df['WADL_SLOPE'] > params.wadlSlopeThr))

    # Final long setup
    entry_sources_L = long_pb | long_break | long_orb | (params.useUTasSignal & ut_buy)
    base_long_gate = sess_mask & (~(params.skipFridays) | (~fri_mask)) & vol_ok & bb_ok & trend_long & confirms_met_L & entry_sources_L
    final_long_gate = base_long_gate & ((~params.useUTasFilter) | ut_pos_long) & breadth_ok_long

    # Backtest loop
    equity = params.initial_capital
    peak_closed_net = 0.0
    closed_net = 0.0
    position = None  # dict with keys: entry_price, qty, tp1_done, be_armed, stop, trail_type
    trades: List[Trade] = []

    long_count_day = {}
    long_count_week = {}

    cooldown = 0

    def can_enter(ts):
        nonlocal cooldown, closed_net, peak_closed_net
        if params.pauseDD and peak_closed_net > 0:
            dd_pct = (peak_closed_net - closed_net) / abs(peak_closed_net) * 100.0
            if dd_pct > params.ddLimitPct:
                return False
        return cooldown == 0

    # Iterate bars
    for i, ts in enumerate(df.index):
        row = df.iloc[i]

        # Cooldown tick
        if cooldown > 0:
            cooldown -= 1

        # Update counts
        d = ts.tz_convert('US/Eastern').date()
        w = week_no[i]
        long_count_day.setdefault(d, 0)
        long_count_week.setdefault(w, 0)

        price = row['Close']

        # Manage open position
        if position:
            # Update ATR (for trailing)
            atr_now = row['ATR']
            # Take-profit 1
            if (not position['tp1_done']) and price >= position['tp1_price']:
                # close tp1 percent
                qty_to_close = math.floor(position['qty'] * (params.tp1QtyPct / 100.0))
                fill = price - params.tick_size * params.slippage_ticks  # selling
                trade_val = qty_to_close * fill
                fee = trade_val * params.commission_rate
                realized = (fill - position['entry_price']) * qty_to_close - fee
                equity += realized
                position['qty'] -= qty_to_close
                position['tp1_done'] = True
                # arm BE
                position['stop'] = max(position['stop'], position['entry_price'] + params.beOffsetTicks * params.tick_size)
            # Dynamic trailing for runner
            if position['qty'] > 0:
                if params.useUTtrailExit:
                    # stop is max(UT stop, BE)
                    position['stop'] = max(position['stop'], float(row['UT_STOP']))
                else:
                    # ATR trail from highest close since entry
                    position['hh'] = max(position['hh'], price)
                    position['stop'] = max(position['stop'], position['hh'] - params.trailATR * atr_now)

                # Hit stop?
                if price <= position['stop']:
                    fill = position['stop'] - params.tick_size * params.slippage_ticks
                    qty_to_close = position['qty']
                    trade_val = qty_to_close * fill
                    fee = trade_val * params.commission_rate
                    realized = (fill - position['entry_price']) * qty_to_close - fee
                    equity += realized
                    tr = Trade(entry_time=position['t_entry'], exit_time=ts, direction="long",
                               entry_price=position['entry_price'], exit_price=fill, qty=qty_to_close,
                               pnl=realized, reason="Stop/Trail", tp1_hit=position['tp1_done'])
                    trades.append(tr)
                    closed_net += realized
                    peak_closed_net = max(peak_closed_net, closed_net)
                    # cooldown if loss
                    if realized < 0:
                        cooldown = params.cooldownBars
                    position = None
            # Time stop
            if position and (i - position['i_entry']) >= params.maxBarsInTrade:
                fill = price - params.tick_size * params.slippage_ticks
                qty_to_close = position['qty']
                trade_val = qty_to_close * fill
                fee = trade_val * params.commission_rate
                realized = (fill - position['entry_price']) * qty_to_close - fee
                equity += realized
                tr = Trade(entry_time=position['t_entry'], exit_time=ts, direction="long",
                           entry_price=position['entry_price'], exit_price=fill, qty=qty_to_close,
                           pnl=realized, reason="TimeStop", tp1_hit=position['tp1_done'])
                trades.append(tr)
                closed_net += realized
                peak_closed_net = max(peak_closed_net, closed_net)
                if realized < 0:
                    cooldown = params.cooldownBars
                position = None

        # Entry logic (long-only)
        if (not position) and params.longOnly:
            if final_long_gate.iloc[i] and can_enter(ts):
                # caps
                if long_count_day[d] >= params.maxLongPerDay or long_count_week[w] >= params.maxLongPerWeek:
                    pass
                else:
                    # size: 100% equity
                    qty = int(equity // (price + params.tick_size * params.slippage_ticks))
                    if qty > 0:
                        fill = price + params.tick_size * params.slippage_ticks  # buying
                        cost = qty * fill
                        fee = cost * params.commission_rate
                        equity -= (cost + fee)

                        # init stops and targets
                        atr_now = row['ATR']
                        tp1_price = fill + params.tp1ATR * atr_now
                        init_stop = fill - params.stopATR * atr_now
                        be_trigger = fill + params.beTrigATR * atr_now

                        position = dict(
                            i_entry=i,
                            t_entry=ts,
                            entry_price=fill,
                            qty=qty,
                            tp1_price=tp1_price,
                            be_trigger=be_trigger,
                            stop=init_stop,
                            hh=fill,
                            tp1_done=False
                        )
                        long_count_day[d] += 1
                        long_count_week[w] += 1

        # arm BE after trigger
        if position:
            if price >= position['be_trigger']:
                position['stop'] = max(position['stop'], position['entry_price'] + params.beOffsetTicks * params.tick_size)

    # Close any open position at the end
    if position:
        last_price = df['Close'].iloc[-1]
        fill = last_price - params.tick_size * params.slippage_ticks
        qty_to_close = position['qty']
        fee = (qty_to_close * fill) * params.commission_rate
        realized = (fill - position['entry_price']) * qty_to_close - fee
        tr = Trade(entry_time=position['t_entry'], exit_time=df.index[-1], direction="long",
                   entry_price=position['entry_price'], exit_price=fill, qty=qty_to_close,
                   pnl=realized, reason="EOD", tp1_hit=position['tp1_done'])
        trades.append(tr)

    # Build equity curve (closed P&L only; simple)
    # For detailed curve, you'd track equity per bar.
    results = {
        "total_trades": len(trades),
        "wins": sum(1 for t in trades if t.pnl > 0),
        "losses": sum(1 for t in trades if t.pnl <= 0),
        "win_rate": (sum(1 for t in trades if t.pnl > 0) / len(trades) * 100.0) if trades else 0.0,
        "net_profit": sum(t.pnl for t in trades),
        "profit_factor": (sum(t.pnl for t in trades if t.pnl > 0) / abs(sum(t.pnl for t in trades if t.pnl < 0))) if any(t.pnl < 0 for t in trades) else np.inf,
    }
    # Max equity DD on closed-trade equity
    eq = pd.Series([params.initial_capital + sum(t.pnl for t in trades[:k]) for k in range(len(trades)+1)], dtype=float)
    rolling_max = eq.cummax()
    dd = (rolling_max - eq)
    results["max_dd"] = dd.max()
    results["max_dd_pct"] = (dd.max() / rolling_max.max() * 100.0) if rolling_max.max() > 0 else 0.0

    trades_df = pd.DataFrame([t.__dict__ for t in trades])
    return pd.DataFrame([results]), trades_df

# =========================
# Main
# =========================

def main(csv_path: Optional[str] = None):
    params = Params()
    df = load_data(params, csv_path=csv_path)
    wadl_series = load_wadl_series(params, df.index)

    df = compute_indicators(df, params, wadl_series)

    # Filter NaNs early period
    df = df.dropna(subset=["ATR","BBWidthFrac","ADX","EMA15","EMA60","EMA_PB","VWAP"])

    results, trades = simulate(df, params)
    pd.set_option("display.float_format", "{:,.2f}".format)
    print("\n=== RESULTS ===")
    print(results.to_string(index=False))
    print("\n=== SAMPLE TRADES ===")
    print(trades.head(10).to_string(index=False))

    # Save trades
    trades.to_csv("trades_spy5_win60_ut_wadl.csv", index=False)
    print("\nSaved trades to trades_spy5_win60_ut_wadl.csv")

if __name__ == "__main__":
    # Optionally pass a CSV path here, e.g. main('your_5m_data.csv')
    main()
