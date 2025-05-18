from reactpy import component, html, use_state, use_effect
import requests
import json
import markdown
import asyncio

@component
def BotVsBotRoastBattle():
    topic, set_topic = use_state("")
    chat, set_chat = use_state([])  # List of (speaker, message)
    is_typing, set_is_typing = use_state(False)
    started, set_started = use_state(False)
    error, set_error = use_state("")

    async def roast_battle():
        set_chat([])
        set_error("")
        set_is_typing(True)
        bot1 = "Bot Alpha"
        bot2 = "Bot Beta"
        bots = [bot1, bot2]
        messages = [
            {"role": "system", "content": (
                "You are two witty, clever, and friendly AI bots having a roast battle. "
                "You must never use profanity or offensive language. "
                "Each bot should roast the other in a fun, creative, and clever way, but always keep it clean. "
                "Each message should be a single roast, and the bots should take turns. "
                "The topic is: " + topic + ". "
                "Each bot should have a unique style. "
                "Output only the roast for your turn, no extra comments."
            )}
        ]
        for turn in range(20):
            bot = bots[turn % 2]
            user_prompt = (
                f"{bot}, it's your turn. Roast your opponent about '{topic}'. "
                "Do not repeat previous jokes. Keep it clever, clean, and funny."
            )
            messages.append({"role": "user", "content": user_prompt})
            try:
                resp = requests.post(
                    "https://ai.hackclub.com/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "messages": messages[-3:],  # Only send last 3 for context
                        "max_tokens": 120
                    },
                    timeout=60
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"AI model returned {resp.status_code}")
                data = resp.json()
                roast = data["choices"][0]["message"]["content"].strip()
                set_chat(lambda c: c + [(bot, roast)])
                set_is_typing(True)
                await asyncio.sleep(1.2 + 0.5 * (turn % 2))  # Simulate typing
                set_is_typing(False)
            except Exception as e:
                set_error(f"Error: {e}")
                break
        set_is_typing(False)

    def handle_start(event):
        set_started(True)
        asyncio.create_task(roast_battle())

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/roast_battle.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "recipe-maker chat-style"},
            html.h2("Bot Vs Bot AI Roast Battle"),
            html.p({"style": {"fontSize": "1.1rem", "marginBottom": "1.5rem"}},
                   "Enter a topic and watch two friendly bots roast each other! No profanity, just clever fun."),
            html.div(
                {"className": "form-group"},
                html.label({"for": "topic"}, "Roast Topic:"),
                html.input({
                    "id": "topic", "type": "text", "value": topic,
                    "placeholder": "e.g. programming, pizza, Mondays",
                    "onChange": lambda e: set_topic(e["target"]["value"]),
                    "disabled": started
                }),
            ),
            html.button(
                {"className": "btn btn-primary", "onClick": handle_start, "disabled": started or not topic.strip()},
                "Start Roast Battle"
            ),
            html.div(
                {"className": "chat-window"},
                [
                    html.div({"className": f"chat-bubble {('bot1' if speaker == 'Bot Alpha' else 'bot2')}"},
                             html.strong(f"{speaker}: "),
                             html.span({"dangerouslySetInnerHTML": {"__html": markdown.markdown(msg)}})
                    ) for speaker, msg in chat
                ],
                is_typing and html.div({"className": "typing-indicator"},
                                      html.span({"className": "dot"}),
                                      html.span({"className": "dot"}),
                                      html.span({"className": "dot"}),
                                      html.span("Bot is typing...")
                )
            ),
            error and html.p({"style": {"color": "red"}}, error)
        )
    )
