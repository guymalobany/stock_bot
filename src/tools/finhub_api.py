import finnhub
import os
from time import sleep
from datetime import datetime, timedelta
import pandas as pd
from tabulate import tabulate

#Finhub Sub Function's
def get_finhub_client():
    return finnhub.Client(api_key=os.getenv("FINHUB_API_KEY"))


def check_stock_symbol(symbol):
    client = get_finhub_client()
    return client.symbol_lookup(symbol)

def create_table_result_for_symbol_lookup(data):
    """
    Converts JSON response into a neat fixed-width plain table suitable for Telegram.
    Only keeps 'description' and 'symbol'.
    """
    if not data.get('result'):
        return "Sorry, no similar tickers found."
    
    df = pd.DataFrame(data['result'])
    
    if df.empty:
        return "Sorry, no similar tickers found."
    
    # Keep only necessary columns
    df = df[['description', 'symbol']]
    
    # Optional: reset index
    df.index = range(1, len(df) + 1)
    
    # Convert to plain table using tabulate
    plain_table = tabulate(df, headers=['Description', 'Symbol'], tablefmt='plain', showindex=False)
    
    # Wrap in Telegram monospace for neat display
    telegram_table = f"```\n{plain_table}\n```"
    
    return telegram_table


def get_stock_price(symbol):
    client = get_finhub_client()
    return client.quote(symbol)

def get_stock_news_category(symbol, start_date, end_date):
    client = get_finhub_client()
    return client.company_news(symbol, _from=start_date, to=end_date)

def get_stock_insider_sentiment(symbol, start_date, end_date):
    client = get_finhub_client()
    return client.stock_insider_sentiment(symbol, start_date, end_date)

def get_general_market_news():
    client = get_finhub_client()
    client.general_news('general', min_id=0)


# Checking Tools
def is_empty_price(data):
    # Check if all numeric price fields are zero or None
    numeric_fields = ['c', 'h', 'l', 'o', 'pc']
    return all(data.get(f) in [0, None] for f in numeric_fields)

# Main function's
def get_stock_data(symbol, start_date, end_date):
        client = get_finhub_client()

        # Honor provided date range; fallback to last 14 days on invalid input
        try:
            from_date = datetime.fromisoformat(start_date).date()
            to_date = datetime.fromisoformat(end_date).date()
        except Exception:
            to_date = datetime.utcnow().date()  # pyright: ignore[reportDeprecated]
            from_date = to_date - timedelta(days=14)

        print(f"Getting {symbol} price...")
        price = client.quote(symbol)
        # checking if the price is empty, and return correct message
        if is_empty_price(price):
            similar_stock = create_table_result_for_symbol_lookup(check_stock_symbol(symbol))
            result = f"Sorry, no stock with the name provided have found please see the bellow suggestion \n {similar_stock}."
            return result
        print(price)
        print(f"Getting {symbol} news...")
        news = client.company_news(symbol, _from=from_date.isoformat(), to=to_date.isoformat())
        # Optional: limit and simplify news
        news = news[:10] if isinstance(news, list) else news

        print(f"Getting {symbol} insider sentiment...")
        insider = client.stock_insider_sentiment(symbol, from_date.isoformat(), to_date.isoformat())
        # Fallback: if empty, expand window to last 90 days
        try:
            empty = (
                insider is None or
                (isinstance(insider, dict) and not insider.get('data')) or
                (isinstance(insider, list) and len(insider) == 0)
            )
            if empty:
                alt_from = (to_date - timedelta(days=90)).isoformat()
                insider = client.stock_insider_sentiment(symbol, alt_from, to_date.isoformat())
        except Exception:
            pass

        print(f"Getting SPY price")
        spy = client.quote("SPY")

        print(f"Getting SPY Market sentiment...")
        insider_market = client.stock_insider_sentiment("SPY", from_date.isoformat(), to_date.isoformat())
        try:
            empty_market = (
                insider_market is None or
                (isinstance(insider_market, dict) and not insider_market.get('data')) or
                (isinstance(insider_market, list) and len(insider_market) == 0)
            )
            if empty_market:
                alt_from_m = (to_date - timedelta(days=90)).isoformat()
                insider_market = client.stock_insider_sentiment("SPY", alt_from_m, to_date.isoformat())
        except Exception:
            pass

        print(f"Getting SPY news...")
        market_news = client.company_news("SPY", _from=from_date.isoformat(), to=to_date.isoformat())

        print("General Market news...")
        general_news = client.general_news('general', min_id=0)
        return {
            "symbol": symbol,
            "price": price,
            "news": news,
            "insider_sentiment": insider,
            "date_range": {"from": from_date.isoformat(), "to": to_date.isoformat()},
            "Market": spy,
            "Market news": market_news,
            "insider_market": insider_market,
            "General_market_news": general_news
        }



def get_latest_company_news_last_two_weeks(symbol, limit=20):
        client = get_finhub_client()

        to_date = datetime.utcnow().date()
        from_date = to_date - timedelta(days=14)

        news = client.company_news(symbol, _from=from_date.isoformat(), to=to_date.isoformat())

        if isinstance(news, list) and limit:
                return news[:limit]
        return news

