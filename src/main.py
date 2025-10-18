

#todo unmark it when finish bot

for stock in [test_stock]:
    stock_name = stock
    result = get_stock_data(stock, "2024-10-01", "2025-10-12")
    print(result)
    response = ask_nvidia_ai(result)
    print(response)


