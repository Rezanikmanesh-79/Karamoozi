import json
from decouple import config
from django.views.generic import TemplateView
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpResponse
from langchain_openai import ChatOpenAI
import tiktoken
from pathlib import Path

# ==== تنظیمات اصلی ====
API_KEY = config("API_KEY")
API_URL = config("API_URL")
MODEL_NAME = "gpt-4o-mini"
TARGET_WEB = "ehadish.com"
JSON_PATH = Path(__file__).resolve().parent.parent / "all_products.json"

# ==== بارگذاری JSON یک بار در حافظه ====
try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        PRODUCTS_DATA = json.load(f)
except FileNotFoundError:
    PRODUCTS_DATA = []

# ==== راه‌انداز LLM ====
llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=API_URL,
    api_key=API_KEY,
)

# ==== توکن‌شماری ====
def num_tokens_from_messages(messages, model=MODEL_NAME):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return sum(len(encoding.encode(msg["content"])) for msg in messages)

# ==== متد اصلی چت با LLM ====
def chat_with_bot(user_message: str):
    messages = [
        {
            "role": "system",
            "content": (
                f"You are the support assistant of the online store {TARGET_WEB}. "
                "Only answer questions related to login/signup, payments, orders, products, and customer support. "
                "Always respond in Persian. "
                f"Here is the product list (JSON): {json.dumps(PRODUCTS_DATA)}"
            ),
        },
        {"role": "user", "content": user_message},
    ]

    try:
        response = llm.invoke(messages)
        assistant_reply = response.content

        # محاسبه توکن‌ها
        prompt_tokens = num_tokens_from_messages(messages)
        completion_tokens = len(tiktoken.encoding_for_model(MODEL_NAME).encode(assistant_reply))
        usage_info = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }

        return assistant_reply, usage_info

    except Exception as e:
        return None, {"error": str(e)}

# ==== ویو اصلی ====
class ChatView(TemplateView):
    template_name = "chat_bot/chat.html"

    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_text, usage_info = chat_with_bot(user_input)

        # فقط قطعه پیام رو برگردونیم
        html = render_to_string("chat_bot/message.html", {
            "user_input": user_input,
            "response": response_text
        })
        return HttpResponse(html)
