from tools.finhub_api import get_stock_data
from setting import watchlist,test_stock
from tools.ai import ask_nvidia_ai
from time import sleep

for stock in [test_stock]:
    stock_name = stock
    result = get_stock_data(stock, "2024-10-01", "2025-10-12")
    print(result)
    response = ask_nvidia_ai(result)
    print(response)