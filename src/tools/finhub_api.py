import finnhub
import os
from time import sleep
from setting import watchlist

def get_finhub_client():
    return finnhub.Client(api_key=os.getenv("FINHUB_API_KEY"))

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


def get_stock_data(symbol, start_date, end_date):
        client = get_finhub_client()

        print(f"Getting {symbol} price...")
        price = client.quote(symbol)

        print(f"Getting {symbol} news...")
        news = client.company_news(symbol, _from=start_date, to=end_date)
        # Optional: limit and simplify news
        news = news[:10] if isinstance(news, list) else news

        print(f"Getting {symbol} insider sentiment...")
        insider = client.stock_insider_sentiment(symbol, start_date, end_date)

        print(f"Getting SPY price")
        spy = client.quote("SPY")

        print(f"Getting SPY Market sentiment...")
        insider_market = client.stock_insider_sentiment("SPY", start_date, end_date)

        print(f"Getting SPY news...")
        market_news = client.company_news("SPY", _from=start_date, to=end_date)

        print("General Market news...")
        general_news = client.general_news('general', min_id=0)
        

        print
        return {
            "symbol": symbol,
            "price": price,
            "news": news,
            "insider_sentiment": insider,
            "date_range": {"from": start_date, "to": end_date},
            "Market": spy,
            "Market news": market_news,
            "insider_market": insider_market,
            "General_market_news": general_news
        }


