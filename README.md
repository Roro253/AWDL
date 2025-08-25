# TSLA Trading Bot - Deployment Guide

## 🚀 Quick Deployment Checklist

### Prerequisites Completed ✅
- [x] Real-time data fetching from Polygon.io
- [x] Advanced trading strategy with multiple indicators
- [x] IBKR integration for live trading
- [x] Terminal monitoring with 60-second updates
- [x] macOS compatibility
- [x] 5-minute TSLA data processing
- [x] Comprehensive error handling
- [x] Risk management systems

### Files Included

| File | Purpose |
|------|---------|
| `tsla_trading_bot.py` | Main bot application |
| `live_data_fetcher.py` | Polygon.io data integration |
| `live_strategy_engine.py` | Trading strategy logic |
| `ibkr_interface.py` | Interactive Brokers API |
| `terminal_monitor.py` | Real-time terminal display |
| `requirements.txt` | Python dependencies |
| `setup.py` | Package installation |
| `test_setup.py` | Setup validation |
| `quick_start.sh` | Automated setup script |
| `.env.example` | Environment variables template |
| `README.md` | Complete documentation |

## 🏃‍♂️ Quick Start (5 Minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd tsla-trading-bot

# Run automated setup
./quick_start.sh
```

### 2. Configure API Keys
```bash
# Edit environment file
nano .env

# Add your Polygon API key
POLYGON_API_KEY=JlAQap9qJ8F8VrfChiPmYpticVo6SMPO
```

### 3. Start Trading
```bash
# Activate environment
source venv/bin/activate

# Run the bot
python tsla_trading_bot.py
```

## 🔧 Manual Setup (If Needed)

### 1. Python Environment
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables
```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

### 3. Test Setup
```bash
# Validate configuration
python test_setup.py

# Test terminal display
python terminal_monitor.py
```

## 📊 Terminal Interface Preview

The bot displays real-time information every 60 seconds:

```
================================================================================
                        TSLA TRADING BOT - LIVE MONITOR                        
================================================================================
Last Update: 2024-01-15 14:30:15 EST

BOT STATUS
--------------------
Status: RUNNING
Update Interval: 60 seconds
Next Update: 14:31:15

MARKET CONDITIONS
------------------------------
TSLA Price: $215.50
Market: OPEN
Trend: Strong
Volatility: Normal
Momentum: Bullish
RSI: 65.5
ADX: 28.3

POSITION STATUS
-------------------------
Position: LONG
Quantity: 3 shares
Entry Price: $210.00
Current Price: $215.50
Unrealized P&L: $16.50
Stop Loss: $205.00
Take Profit: $220.00

PERFORMANCE STATISTICS
-----------------------------------
Total Trades: 5
Win Rate: 60.0%
Total P&L: $125.50
Current Streak: 2
```

## ⚙️ Configuration Options

### Trading Parameters
- **Position Size**: 3 shares per trade (configurable)
- **Risk Management**: ATR-based stops and targets
- **Daily Limits**: Max trades and loss limits
- **Strategy**: Multi-indicator confirmation system

### Safety Features
- **Paper Trading Mode**: Test without real money
- **Emergency Stops**: Global account protection
- **Real-time Monitoring**: Continuous status updates
- **Comprehensive Logging**: Full audit trail

## 🔒 Security & Risk Management

### Built-in Protections
1. **Position Limits**: Maximum 3 shares per trade
2. **Daily Limits**: Configurable trade and loss limits
3. **Stop Losses**: Automatic risk management
4. **Emergency Stops**: Account-level protection
5. **Paper Trading**: Safe testing environment

### Recommended Settings for Beginners
```env
ENABLE_TRADING=true        # Live trading always enabled
MAX_POSITION_SIZE=3        # Small position size
MAX_DAILY_TRADES=3          # Conservative trade limit
MAX_DAILY_LOSS=200.0        # Reasonable loss limit
```

## 🐛 Troubleshooting

### Common Issues & Solutions

1. **"Connection refused" to IBKR**
   ```bash
   # Check TWS is running
   ps aux | grep tws
   
   # Verify API settings in TWS
   # File → Global Configuration → API → Settings
   ```

2. **"Invalid API key" for Polygon**
   ```bash
   # Test API key
   curl "https://api.polygon.io/v2/last/trade/TSLA?apikey=YOUR_KEY"
   ```

3. **Import errors**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

4. **macOS permission issues**
   ```bash
   # Fix Python permissions
   sudo xcode-select --install
   ```

## 📈 Performance Monitoring

### Key Metrics Tracked
- **Win Rate**: Percentage of profitable trades
- **Average P&L**: Per-trade performance
- **Maximum Drawdown**: Risk assessment
- **Sharpe Ratio**: Risk-adjusted returns
- **Trade Frequency**: Activity level

### Log Files
- `tsla_bot.log`: Main application log
- `session_data_*.json`: Trading session data
- Terminal output: Real-time status

## 🚨 Important Disclaimers

