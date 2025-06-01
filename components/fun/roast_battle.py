from reactpy import component, html, use_state, use_effect, use_ref
import requests
import markdown
import asyncio

@component
def BotVsBotRoastBattle():
    topic, set_topic = use_state("")
    chat, set_chat = use_state([])  # list of (speaker, message)
    is_typing, set_is_typing = use_state(False)
    started, set_started = use_state(False)
    error, set_error = use_state("")

    cancel_ref = use_ref(False)
    task_ref = use_ref(None)

    async def roast_battle(cancel_ref):
        import aiohttp
        set_chat([])
        set_error("")
        set_is_typing(True)
        bot1 = "Bot Alpha"
        bot2 = "Bot Beta"
        system_msg = {
            "role": "system",
            "content": (
                "You are two witty, clever, and friendly AI bots having a roast battle. "
                "You must never use profanity or offensive language. "
                "Each bot should argue with each other in a fun, creative, and clever way, "
                "but always keep it clean. Each message should be a single roast, "
                "and the bots should take turns. Output only your roast—keep it punchy (1-2 lines)."
                "If the input is something versus something, each bot should take the side of one of the two things. "
                "If the input is a single thing, each bot should take a different side of that thing. "
            )
        }
        history = []
        for turn in range(20):
            if cancel_ref.current:
                break
            bot = [bot1, bot2][turn % 2]
            context = [
                {"role": "assistant" if spk == bot else "user", "content": msg}
                for spk, msg in history
            ]
            prompt = (
                f"{bot}, it's your turn to roast your opponent on “{topic}”. "
                "Do not repeat previous jokes. Keep it clever, clean, and punchy."
            )
            payload = [system_msg] + context + [{"role": "user", "content": prompt}]
            try:
                if cancel_ref.current:
                    break
                set_is_typing(True)
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://ai.hackclub.com/chat/completions",
                        json={"messages": payload, "max_tokens": 120},
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                if cancel_ref.current:
                    break
                roast = data["choices"][0]["message"]["content"].strip()
                set_chat(lambda c: c + [(bot, roast)])
                history.append((bot, roast))
                await asyncio.sleep(3.5 + 1.2 * (turn % 2))
                set_is_typing(False)
            except Exception as e:
                if not cancel_ref.current:
                    set_error(f"Error: {e}")
                    set_is_typing(False)
                break
        set_is_typing(False)
        set_started(False)

    def handle_start(event):
        set_started(True)
        cancel_ref.current = False
        coro = roast_battle(cancel_ref)
        task = asyncio.create_task(coro)
        task_ref.current = task

    def cancel_battle():
        cancel_ref.current = True
        set_is_typing(False)
        set_started(False)

    use_effect(
        lambda: (
            lambda: cancel_battle()
        ),
        []
    )

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        # background blur
        html.div({"className": "background-gradient-blur"}),

        # stylesheet
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/roast_battle.css?v={CACHE_SUFFIX}"}),

        # navbar
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-home"}, "🏠 Home"),
        ),

        # main container
        html.div(
            {"className": "roast-battle chat-style"},
            html.h2("Bot Vs Bot AI Roast Battle"),
            html.p(
                {"className": "roast-battle-desc"},
                "Enter a topic and watch two friendly bots roast each other! No profanity, just clever fun:",
            ),

            # topic input
            html.div(
                {"className": "form-group"},
                html.input(
                    {
                        "id": "topic",
                        "type": "text",
                        "value": topic,
                        "placeholder": "e.g. programming, pizza, Mondays",
                        "onBlur": lambda e: set_topic(e["target"]["value"]),
                        "disabled": started,
                    }
                ),
            ),

            # start button
            html.button(
                {
                    "className": f"btn btn-gradient{' disabled' if started or not topic.strip() else ''}",
                    "onClick": handle_start if not (started or not topic.strip()) else None,
                    "disabled": started or not topic.strip(),
                },
                ("Battle Started" if started else "Start Roast Battle")
            ),

            html.div(
                {"className": "chat-window"},
                *[
                    html.div(
                        {"className": ("chat-bubble bot1" if speaker == "Bot Alpha" else "chat-bubble bot2")},
                        html.div({
                            "className": "bot-message",
                            "dangerouslySetInnerHTML": {
                                "__html": markdown.markdown(msg)
                            }
                        })
                    )
                    for speaker, msg in chat
                ],
                *(
                    [
                        html.div(
                            {"className": "typing-indicator"},
                            html.span({"className": "dot"}),
                            html.span({"className": "dot"}),
                            html.span({"className": "dot"}),
                            html.span("Typing...")
                        )
                    ] if is_typing else []
                )
            ),

            # error display
            error and html.p({"style": {"color": "red"}}, error),
        ),
    )