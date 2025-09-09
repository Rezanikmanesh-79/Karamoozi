import json
import re
from decouple import config
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.http import HttpResponse
from langchain_openai import ChatOpenAI
import tiktoken
from pathlib import Path
import markdown


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


# ==== ساخت لینک Markdown از JSON ====
def format_product(product: dict) -> str:
    link = product['link']
    # اگر لینک نسبی بود، کاملش کن
    if not link.startswith("http"):
        link = f"https://{TARGET_WEB}{link}"
    return f"[{product['title']}]({link}) - قیمت: {product['price']} تومان"


def inject_products_into_text(text: str) -> str:
    """
    هر محصولی که تو JSON داریم رو با فرمت Markdown به متن اضافه می‌کنیم
    (این مرحله می‌تونه customize بشه بر اساس نوع جواب بات).
    """
    formatted = []
    for product in PRODUCTS_DATA[:5]:  # 👈 مثلا فقط ۵ محصول اول
        formatted.append(format_product(product))
    if formatted:
        text += "\n\n📦 محصولات پیشنهادی:\n" + "\n".join([f"- {p}" for p in formatted])
    return text


# ==== تبدیل Markdown به HTML ====
def convert_markdown_to_html(text: str) -> str:
    return markdown.markdown(text)


# ==== متد اصلی چت با LLM ====
def chat_with_bot(user_message: str):
    messages = [
        {
            "role": "system",
            "content": (
                f"You are the support assistant of the online store {TARGET_WEB}. "
                "Only answer questions related to login/signup, payments, orders, products, and customer support. "
                "Always respond in Persian."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    try:
        response = llm.invoke(messages)
        assistant_reply = response.content.strip()

        # 👇 محصولات JSON رو به متن بات تزریق می‌کنیم
        enriched_text = inject_products_into_text(assistant_reply)

        # 👇 Markdown → HTML
        assistant_reply_html = convert_markdown_to_html(enriched_text)

        # محاسبه توکن‌ها
        prompt_tokens = num_tokens_from_messages(messages)
        completion_tokens = len(tiktoken.encoding_for_model(MODEL_NAME).encode(assistant_reply))
        usage_info = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }

        return assistant_reply_html, usage_info

    except Exception as e:
        return None, {"error": str(e)}


# ==== ویو اصلی ====
class ChatView(TemplateView):
    template_name = "chat_bot/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host"] = self.request.get_host()
        return context

    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_html, usage_info = chat_with_bot(user_input)

        # پیام کاربر + پیام بات
        html = render_to_string("chat_bot/message.html", {
            "user_input": user_input,
            "response": response_html
        })
        return HttpResponse(html)
