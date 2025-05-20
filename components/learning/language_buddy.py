from reactpy import component, html, use_state, use_effect
import requests
import asyncio

LANGUAGES = [
    "English", "Spanish", "French", "German", "Italian", "Portuguese", "Russian",
    "Chinese", "Japanese", "Korean", "Arabic", "Hindi", "Dutch", "Turkish", "Polish",
    "Romanian", "Greek", "Swedish", "Czech", "Finnish", "Hebrew", "Hungarian",
    "Indonesian", "Norwegian", "Thai", "Ukrainian", "Vietnamese", "Other"
]
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
                    "If the user makes a mistake, gently correct it and explain why, but keep the conversation mostly in the target language."
                )},
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
            reply = resp.json()["choices"][0]["message"]["content"].strip()
            set_chat(lambda c: c + [("Buddy", reply)])
        except Exception as e:
            set_error(f"Error: {e}")
        set_is_typing(False)

    # Reset chat whenever setup options change
    use_effect(lambda: set_chat([]), [native_lang, target_lang, level, learning_time])

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
                            "onChange": lambda e: set_native_lang(e["target"]["value"]),
                        },
                        [html.option({"value": "", "disabled": True}, "Select...")]
                        + [html.option({"value": lang}, lang) for lang in LANGUAGES],
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
                        + [html.option({"value": lang}, lang) for lang in LANGUAGES],
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
                        "onChange": lambda e: set_learning_time(e["target"]["value"]),
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

            # --- Chat UI (no False leak) ---
            None if not started else html.div(
                {},
                # messages
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
                    # typing indicator only if typing
                    html.div({"className": "typing-indicator"}, 
                             html.span({"className": "dot"}), 
                             html.span({"className": "dot"}),
                             html.span({"className": "dot"}), 
                             html.span("Buddy is typing...")
                    ) if is_typing else None,
                ),
                # input + send
                html.div(
                    {"className": "input-form"},
                    html.input({
                        "type": "text",
                        "value": user_input,
                        "onChange": lambda e: set_user_input(e["target"]["value"]),
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
                    # error message if any
                    html.p({"className": "error-message"}, error) if error else None,
                )
            ),
        )
    )
