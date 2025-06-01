import os
import json
import asyncio
import aiohttp
from reactpy import component, html, use_state, use_effect

LANGUAGES_PATH = os.path.join(os.path.dirname(__file__), '../../static/assets/languages-en.json')
with open(LANGUAGES_PATH, encoding='utf-8') as f:
    LANGUAGES = json.load(f)

LEVELS = ["Beginner", "Intermediate", "Advanced", "Fluent"]

@component
def LanguageBuddy():
    native_lang, set_native_lang = use_state("")
    target_lang, set_target_lang = use_state("")
    level, set_level = use_state(LEVELS[0])
    learning_time, set_learning_time = use_state("")
    chat, set_chat = use_state([])           # list of (speaker, message)
    user_input, set_user_input = use_state("")
    is_typing, set_is_typing = use_state(False)
    error, set_error = use_state("")
    started, set_started = use_state(False)
    feedback, set_feedback = use_state("")

    def handle_start(_event=None):
        set_started(True)
        set_chat([])
        set_feedback("")
        set_error("")
        set_user_input("")

    def handle_send(_event=None):
        if not user_input.strip() or is_typing:
            return
        set_chat(chat + [("You", user_input)])
        set_is_typing(True)
        set_error("")
        asyncio.create_task(send_message(user_input))
        set_user_input("")

    def handle_keydown(e):
        if e.get("key") == "Enter" and not e.get("shiftKey") and not is_typing and user_input.strip():
            handle_send()

    async def send_message(msg):
        try:
            # Build chat history for context
            history = []
            for speaker, message in chat:
                if speaker == "You":
                    history.append({"role": "user", "content": message})
                else:
                    history.append({"role": "assistant", "content": message})
            # Add the new user message
            history.append({"role": "user", "content": msg})
            prompt = (
                f"You are a friendly AI language buddy. The user is a {level} learner of {target_lang}, "
                f"whose native language is {native_lang}. They have been learning for {learning_time}. "
                "Respond in the target language, keep it simple and encouraging, and correct mistakes gently. "
                "After your reply, provide a short feedback or suggestion for improvement. "
                "Format your response as follows: \n\n<reply>\n\nFEEDBACK: <feedback>. "
                "Do not use Markdown or HTML formatting."
            )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={
                        "messages": [
                            {"role": "system", "content": prompt},
                            *history
                        ],
                        "max_tokens": 400
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    # Split feedback if present
                    if "FEEDBACK:" in content:
                        reply, fb = content.split("FEEDBACK:", 1)
                        set_chat(chat + [("You", msg), (target_lang, reply.strip())])
                        set_feedback(fb.strip())
                    else:
                        set_chat(chat + [("You", msg), (target_lang, content.strip())])
                        set_feedback("")
        except Exception as e:
            set_error(f"Error: {e}")
        set_is_typing(False)

    # Reset chat whenever setup options change
    use_effect(lambda: set_chat([]), [native_lang, target_lang, level, learning_time])

    def render_language_option(lang):
        # lang is a dict with 'name', 'flag', and optionally 'code'
        code = lang.get("code")
        if not code:
            # fallback: use first two letters of name
            code = lang["name"][:2].upper() if len(lang["name"]) >= 2 else lang["name"].upper()
        return html.option({"value": lang["name"]}, f"{code} - {lang['flag']} {lang['name']}")

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/learning/language_buddy.css?v={CACHE_SUFFIX}"}),
        html.div(
            {"className": "home-btn-row"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "language-buddy chat-style"},
            html.h2("Language Buddy"),
            html.p({"className": "desc"}, "Practice your target language with an AI buddy!"),
            # --- Setup UI (no False leak) ---
            None if started else html.div(
                {"className": "setup-form"},
                # native language
                html.div(
                    {"className": "form-group"},
                    html.label({"htmlFor": "native-lang"}, "Your native language:"),
                    html.select(
                        {
                            "id": "native-lang",
                            "value": native_lang,
                            "onChange": lambda e: set_native_lang(e["target"]["value"]),
                        },
                        [html.option({"value": "", "disabled": True}, "Select...")]
                        + [render_language_option(lang) for lang in LANGUAGES],
                    ),
                ),
                # target language
                html.div(
                    {"className": "form-group"},
                    html.label({"htmlFor": "target-lang"}, "Language you want to learn:"),
                    html.select(
                        {
                            "id": "target-lang",
                            "value": target_lang,
                            "onChange": lambda e: set_target_lang(e["target"]["value"]),
                        },
                        [html.option({"value": "", "disabled": True}, "Select...")]
                        + [render_language_option(lang) for lang in LANGUAGES],
                    ),
                ),
                # level
                html.div(
                    {"className": "form-group"},
                    html.label({"htmlFor": "level"}, "Your level:"),
                    html.select(
                        {
                            "id": "level",
                            "value": level,
                            "onChange": lambda e: set_level(e["target"]["value"]),
                        },
                        [html.option({"value": l}, l) for l in LEVELS],
                    ),
                ),
                # learning time
                html.div(
                    {"className": "form-group"},
                    html.label({"htmlFor": "learning-time"}, "How long have you been learning?"),
                    html.input({
                        "id": "learning-time",
                        "type": "text",
                        "value": learning_time,
                        "onBlur": lambda e: set_learning_time(e["target"]["value"]),
                        "placeholder": "e.g. 6 months",
                    }),
                ),
                html.button(
                    {
                        "className": "btn btn-gradient",
                        "onClick": handle_start,
                        "disabled": not (native_lang and target_lang and learning_time) or is_typing,
                    },
                    "Start Chatting!"
                ),
            ),
            None if not started else html.div(
                {"className": "chat-feedback-row"},
                html.div(
                    {"className": "chat-col"},
                    html.div(
                        {"className": "chat-window"},
                        *[
                            html.div(
                                {"className": "chat-bubble user"} if speaker == "You"
                                else {"className": "chat-bubble buddy"},
                                html.div({"className": "bot-message"}, message)
                            )
                            for speaker, message in chat
                        ],
                        html.div({"className": "typing-indicator"}, 
                                 html.span({"className": "dot"}), 
                                 html.span({"className": "dot"}),
                                 html.span({"className": "dot"}), 
                                 html.span("Buddy is typing...")
                        ) if is_typing else None,
                    ),
                    html.div(
                        {"className": "input-form"},
                        html.input({
                            "type": "text",
                            "value": user_input,
                            "onBlur": lambda e: set_user_input(e["target"]["value"]),
                            "placeholder": f"Type in {target_lang}…",
                            "disabled": is_typing
                        }),
                        html.button(
                            {
                                "className": "btn btn-gradient",
                                "onClick": handle_send,
                                "disabled": is_typing,
                            },
                            "Send"
                        ),
                        html.p({"className": "error-message"}, error) if error else None,
                    ),
                ),
                html.div(
                    {"className": "feedback-col"},
                    html.div(
                        {"className": "feedback-box"},
                        html.label(
                            {"htmlFor": "feedback", "className": "feedback-label"},
                            "AI Feedback & Suggestions:"
                        ),
                        html.div(
                            {"className": "feedback-content", "id": "feedback"},
                            feedback or html.span({"style": {"color": "#888"}}, "Feedback and suggestions will appear here after you send a message.")
                        )
                    )
                )
            ),
        )
    )