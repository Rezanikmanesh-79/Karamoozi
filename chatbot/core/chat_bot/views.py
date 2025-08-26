from decouple import config
from django.views.generic import TemplateView
from django.shortcuts import render
from langchain_openai import ChatOpenAI
import tiktoken


API_KEY = config("API_KEY")
API_URL = config("API_URL")  

MODEL_NAME = "gpt-4o-mini"

llm = ChatOpenAI(
    model=MODEL_NAME,
    base_url=API_URL,
    api_key=API_KEY,
)


class ChatView(TemplateView):
    template_name = "chat_bot/chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["response"] = None
        context["usage"] = None
        return context

    def post(self, request, *args, **kwargs):
        user_input = request.POST.get("user_input", "")
        response_text, usage_info = chat_with_bot(user_input)
        return render(request, self.template_name, {
            "response": response_text,
            "usage": usage_info,
            "user_input": user_input
        })


def num_tokens_from_messages(messages, model="gpt-4o-mini"):

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = 0
    for msg in messages:
        tokens += len(encoding.encode(msg["content"]))
    return tokens


def chat_with_bot(user_message: str):
    messages = [
        {"role": "system", "content": "You are a helpful assistant who answers in Persian."},
        {"role": "user", "content": user_message},
    ]

    try:
        response = llm.invoke(messages)
        assistant_reply = response.content

        prompt_tokens = num_tokens_from_messages(messages, MODEL_NAME)
        completion_tokens = len(tiktoken.encoding_for_model(MODEL_NAME).encode(assistant_reply))
        total_tokens = prompt_tokens + completion_tokens

        usage_info = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }

        return assistant_reply, usage_info

    except Exception as e:
        return None, {"error": str(e)}
