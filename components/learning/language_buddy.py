from reactpy import component, html, use_state, use_effect
import requests
import asyncio
import json
import os

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
        set_error("")

    def handle_send(_event=None):
        msg = user_input.strip()
        if not msg or is_typing:
            return
        set_user_input("")
        asyncio.create_task(send_message(msg))

    def handle_keydown(e):
        # If user hits Enter (and not Shift+Enter), send
        if e.get("key") == "Enter" and not e.get("shiftKey"):
            handle_send()

    async def send_message(msg):
        set_is_typing(True)
        set_error("")
        set_chat(lambda c: c + [("You", msg)])
        payload = {
            "messages": [
                {"role": "system", "content": (
                    f"You are a friendly language learning buddy. The user is a {level} "
                    f"in {target_lang} (native: {native_lang}), and has been learning for "
                    f"{learning_time or 'an unknown amount of'} time. Help them practice, "
                    "correct mistakes, and encourage them. Keep it fun and supportive. "
                    "Chat with the user primarily in the target language, at a level appropriate for their skills. "
                    "Only use their native language to explain something if they are clearly confused or ask for clarification. "
                    "Do not mix languages in the same sentence unless absolutely necessary for understanding. "
                    "If the user makes a mistake, gently correct it and explain why, but keep the conversation mostly in the target language.\n"
                    "When you reply, always return a JSON object with two fields: 'reply' (your chat message in the target language) and 'feedback' \n"
                    "(a short, friendly tip or correction for the user, focusing on how they can improve their language skills, such as grammar, vocabulary, or pronunciation. \n"
                    "Do NOT provide possible responses to the user's question; only give feedback on their language use and how to improve their typing or writing in the target language. \n"
                    "Give the feedback in the user's native language, but do not use it in your chat message. \n"
                    "Example: {\"reply\": \"Salut! Cum te simti azi?\", \"feedback\": \"Great job using the present tense! Try to use accents correctly in future messages.\"}")
                },
                *[
                    {
                        "role": "user" if speaker == "You" else "assistant",
                        "content": message
                    }
                    for speaker, message in chat + [("You", msg)]
                ]
            ],
            "max_tokens": 180
        }
        try:
            resp = requests.post(
                "https://ai.hackclub.com/chat/completions",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            import re
            # Extract the first JSON object from the response
            match = re.search(r'\{.*?\}', content, re.DOTALL)
            if match:
                json_str = match.group(0)
                try:
                    data = json.loads(json_str)
                    reply = data.get("reply", "")
                    feedback_msg = data.get("feedback", "")
                except Exception:
                    reply = content
                    feedback_msg = ""
            else:
                reply = content
                feedback_msg = ""
            set_chat(lambda c: c + [("Buddy", reply)])
            set_feedback(feedback_msg)
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

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/language_buddy.css"}),
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
                            "onBlur": lambda e: set_native_lang(e["target"]["value"]),
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
                            "onBlur": lambda e: set_target_lang(e["target"]["value"]),
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
                            "onBlur": lambda e: set_level(e["target"]["value"]),
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
                # start button
                html.button(
                    {
                        "className": "btn btn-gradient",
                        "onClick": handle_start,
                        "disabled": not (native_lang and target_lang and learning_time),
                    },
                    "Start Chatting!"
                ),
            ),
            # --- Chat + Feedback UI ---
            None if not started else html.div(
                {"className": "chat-feedback-row"},
                # Chat window and input
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
                            "onChange": lambda e: set_user_input(e["target"]["value"]),
                            "onBlur": lambda e: None,  # Keep onBlur for future logic if needed
                            "onKeyDown": handle_keydown,
                            "placeholder": f"Type in {target_lang}…",
                            "disabled": is_typing
                        }),
                        html.button(
                            {
                                "className": "btn btn-gradient",
                                "onClick": handle_send,
                                "disabled": not user_input.strip() or is_typing,
                            },
                            "Send"
                        ),
                        html.p({"className": "error-message"}, error) if error else None,
                    ),
                ),
                # Feedback Box (separate column on desktop, below on mobile)
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