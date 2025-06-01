from reactpy import component, html, use_state
import json
import os
import asyncio

CHAR_MAP_PATH = os.path.join(os.path.dirname(__file__), '../../static/assets/characters/character_map.json')
with open(CHAR_MAP_PATH, encoding='utf-8') as f:
    CHAR_MAP = json.load(f)["shows"]

@component
def CharacterChat():
    selected_show, set_selected_show = use_state("")
    selected_char, set_selected_char = use_state("")
    chat, set_chat = use_state([])  # (speaker, message)
    user_input, set_user_input = use_state("")
    is_typing, set_is_typing = use_state(False)
    error, set_error = use_state("")
    started, set_started = use_state(False)

    def handle_start(_event=None):
        set_started(True)
        set_chat([])
        set_error("")

    async def send_message(msg):
        set_is_typing(True)
        set_error("")
        set_chat(lambda c: c + [("You", msg)])
        try:
            # Compose prompt for AI
            char_data = CHAR_MAP[selected_show]["characters"][selected_char]
            system_prompt = (
                f"You are roleplaying as {selected_char.capitalize()} from {selected_show.title()}. {char_data['personality_modifiers']} Stay in character."
                "Respond to the user's messages as if you were that character, using their unique speech patterns and personality traits."
                " If you don't know the answer, say 'I don't know' or 'I can't answer that'."
                f" Use the following information about {selected_char.capitalize()}: {char_data['personality_modifiers']}"
                "Respond in short-sized messages, and use emojis where appropriate."
            )
            user_prompt = msg
            import requests
            resp = requests.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ]
                },
                timeout=60
            )
            resp.raise_for_status()
            reply = resp.json()["choices"][0]["message"]["content"]
            set_chat(lambda c: c + [(selected_char, reply)])
        except Exception as e:
            set_error(f"AI error: {e}")
        set_is_typing(False)

    def handle_send(_event=None):
        msg = user_input.strip()
        if not msg or is_typing:
            return
        set_user_input("")
        asyncio.create_task(send_message(msg))

    def handle_keydown(e):
        if e.get("key") == "Enter" and not e.get("shiftKey"):
            handle_send()

    def render_char_option(char, char_data):
        return html.option({"value": char}, char.capitalize())

    def render_show_option(show):
        return html.option({"value": show}, show.title())

    def get_char_image():
        if selected_show and selected_char:
            img_path = CHAR_MAP[selected_show]["characters"][selected_char]["image"]
            if img_path.startswith("static/"):
                return "/" + img_path
            return img_path
        return None

    # Fix: Use class instead of className for HTML attributes
    from components.common.config import CACHE_SUFFIX
    #print("CACHE_SUFFIX is", CACHE_SUFFIX)
    return html.div(
        {},
        html.div({"class": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/character_chat.css?v={CACHE_SUFFIX}"}),
        html.div(
            {"class": "home-btn-row"},
            html.a({"href": "/", "class": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"class": "character-chat chat-style"},
            html.h2("Character Chat"),
            html.p({"class": "desc"}, "Chat with your favorite cartoon characters!"),
            None if started else html.div(
                {"class": "setup-form"},
                html.div(
                    {"class": "form-group"},
                    html.label({"htmlFor": "show-select"}, "Choose a show:"),
                    html.select(
                        {
                            "id": "show-select",
                            "value": selected_show,
                            "onChange": lambda e: set_selected_show(e["target"]["value"]),
                        },
                        [html.option({"value": "", "disabled": True}, "Select...")]
                        + [render_show_option(show) for show in CHAR_MAP.keys()]
                    ),
                ),
                html.div(
                    {"class": "form-group"},
                    html.label({"htmlFor": "char-select"}, "Choose a character:"),
                    html.select(
                        {
                            "id": "char-select",
                            "value": selected_char,
                            "onChange": lambda e: set_selected_char(e["target"]["value"]),
                            "disabled": not selected_show
                        },
                        [html.option({"value": "", "disabled": True}, "Select...")]
                        + ([render_char_option(char, data) for char, data in CHAR_MAP[selected_show]["characters"].items()] if selected_show else [])
                    ),
                ),
                html.button(
                    {
                        "class": "btn btn-gradient",
                        "onClick": handle_start,
                        "disabled": not (selected_show and selected_char),
                    },
                    "Start Chatting!"
                ),
            ),
            None if not started else html.div(
                {"class": "chat-col"},
                html.div(
                    {"class": "profile-header"},
                    get_char_image() and html.img({
                        "src": get_char_image(),
                        "class": "profile-pic",
                        "alt": selected_char,
                    }),
                    html.h3({"class": "profile-name"}, selected_char.capitalize() if selected_char else "")
                ),
                html.div(
                    {"class": "chat-window"},
                    *[
                        html.div(
                            {"class": "chat-bubble user"} if speaker == "You"
                            else {"class": "chat-bubble buddy"},
                            html.div({"class": "bot-message"}, message)
                        )
                        for speaker, message in chat
                    ],
                    html.div({"class": "typing-indicator"},
                        html.span({"class": "dot"}),
                        html.span({"class": "dot"}),
                        html.span({"class": "dot"}),
                        html.span(f"{selected_char.capitalize()} is typing...")
                    ) if is_typing else None,
                ),
                html.div(
                    {"class": "input-form"},
                    html.input({
                        "type": "text",
                        "value": user_input,
                        "onChange": lambda e: set_user_input(e["target"]["value"]),
                        "onBlur": lambda e: None,
                        "onKeyDown": handle_keydown,
                        "placeholder": f"Type to chat with {selected_char.capitalize()}…" if selected_char else "Type a message…",
                        "disabled": is_typing
                    }),
                    html.button(
                        {
                            "class": "btn btn-gradient",
                            "onClick": handle_send,
                            "disabled": not user_input.strip() or is_typing,
                        },
                        "Send"
                    ),
                    html.p({"class": "error-message"}, error) if error else None,
                ),
            ),
        )
    )