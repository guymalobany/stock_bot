from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
import json
import asyncio
from datetime import datetime, timedelta
from finhub_api import get_stock_data

short_system_prompt = """
You are Beerski — a precise, no-nonsense financial assistant.

Mapping Rating Emoji Rules:
- 4–5: 🚀 (positive)
- 3 😐 (neutral)
- 1–2: 🔻 (negative)

Your ONLY task is to output in the EXACT format below:

Stock Rating
================
Stock name: <stock_name>: <rating>/5 

Rating Reasoning
==================
<concise reasoning in Markdown, with emojis 😊👍🎨>
<emoji>

Rules:
- If data is empty like stock price and news or insufficient,reply politely:
  "Sorry, I currently don’t have enough data to provide a rating."
- NEVER write anything outside this format.
- NEVER apologize or explain beyond what’s required.
- Keep tone confident, friendly, and professional.
- NEVER estimete stock if it has empty result values, don't relay on the stock market SPY in this case.
"""

system_prompt = """
You are Beerski, a helpful financial assistant that analyzes stock data and provides investment recommendations.

You will receive the following information:
- Stock news
- Price history
- Insider sentiment
- Market status (SPY — represents the top 500 companies)

Your task is to analyze this data and determine whether the stock is a good investment.

Output Format:
Mandatory! Try to be prcise  for each section no more then 2-3 row
Please provide a summary of X, formatted in Markdown with appropriate headings
Add related emojis 😊, so the output will be more friendly 👍. Also, the indicator should use colors 🎨
Based on the provided data, here is the analysis for "{{Stock Name}}":

Stock News:
{{Your analysis of the stock-related news}}

Insider Sentiment:
{{Your analysis of insider trading or sentiment data}}

Price History:
{{Your interpretation of recent stock price trends}}

Market Status (SPY):
{{Current SPY performance and relevance to this stock}}

Market Trend:
{{Your analysis of the overall market direction}}

Market News:
{{Important market-wide updates affecting the stock}}

Rating Breakdown:
{{Explain key factors that influenced your rating}}

Color Indicator:
Green (Buy): Rating 4–5
Yellow (Hold): Rating 3
Red (Sell): Rating 1–2

Summary:
{{Short final recommendation — concise and decisive}}

Guidelines:
- Base your reasoning on the combined influence of stock news, insider sentiment, price history, and overall market trends.
- Always provide a rating from 1 to 5.
- Use clear, professional language and concise explanations.
- Mandatory! Try to be prcise  for each section no more then 2-3 row
"""

def get_nvidia_ai_client():
    return ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",  # consider switching to a known-good model for your account
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0.0,
        max_tokens=800,
    )


def _build_template(system_prompt):
    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + "\nUse insider_sentiment explicitly in your reasoning and final output."),
            ("user", "Analyze the following structured stock data:\n\n{user_input}")
        ]
    )


def _to_user_input(data) -> str:
    if isinstance(data, (dict, list)):
        return json.dumps(data, ensure_ascii=False, indent=2)
    return str(data)


def ask_nvidia_ai(user_input,system_prompt):
    template = _build_template(system_prompt)
    client = get_nvidia_ai_client()
    chain = template | client | StrOutputParser()
    return chain.invoke({"user_input": _to_user_input(user_input)}).strip()


def prepare_stock_data(symbol: str):
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=365)
    return get_stock_data(symbol, from_date.isoformat(), to_date.isoformat())


def analyze_from_data(data,system_prompt) -> str:
    return ask_nvidia_ai(data,system_prompt)

def get_stock_info(symbol: str) -> str:
    try:
        data = prepare_stock_data(symbol)
        response = analyze_from_data(data)
        return response
    except Exception as exc:
        return f"⚠️ Failed to fetch analysis for '{symbol}': {exc}"
