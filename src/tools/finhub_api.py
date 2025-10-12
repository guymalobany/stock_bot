import finnhub
import os



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



print("Getting {symbol} price...".format(symbol="AMD"))
print(get_stock_price("AMD"))

print("Getting {symbol} news...".format(symbol="AMD"))
print(get_stock_news_category("AMD", "2025-10-01", "2025-10-12"))

print("Getting {symbol} insider sentiment...".format(symbol="AMD"))
print(get_stock_insider_sentiment("AMD", "2024-10-01", "2025-10-12"))

