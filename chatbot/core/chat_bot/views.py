import json
from pathlib import Path
from decouple import config
from django.views.generic import TemplateView
from django.template.loader import render_to_string
from django.http import HttpResponse, StreamingHttpResponse
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

try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        PRODUCTS_DATA = json.load(f)
except FileNotFoundError:
    PRODUCTS_DATA = []

llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=API_URL,
    api_key=API_KEY,
)


# ================== توابع کمکی ==================
def num_tokens_from_messages(messages, model=MODEL_NAME):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return sum(len(encoding.encode(msg.content)) for msg in messages)


def convert_markdown_to_html(text: str) -> str:
    return markdown.markdown(text)


# ================== منطق اصلی ربات ==================
def build_messages(user_message: str):
    products_context = "\n".join([
        f"- {p['title']} (قیمت: {p['price']} تومان) | لینک: https://{TARGET_WEB}{p['link']}"
        for p in PRODUCTS_DATA
    ]) or "فعلاً محصولی موجود نیست."

    return [
        SystemMessage(content=(
            f"تو یک دستیار حرفه‌ای پشتیبانی برای فروشگاه آنلاین {TARGET_WEB} هستی. "
            "همیشه مودبانه و واضح به فارسی پاسخ بده. "
            "وظایف تو شامل پاسخ به سوالات مشتریان درباره خرید، پرداخت، پیگیری سفارش، بازگشت کالا و مشکلات احتمالی است. "
            "اگر سوال درباره مشخصات یا قابلیت‌های محصولات باشد، می‌توانی **با توجه به مشخصات سخت‌افزاری، پیش‌بینی تقریبی بدهی** که محصول برای کار خاصی مناسب است یا نه. "
            "مثلاً اگر مشتری بپرسد آیا لپ‌تاپ برای بازی یا کار خواستی X مناسب است، با توجه به CPU، GPU و RAM، راهنمایی تقریبی بده. "
            "همیشه تاکید کن که این پیش‌بینی تقریبی است و عملکرد واقعی ممکن است متفاوت باشد. "
            "لیست محصولات فروشگاه برای راهنمایی:\n\n"
            f"{products_context}\n\n"
            "اگر سوال خارج از محدوده فروشگاه یا محصولات باشد، فقط بگو که نمی‌توانی پاسخ بدهی و هیچ اطلاعاتی اضافه نده."
        )),
        HumanMessage(content=user_message),
    ]

def chat_with_bot(user_message: str):
    messages = build_messages(user_message)

    try:
        response = llm.invoke(messages)
        assistant_reply = response.content.strip()
        assistant_reply_html = convert_markdown_to_html(assistant_reply)

        prompt_tokens = num_tokens_from_messages(messages)
        completion_tokens = len(tiktoken.encoding_for_model(MODEL_NAME).encode(assistant_reply))
        usage_info = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens
        }

        return assistant_reply_html, usage_info
    except Exception as e:
        return f"<p style='color:red'>Error: {e}</p>", {"error": str(e)}


def chat_with_bot_stream(user_message: str):
    messages = build_messages(user_message)

    try:
        response_stream = llm.stream(messages)
        for chunk in response_stream:
            if chunk.content:
                yield convert_markdown_to_html(chunk.content)
    except Exception as e:
        yield f"<p style='color:red'>Error: {e}</p>"


# ================== ویوها ==================
class ChatView(TemplateView):
    template_name = "chat_bot/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["host"] = self.request.get_host()
        context["response"] = convert_markdown_to_html(
            "سلام! من ربات پشتیبانی سایت **ehadish.com** هستم.\n"
            "هر سوالی درباره ورود، پرداخت، سفارش‌ها یا محصولات دارید، در خدمتتونم."
        )
        return context

    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_html, usage_info = chat_with_bot(user_input)
        html = render_to_string("chat_bot/message.html", {
            "user_input": user_input,
            "response": response_html
        })
        return HttpResponse(html)


class ChatStreamView(TemplateView):
    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_stream = chat_with_bot_stream(user_input)
        return StreamingHttpResponse(response_stream, content_type="text/html; charset=utf-8")