### Risk Warning
- **Start with paper trading** to test the system
- **Never risk more than you can afford to lose**
- **Monitor the bot actively** during market hours
- **Understand the strategy** before using real money

### Technical Limitations
- Requires stable internet connection
- Dependent on Polygon.io and IBKR uptime
- Strategy performance varies with market conditions
- Past performance doesn't guarantee future results

## 📞 Support & Resources

### Getting Help
1. **Setup Issues**: Run `python test_setup.py`
2. **Strategy Questions**: Review `live_strategy_engine.py`
3. **IBKR Problems**: Check TWS/Gateway status
4. **Data Issues**: Verify Polygon.io subscription

### Additional Resources
- **IBKR API Documentation**: [interactivebrokers.github.io](https://interactivebrokers.github.io/)
- **Polygon.io Docs**: [polygon.io/docs](https://polygon.io/docs)
- **Python Trading**: [python-trading.com](https://python-trading.com)

---

# TSLA Live Trading Bot

A sophisticated real-time trading bot for Tesla (TSLA) stock using Interactive Brokers (IBKR) with live data from Polygon.io. Features advanced technical analysis, risk management, and real-time terminal monitoring.

## 🚀 Features

- **Real-time Data**: Live 5-minute OHLCV data from Polygon.io
- **Advanced Strategy**: Multi-timeframe technical analysis with UT Bot, ADX, RSI, MACD, and Bollinger Bands
- **IBKR Integration**: Direct trading through Interactive Brokers API
- **Terminal Monitoring**: Real-time status updates every 60 seconds with colored output
- **Risk Management**: Stop losses, take profits, position sizing, and daily limits
- **macOS Compatible**: Optimized for macOS development environment
- **Paper Trading**: Built-in simulation mode for testing

## 📋 Prerequisites

### Required Accounts & Software

1. **Polygon.io Account**: For real-time market data
   - Sign up at [polygon.io](https://polygon.io)
   - Get your API key from the dashboard

2. **Interactive Brokers Account**: For trade execution
   - Open account at [Interactive Brokers](https://www.interactivebrokers.com)
   - Download and install TWS (Trader Workstation) or IB Gateway
   - Enable API trading in TWS settings

3. **Python 3.8+**: Required for running the bot
   - Install from [python.org](https://python.org) or use Homebrew on macOS

### macOS Setup

```bash
# Install Python via Homebrew (recommended)
brew install python

# Install Git if not already installed
brew install git
```

## 🛠 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/tsla-trading-bot.git
cd tsla-trading-bot
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Install IBKR API (if not included in requirements)
pip install ibapi
```

### 4. Set Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example environment file
cp .env.example .env

# Edit with your actual values
nano .env
```

Add your API keys and settings:

```env
# Polygon.io API Key (Required)
POLYGON_API_KEY=JlAQap9qJ8F8VrfChiPmYpticVo6SMPO

# IBKR Settings
IBKR_HOST=127.0.0.1
IBKR_PORT=7496  # 7496 for live trading, 7497 for paper trading
IBKR_CLIENT_ID=1

# Trading Settings
ENABLE_TRADING=true  # Live trading cannot be disabled
MAX_POSITION_SIZE=3
MAX_DAILY_TRADES=5
MAX_DAILY_LOSS=500.0

# Monitoring
UPDATE_INTERVAL=60
LOG_LEVEL=INFO

# CSV logging
LOG_DIR=./logs
LOG_PREFIX=tsla_bot
SESSION_ID=
```

## 🚀 Quick Start

### 1. Setup Interactive Brokers

1. **Start TWS or IB Gateway**:
   ```bash
   # TWS is usually installed in Applications on macOS
   open "/Applications/Trader Workstation.app"
   ```

2. **Configure API Settings**:
   - In TWS: File → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Add "127.0.0.1" to trusted IPs
   - Set Socket port to 7496 (live) or 7497 (paper)

3. **Login to Paper Trading Account** (recommended for testing)

### 2. Test the Setup

```bash
# Test data connection
python test_data_connection.py

# Test IBKR connection
python test_ibkr_connection.py

# Test terminal monitor
python test_terminal_monitor.py
```

### 3. Run the Bot

```bash
# Start the trading bot
python tsla_trading_bot.py
```

The bot will display a real-time terminal interface with:
- Current market conditions
- Position status
- Performance statistics
- Recent signals and trades
- Alerts and warnings

## 📊 Terminal Interface

The bot provides a comprehensive terminal interface that updates every 60 seconds:

```
================================================================================
                        TSLA TRADING BOT - LIVE MONITOR                        
================================================================================
Last Update: 2024-01-15 14:30:15 EST

BOT STATUS
--------------------
Status: RUNNING
Update Interval: 60 seconds
Next Update: 14:31:15

MARKET CONDITIONS
------------------------------
TSLA Price: $215.50
Market: OPEN
Trend: Strong
Volatility: Normal
Momentum: Bullish
RSI: 65.5
ADX: 28.3

POSITION STATUS
-------------------------
Position: LONG
Quantity: 3 shares
Entry Price: $210.00
Current Price: $215.50
Unrealized P&L: $16.50
Stop Loss: $205.00
Take Profit: $220.00
Time in Trade: 15 bars

PERFORMANCE STATISTICS
-----------------------------------
Total Trades: 5
Win Rate: 60.0%
Winning Trades: 3
Losing Trades: 2
Total P&L: $125.50
Avg Win: $75.25
Avg Loss: $-37.50
Current Streak: 2
Max Win Streak: 3
Max Loss Streak: 1

RECENT ACTIVITY
-------------------------
Recent Signals:
  14:25:30 - BUY: Pullback + UT Bot signal
  13:45:15 - SELL: Stop Loss
  12:30:45 - BUY: Breakout signal

Recent Trades:
  14:25:30 - BUY 10 @ $210.00 | P&L: $0.00
  13:45:15 - SELL 10 @ $208.50 | P&L: $-15.00
  12:30:45 - BUY 10 @ $207.00 | P&L: $0.00

================================================================================
Controls: Ctrl+C to stop | Bot will update every 60 seconds
================================================================================
```

## ⚙️ Configuration

### Strategy Parameters

The bot uses a sophisticated multi-indicator strategy. Key parameters can be adjusted in `live_strategy_engine.py`:

```python
@dataclass
class StrategyParams:
    # Position sizing
    shares_per_trade: int = 3
    max_position_size: int = 3
    
    # Risk management
    stop_atr: float = 1.0          # Stop loss in ATR multiples
    tp1_atr: float = 1.5           # Take profit in ATR multiples
    tp1_qty_pct: int = 50          # Partial profit percentage
    
    # Entry filters
    adx_min: float = 15.0          # Minimum trend strength
    atr_min_pct: float = 0.0005    # Minimum volatility
    rsi_threshold: float = 30      # RSI threshold for entries
    
    # Indicator periods
    atr_len: int = 14
    adx_len: int = 14
    rsi_len: int = 14
```

### Risk Management

Built-in risk management features:

- **Position Sizing**: Fixed 3 shares per trade (configurable)
- **Stop Losses**: ATR-based dynamic stops
- **Take Profits**: Partial profit taking with trailing stops
- **Daily Limits**: Maximum trades and loss limits per day
- **Emergency Stop**: Global stop loss for account protection

## 🧪 Testing & Development

### Live Trading Mode

The bot now always runs in live trading mode and forces `ENABLE_TRADING=true`:

```bash
python tsla_trading_bot.py
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python test_strategy_engine.py

# Test with coverage
python -m pytest --cov=. tests/
```

### Debugging

Enable debug logging:

```bash
# Set in .env file
LOG_LEVEL=DEBUG

# Or run with debug flag
python tsla_trading_bot.py --debug
```

## 📁 Project Structure

```
tsla-trading-bot/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore file
├── setup.py                 # Package setup
├── tsla_trading_bot.py      # Main bot application
├── live_data_fetcher.py     # Polygon.io data integration
├── live_strategy_engine.py  # Trading strategy logic
├── ibkr_interface.py        # Interactive Brokers API
├── terminal_monitor.py      # Real-time terminal display
├── tests/                   # Test files
│   ├── test_data_fetcher.py
│   ├── test_strategy.py
│   └── test_ibkr.py
├── docs/                    # Documentation
│   ├── strategy_guide.md
│   ├── api_reference.md
│   └── troubleshooting.md
└── logs/                    # Log files (created at runtime)
```

## 🔧 Troubleshooting

### Common Issues

1. **"Connection refused" to IBKR**:
   - Ensure TWS/Gateway is running
   - Check API settings are enabled
   - Verify port number (7496 for live, 7497 for paper)

2. **"Invalid API key" for Polygon**:
   - Verify your API key is correct
   - Check your Polygon.io subscription status
   - Ensure you have real-time data access

3. **"No data available"**:
   - Check market hours (9:30 AM - 4:00 PM ET)
   - Verify internet connection
   - Check Polygon.io API status

4. **macOS Permission Issues**:
   ```bash
   # Fix Python permissions
   sudo xcode-select --install
   
   # Reinstall Python packages
   pip uninstall -r requirements.txt
   pip install -r requirements.txt
   ```

### Log Files

Check log files for detailed error information:

```bash
# View recent logs
tail -f tsla_bot.log

# Search for errors
grep ERROR tsla_bot.log

# View specific date
grep "2024-01-15" tsla_bot.log
```



- **Start with paper trading** to test the system
- **Never risk more than you can afford to lose**
- **Understand the strategy** before using real money
- **Monitor the bot actively** during trading hours
- **Have a backup plan** for system failures




## 🙏 Acknowledgments

- Interactive Brokers for their comprehensive API
- Polygon.io for reliable market data
- The Python trading community for inspiration and tools





