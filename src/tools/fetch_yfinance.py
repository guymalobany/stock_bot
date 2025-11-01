from math import e
import yfinance as yf
import pandas as pd
import requests
import time
import os
import logging
# Telegram bot info
TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("TG_ALLOWED_IDS", "")
symbols = ["NVDA","AMD","SPY","APPL","AMZN","RGTI","NIO","RBLX"]

def high_stock_scan(symbols):
    for sy in symbols:
        print(f"Proccessing STOCK: {sy}")
    # Download 14 days of 5-min interval data
        try:
            data = yf.download(sy, period="14d", interval="5m", prepost=False, progress=False)
            time.sleep(1)
            if data.empty is True: # check if dataframe is empty has API can send back empty result
                print("Empty Data")
                continue
        except Exception as e:
            logging.error(f"Data fetch for STOCK: {sy} has falied - Error details : {e} ")



        # Flatten MultiIndex if needed
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]

        # Find highest high
        max_high = data["High"].max()
        max_time = data["High"].idxmax()

        # Check the last candle
        last_high = data["High"].iloc[-1]
        last_time = data.index[-1]

        # Function to send Telegram message
        def send_telegram(msg,chat):
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            payload = {"chat_id": chat, "text": msg}
            requests.post(url, data=payload)

        # Notify if the last candle broke the high
        if last_high >= max_high:
            message = f"🚀 {sy} hit a new 14-day high!\nHigh: {last_high:.2f} at {last_time}"
            for chat in CHAT_ID:
                print(chat)
                send_telegram(message,chat)
                print("Notification sent!")
                time.sleep(3)
        else:
            print(f"Last candle high: {last_high:.2f}, 14 days max High: {max_high}, overall no new high.")


if __name__ == "__main__":
    while True:
        high_stock_scan(symbols)
        print("Entering Sleep mode for 2 Hours")
        # Sleep for 2 hours (2 hours  * 60 minutes/hour * 60 seconds/minute)
        time.sleep(2 * 60 * 60)
    
