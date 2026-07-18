"""
NSE Data Fetch Module
Fetches historical stock data for NSE-listed companies using yfinance
Supports data ranging from available historical data (typically 10+ years) to present
"""

import os
import pandas as pd
import yfinance as yf
import logging
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def ist_now():
    return datetime.now(IST)

# Setup logging
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

nse_logger = logging.getLogger('nse_logger')
if not nse_logger.handlers:
    nse_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(os.path.join(log_dir, 'nse_fetch.log'))
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    nse_logger.addHandler(handler)

# Also add console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
nse_logger.addHandler(console_handler)


class NSEDataFetcher:
    """
    Fetches historical stock data for NSE-listed companies
    """
    
    def __init__(self, nse_list_path='NSE_LIST/stocks.csv'):
        """
        Initialize NSE Data Fetcher
        
        Args:
            nse_list_path (str): Path to the CSV file containing NSE stock list
        """
        self.nse_list_path = nse_list_path
        self.stocks_df = None
        self.base_dir = os.path.join(os.getcwd(), 'NSE')
        os.makedirs(self.base_dir, exist_ok=True)
        
    def load_stocks_list(self):
        """Load the list of stocks from CSV"""
        try:
            self.stocks_df = pd.read_csv(self.nse_list_path)
            nse_logger.info(f"Loaded {len(self.stocks_df)} stocks from NSE list")
            return self.stocks_df
        except Exception as e:
            nse_logger.error(f"Error loading NSE stocks list: {str(e)}")
            return None
    
    def fetch_stock_data(self, symbol, start_date=None, end_date=None, progress_callback=None):
        """
        Fetch historical data for a single stock with additional fundamental data
        
        Args:
            symbol (str): Stock symbol (e.g., 'RELIANCE')
            start_date (str): Start date in 'YYYY-MM-DD' format. If None, fetches from earliest available
            end_date (str): End date in 'YYYY-MM-DD' format. If None, uses today's date
            progress_callback (callable): Callback function to report progress
            
        Returns:
            pd.DataFrame: Historical stock data with additional fields or None if fetch failed
        """
        try:
            # NSE stocks use .NS suffix in yfinance
            ticker = f"{symbol}.NS"
            
            if end_date is None:
                end_date = ist_now().strftime('%Y-%m-%d')
            
            # If start_date is not specified, fetch from 15 years ago (maximum available data)
            if start_date is None:
                start_date = (ist_now() - timedelta(days=365*15)).strftime('%Y-%m-%d')
            
            nse_logger.info(f"Fetching data for {symbol} ({ticker}) from {start_date} to {end_date}")
            
            # Download historical data
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            
            if data is None or data.empty:
                nse_logger.warning(f"No data found for {symbol}")
                return None
            
            # Fetch additional info from ticker
            try:
                ticker_obj = yf.Ticker(ticker)
                info = ticker_obj.info
                
                # Add fundamental data columns (these will be same for all rows)
                data['Symbol'] = symbol
                data['PE_Ratio'] = info.get('trailingPE', '')
                data['Year_High'] = info.get('fiftyTwoWeekHigh', '')
                data['Year_Low'] = info.get('fiftyTwoWeekLow', '')
                data['Market_Cap'] = info.get('marketCap', '')
                data['Dividend_Yield'] = info.get('dividendYield', '')
                data['Beta'] = info.get('beta', '')
                data['Earnings_Per_Share'] = info.get('trailingEps', '')
                data['Book_Value'] = info.get('bookValue', '')
                data['Price_To_Book'] = info.get('priceToBook', '')
                data['ROE'] = info.get('returnOnEquity', '')
                data['Debt_To_Equity'] = info.get('debtToEquity', '')
                
                # Calculate change and percentage change
                data['Daily_Change'] = data['Close'] - data['Open']
                data['Daily_Change_Percent'] = ((data['Close'] - data['Open']) / data['Open'] * 100).round(2)
                
            except Exception as e:
                nse_logger.warning(f"Could not fetch additional info for {symbol}: {str(e)}")
                # Continue with basic data if additional fetch fails
                data['Symbol'] = symbol
            
            # Reorder columns to put symbol first
            cols = data.columns.tolist()
            if 'Symbol' in cols:
                cols.remove('Symbol')
                cols = ['Symbol'] + cols
                data = data[cols]
            
            nse_logger.info(f"Successfully fetched {len(data)} records for {symbol}")
            return data
            
        except Exception as e:
            nse_logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def save_stock_data_consolidated(self, symbol, data):
        """
        Save all stock data to a single consolidated CSV file
        
        Args:
            symbol (str): Stock symbol
            data (pd.DataFrame): Historical stock data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            symbol_dir = os.path.join(self.base_dir, symbol)
            os.makedirs(symbol_dir, exist_ok=True)
            
            filename = os.path.join(symbol_dir, f"{symbol}_consolidated.csv")
            file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
            data.to_csv(filename, mode='a' if file_exists else 'w', header=not file_exists)
            
            nse_logger.info(f"Saved consolidated data for {symbol} to {filename}")
            return True
            
        except Exception as e:
            nse_logger.error(f"Error saving consolidated data for {symbol}: {str(e)}")
            return False
    
    def fetch_all_stocks(self, start_date=None, end_date=None, progress_callback=None):
        """
        Fetch data for all stocks in the NSE list
        
        Args:
            start_date (str): Start date in 'YYYY-MM-DD' format
            end_date (str): End date in 'YYYY-MM-DD' format
            progress_callback (callable): Callback to report progress
            
        Returns:
            dict: Dictionary with results for each stock
        """
        if self.stocks_df is None:
            self.load_stocks_list()
        
        results = {}
        
        for idx, row in self.stocks_df.iterrows():
            symbol = row['Symbol']
            nse_logger.info(f"Processing {idx+1}/{len(self.stocks_df)}: {symbol}")
            
            # Fetch data
            data = self.fetch_stock_data(symbol, start_date, end_date, progress_callback)
            
            if data is not None:
                # Save consolidated data
                self.save_stock_data_consolidated(symbol, data)
                results[symbol] = {
                    'status': 'success',
                    'records': len(data),
                    'date_range': f"{data.index.min().date()} to {data.index.max().date()}"
                }
            else:
                results[symbol] = {
                    'status': 'failed',
                    'records': 0,
                    'date_range': None
                }
            
            if progress_callback:
                progress_callback(idx + 1, len(self.stocks_df), symbol)
        
        return results
    
    def get_fetch_summary(self, results):
        """Generate a summary of the fetch operation"""
        total = len(results)
        successful = sum(1 for r in results.values() if r['status'] == 'success')
        failed = total - successful
        
        summary = f"""
========== NSE Data Fetch Summary ==========
Total Stocks: {total}
Successfully Fetched: {successful}
Failed: {failed}
Success Rate: {(successful/total)*100:.1f}%
===============================================
"""
        nse_logger.info(summary)
        return summary


def get_nse_fetcher():
    """Factory function to get NSE fetcher instance"""
    return NSEDataFetcher()


if __name__ == "__main__":
    # Example usage
    fetcher = NSEDataFetcher()
    fetcher.load_stocks_list()
    
    # Fetch data for a single stock first to test
    nse_logger.info("Starting NSE data fetch...")
    results = fetcher.fetch_all_stocks()
    summary = fetcher.get_fetch_summary(results)
    print(summary)





















