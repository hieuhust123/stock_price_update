import os
from contextlib import redirect_stdout
import yfinance as yf
from datetime import datetime, time
import pytz 
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid
import pandas as pd

# --- Email Configuration ---
EMAIL_ENABLED = False  # Set to True to enable email sending
SMTP_SERVER = os.environ.get('SMTP_SERVER')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_TO = os.environ.get('EMAIL_TO')

class StockSummary:
    def __init__(self, tickers, stock_categories, timeframe="6d"):
        self.tickers = tickers
        self.stock_categories = stock_categories
        self.timeframe = timeframe  # e.g., '6d', '7d', '1mo'
        self.hist_data = None
        self.market_status = None
        self.now = datetime.now(pytz.timezone("US/Eastern"))
        self.generated_files = []  # For email attachments

    def get_market_status(self):
        """Determine the current US market status (pre-market, regular, post-market, closed)."""
        now = self.now
        if now.weekday() >= 5:
            return "closed"
        if time(4, 0) <= now.time() < time(9, 30):
            return "pre-market"
        elif time(9, 30) <= now.time() <= time(16, 0):
            return "regular"
        elif time(16, 0) < now.time() <= time(20, 0):
            return "post-market"
        else:
            return "closed"

    def fetch_historical_data(self):
        """Batch download historical data for all tickers using the specified timeframe."""
        self.hist_data = yf.download(self.tickers, period=self.timeframe, interval="1d", group_by="ticker", auto_adjust=True, threads=True)

    def print_market_header(self):
        """Print the market summary header."""
        print(f"\n📊 Stock Summary @ {self.now.strftime('%Y-%m-%d %H:%M:%S')} ({self.market_status.upper()})")
        print(f"Timeframe: {self.timeframe}")
        print("-" * 60)
        if self.market_status == "regular":
            print("Market is open. Today's price is not final!")
        elif self.market_status == "pre-market":
            print("Pre-market session. Prices are indicative.")
        elif self.market_status == "post-market":
            print("Post-market session. Prices are after-hours.")
        else:
            print("Market is closed.")
        print()

    def print_category_summaries(self):
        """Print summaries for each stock category and collect performance data."""
        performance_list = []
        for category, category_stocks in self.stock_categories.items():
            if not category_stocks:
                continue
            print(f"🔹 {category.upper()}")
            print("-" * 40)
            for ticker in category_stocks:
                try:
                    ticker_hist = self.hist_data[ticker]['Close'] if isinstance(self.hist_data.columns, pd.MultiIndex) else self.hist_data['Close']
                except KeyError:
                    print(f"  {ticker}: No data available.")
                    continue
                ticker_hist = ticker_hist.dropna()
                if len(ticker_hist) < 2:
                    print(f"  {ticker}: Not enough data.")
                    continue
                yesterday_close = ticker_hist.iloc[-2]
                today_close = ticker_hist.iloc[-1]
                # Fetch real-time price for all tickers
                try:
                    realtime_price = yf.Ticker(ticker).info.get("regularMarketPrice")
                except Exception:
                    realtime_price = None
                if realtime_price is not None:
                    price = realtime_price
                    price_type = "Real-time"
                else:
                    price = today_close
                    price_type = "Regular"
                # Calculate difference and percent change using the displayed price
                price_diff = price - yesterday_close
                percent_diff = (price_diff / yesterday_close) * 100
                direction = "🔼 UP" if price_diff > 0 else ("🔽 DOWN" if price_diff < 0 else "⏸️ NO CHANGE")
                if self.market_status in ["pre-market", "post-market"]:
                    try:
                        info = yf.Ticker(ticker).info
                        if self.market_status == "pre-market":
                            price = info.get("preMarketPrice") or info.get("regularMarketPrice") or today_close
                            price_type = "Pre-market"
                        elif self.market_status == "post-market":
                            price = info.get("postMarketPrice") or info.get("regularMarketPrice") or today_close
                            price_type = "Post-market"
                        price_diff = price - yesterday_close
                        percent_diff = (price_diff / yesterday_close) * 100
                        direction = "🔼 UP" if price_diff > 0 else ("🔽 DOWN" if price_diff < 0 else "⏸️ NO CHANGE")
                    except Exception:
                        pass
                price_str = f"${price:.2f}" if isinstance(price, (float, int)) else str(price)
                print(f"  {ticker}: {direction} | {price_type}: {price_str} | Δ ${price_diff:.2f} ({percent_diff:.2f}%)")
                perf_dict = {
                    'ticker': ticker,
                    'category': category,
                    'price_type': price_type,
                    'price': price,
                    'price_diff': price_diff,
                    'percent_diff': percent_diff,
                    'direction': direction
                }
                performance_list.append(perf_dict)
            print()
        return performance_list

    def print_top_performers(self, performance_list, n=3):
        """Print the top n best and worst performers by percent change."""
        if performance_list:
            topn = sorted(performance_list, key=lambda x: x['percent_diff'], reverse=True)[:n]
            bottomn = sorted(performance_list, key=lambda x: x['percent_diff'])[:n]
            print(f"🏆 Top {n} Best Performers:")
            for perf in topn:
                price_str = f"${perf['price']:.2f}" if isinstance(perf['price'], (float, int)) else str(perf['price'])
                print(f"  {perf['ticker']}: {perf['direction']} | {perf['price_type']}: {price_str} | Δ ${perf['price_diff']:.2f} ({perf['percent_diff']:.2f}%)")
            print(f"💔 Top {n} Worst Performers:")
            for perf in bottomn:
                price_str = f"${perf['price']:.2f}" if isinstance(perf['price'], (float, int)) else str(perf['price'])
                print(f"  {perf['ticker']}: {perf['direction']} | {perf['price_type']}: {price_str} | Δ ${perf['price_diff']:.2f} ({perf['percent_diff']:.2f}%)")

    def print_top_timeframe_performers(self, n=3):
        performance_tf = []
        for ticker in self.tickers:
            try:
                ticker_hist = self.hist_data[ticker]['Close'] if isinstance(self.hist_data.columns, pd.MultiIndex) else self.hist_data['Close']
            except KeyError:
                continue
            ticker_hist = ticker_hist.dropna()
            if len(ticker_hist) < 2:
                continue
            old_close = ticker_hist.iloc[0]
            new_close = ticker_hist.iloc[-1]
            price_diff = new_close - old_close
            percent_diff = (price_diff / old_close) * 100
            performance_tf.append({
                'ticker': ticker,
                'old_close': old_close,
                'new_close': new_close,
                'price_diff': price_diff,
                'percent_diff': percent_diff
            })
        if performance_tf:
            topn_tf = sorted(performance_tf, key=lambda x: x['percent_diff'], reverse=True)[:n]
            print(f"\n📈 Top {n} Best Performers (Timeframe: {self.timeframe}):")
            for perf in topn_tf:
                print(f"  {perf['ticker']}: Δ ${perf['price_diff']:.2f} ({perf['percent_diff']:.2f}%) | {perf['old_close']:.2f} → {perf['new_close']:.2f}")

    def run_summary(self, n=3):
        self.market_status = self.get_market_status()
        self.fetch_historical_data()
        self.print_market_header()
        performance_list = self.print_category_summaries()
        self.print_top_performers(performance_list, n=n)
        self.print_top_timeframe_performers(n=n)

