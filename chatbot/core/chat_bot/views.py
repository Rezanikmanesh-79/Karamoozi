from decouple import config
import requests
from django.views.generic import TemplateView
from django.shortcuts import render

API_KEY = config("API_KEY")
API_URL = config("API_URL")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}


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

def chat_with_bot(user_message):
    data = {
        "model": "gpt-4.1",
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    response = requests.post(API_URL, headers=HEADERS, json=data)

    if response.status_code == 200:
        response_json = response.json()
        assistant_reply = response_json["choices"][0]["message"]["content"]
        usage_info = response_json.get("usage", {})
        return assistant_reply, usage_info
    else:
        return None, {"error": response.text}
