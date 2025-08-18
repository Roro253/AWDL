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
POLYGON_API_KEY=your_actual_api_key_here
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
Quantity: 10 shares
Entry Price: $210.00
Current Price: $215.50
Unrealized P&L: $55.00
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
- **Position Size**: 10 shares per trade (configurable)
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
1. **Position Limits**: Maximum 10 shares per trade
2. **Daily Limits**: Configurable trade and loss limits
3. **Stop Losses**: Automatic risk management
4. **Emergency Stops**: Account-level protection
5. **Paper Trading**: Safe testing environment

### Recommended Settings for Beginners
```env
ENABLE_TRADING=false        # Start with paper trading
MAX_POSITION_SIZE=10        # Small position size
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

## ✅ Deployment Verification

Before going live, verify:
- [ ] All tests pass: `python test_setup.py`
- [ ] Paper trading works correctly
- [ ] Terminal monitor displays properly
- [ ] IBKR connection is stable
- [ ] Risk limits are appropriate
- [ ] Emergency procedures are understood

**Happy Trading! 🚀📈**