# --- Script entry point ---

my_stocks = ['PLTR','HOOD','IONQ','TD','IBKR','ASML','AMD','AVGO','BULL','CEG','CRWD','CRWV','GE','MU','NRG','OKLO',
             'RBRK','RDDT','TSM','QUBT','NVDA','AMZN','JPM','ARM','BTC-USD','VST','GEV','META','AAPL','GOOGL','MSFT','AFRM','QBTS',
             'FTNT','BYDDY','IBM','CPNG','BABA','NFLX','SPOT','ANET','ORCL','UNH','AMAT']
             # ,'ETH-USD'

stock_categories = {
    'Magnificent 7': ['NVDA', 'AMZN','META','AAPL','GOOGL','MSFT','ORCL'],
    'AI': ['PLTR', 'RDDT','CRWV'],
    'Energy': ['CEG', 'VST', 'NRG', 'OKLO','GEV','GE'],
    'Chip': ['AMD','ARM', 'MU', 'TSM','AVGO','ASML','AMAT'],
    'Cybersecurity': ['CRWD', 'RBRK','FTNT','ANET'],
    'Fintech': ['HOOD', 'IBKR', 'BULL','AFRM'],
    'Bank': ['JPM','TD'],
    'EV':['BYDDY'],
    'Quantum':['QUBT','QBTS','IBM','IONQ'],
    'E-commerce':['CPNG','BABA','UNH'],
    'Entertainment':['SPOT','NFLX'],
    'Other': ['BTC-USD']
    # ,'ETH-USD'
    
}

now = datetime.now(pytz.timezone("US/Eastern"))
filename = f"stock_summary_{now.strftime('%Y-%m-%d_%H-%M-%S')}.txt"
output_path = os.path.join("stock_update_daily", filename)

def main():
    with open(output_path, "w", encoding="utf-8") as f, redirect_stdout(f):
        summary = StockSummary(my_stocks, stock_categories, timeframe="6d")
        summary.run_summary(n=3)
    # Also print to console
    summary = StockSummary(my_stocks, stock_categories, timeframe="6d")
    summary.run_summary(n=3)
    print(f"\nSummary saved to {output_path}")

if __name__ == "__main__":
    main()
