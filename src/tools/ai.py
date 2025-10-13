from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
import os
from time import sleep
import json

system_prompt ="""
    You are a helpful assistant named beerski that can answer questions and help with tasks.
    You will be given with the following data:
    - stock news
    - price history
    - insider sentiment
    

    You need to analyze the stock news, insider sentiment, and price history to determine the best stock to invest in.
    You will receive the curernt Market status 500 biggest compeny as SPY, please relay on this infromation as another indicator you have .
    You should output your result as follow:
    First line - Based on the provided data, here is the analysis for "Stock":
    *Stock News:*
    *Insider Sentiment:*
    *Price History:*
    *Market Status:*
    *Market Trend:*
    *Market News:*
    *Rating Breakdown:*
    *Color Indicator:*
    *Summary:*

    Please suggest rating from 1 to 5.
    Also :
    Green : Buy - 4 to 5
    Yellow : Hold 3
    Red : Sale 2 and bellow
    """



import json

def get_nvidia_ai_client():
    return ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",  # consider switching to a known-good model for your account
        api_key=os.getenv("NVIDIA_API_KEY"),
        temperature=0.2,
        max_tokens=800,
    )


def ask_nvidia_ai(user_input):
    # Ensure user_input is a readable string; pretty-print JSON if dict/list.
    if isinstance(user_input, (dict, list)):
        user_input_str = json.dumps(user_input, ensure_ascii=False, indent=2)
    else:
        user_input_str = str(user_input)

    template = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + "\nUse insider_sentiment explicitly in your reasoning and final output."),
            ("user", "Analyze the following structured stock data:\n\n{user_input}")
        ]
    )

    client = get_nvidia_ai_client()
    chain = template | client | StrOutputParser()
    return chain.invoke({"user_input": user_input_str}).strip()
    