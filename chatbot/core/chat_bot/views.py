import json
from pathlib import Path
from decouple import config
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.http import HttpResponse
import tiktoken
import markdown
from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage

# ================== تنظیمات ==================
API_KEY = config("API_KEY")
API_URL = config("API_URL")
MODEL_NAME = "gpt-4o-mini"
TARGET_WEB = "ehadish.com"
JSON_PATH = Path(__file__).resolve().parent.parent / "all_products.json"

# ================== بارگذاری داده محصولات ==================
try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        PRODUCTS_DATA = json.load(f)
except FileNotFoundError:
    PRODUCTS_DATA = []

# ================== راه‌انداز LLM ==================
llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=API_URL,
    api_key=API_KEY,
)

# ================== توکن‌شمار ==================
def num_tokens_from_messages(messages, model=MODEL_NAME):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return sum(len(encoding.encode(msg.content)) for msg in messages)

# ================== تبدیل متن Markdown به HTML ==================
def convert_markdown_to_html(text: str) -> str:
    return markdown.markdown(text)

# ================== چت با بات ==================
def chat_with_bot(user_message: str):
    # آماده‌سازی کانتکست محصولات
    products_context = "\n".join([
        f"- {p['title']} (قیمت: {p['price']} تومان) | لینک: https://{TARGET_WEB}{p['link']}"
        for p in PRODUCTS_DATA
    ]) or "فعلاً محصولی موجود نیست."

    messages = [
        SystemMessage(content=(
            f"شما دستیار پشتیبانی فروشگاه آنلاین {TARGET_WEB} هستید. "
            "همیشه باید به فارسی پاسخ دهید و مشتری را در خرید محصول راهنمایی کنید. "
            "اگر درباره محصولات سوال شد، فقط از لیست محصولات زیر استفاده کنید و توضیح دهید:\n\n"
            f"{products_context}"
        )),
        HumanMessage(content=user_message),
    ]

    try:
        response = llm.invoke(messages)
        assistant_reply = response.content.strip()
        assistant_reply_html = convert_markdown_to_html(assistant_reply)

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

# ================== ویو Django ==================
class ChatView(TemplateView):
    template_name = "chat_bot/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host"] = self.request.get_host()
        return context

    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_html, usage_info = chat_with_bot(user_input)
        html = render_to_string("chat_bot/message.html", {
            "user_input": user_input,
            "response": response_html
        })
        return HttpResponse(html)
