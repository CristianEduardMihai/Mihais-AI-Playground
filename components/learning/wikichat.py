from reactpy import component, html, use_state
import asyncio
import wikipedia


# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[wikichat.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[wikichat.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[wikichat.py DEBUG]", *args)

@component
def WikiChat():
    chat, set_chat = use_state([])  # (speaker, message)
    user_input, set_user_input = use_state("")
    is_typing, set_is_typing = use_state(False)
    error, set_error = use_state("")
    started, set_started = use_state(False)
    wiki_input, set_wiki_input = use_state("")
    wiki_error, set_wiki_error = use_state("")
    wiki_title, set_wiki_title = use_state("")
    wiki_content, set_wiki_content = use_state("")

    def handle_wiki_start(_event=None):
        debug_log("handle_wiki_start called", wiki_input)
        set_wiki_error("")
        query = wiki_input.strip()
        if not query:
            debug_log("No input provided for Wikipedia search/link")
            set_wiki_error("Please enter a search term or Wikipedia link.")
            return
        if query.startswith("http") and "wikipedia.org/wiki/" in query:
            try:
                title = query.split("/wiki/")[-1].replace("_", " ")
                debug_log("Detected Wikipedia link, title:", title)
                page = wikipedia.page(title)
                debug_log("Fetched page:", page.title)
                set_wiki_title(page.title)
                set_wiki_content(page.content[:3000])
                set_started(True)
                set_chat([])
            except Exception as e:
                debug_log("Exception in fetching Wikipedia page by link:", e)
                set_wiki_error(f"Could not fetch page: {e}")
        else:
            try:
                debug_log("Searching Wikipedia for:", query)
                results = wikipedia.search(query)
                debug_log("Wikipedia search results:", results)
                if not results:
                    set_wiki_error("No results found.")
                    return
                picked = results[0]
                debug_log("Picked first search result:", picked)
                set_wiki_error(f"Using Wikipedia page: {picked}")
                # Try to fetch the picked page, but if it fails, try the next result
                page = None
                for idx, candidate in enumerate(results):
                    try:
                        # Auto suggest off because wikipedia search is weird
                        page = wikipedia.page(candidate, auto_suggest=False)
                        debug_log(f"Fetched page from search (candidate {idx}):", page.title)
                        set_wiki_error(f"Using Wikipedia page: {page.title}")
                        break
                    except Exception as e:
                        debug_log(f"Exception in fetching candidate {idx} '{candidate}':", e)
                if not page:
                    set_wiki_error(f"Could not fetch any search result page. Try another search.")
                    return
                set_wiki_title(page.title)
                set_wiki_content(page.content[:3000])
                set_started(True)
                set_chat([])
            except Exception as e:
                debug_log("Exception in Wikipedia search:", e)
                set_wiki_error(f"Wikipedia error: {e}")

    async def send_message(msg):
        debug_log("send_message called", msg)
        set_is_typing(True)
        set_error("")
        set_chat(lambda c: c + [("You", msg)])
        try:
            import aiohttp
            if wiki_title and wiki_content:
                debug_log("Preparing chat history for AI", chat)
                history = []
                for speaker, message in chat:
                    if speaker == "You":
                        history.append({"role": "user", "content": message})
                    else:
                        history.append({"role": "assistant", "content": message})
                history.append({"role": "user", "content": msg})
                system_prompt = (
                    f"You are a helpful assistant. The user is chatting about a Wikipedia page. "
                    f"Here is the page content (may be truncated):\n{wiki_content}\n\nAnswer the user's questions or chat about this topic. If you don't know, say 'I don't know'. "
                    "Do NOT make up facts."
                )
                debug_log("Sending to AI endpoint", system_prompt, history)
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://ai.hackclub.com/chat/completions",
                        headers={"Content-Type": "application/json"},
                        json={
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                *history
                            ]
                        },
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as resp:
                        debug_log("AI endpoint response status:", resp.status)
                        resp.raise_for_status()
                        data = await resp.json()
                debug_log("AI response data:", data)
                reply = data["choices"][0]["message"]["content"]
                set_chat(lambda c: c + [(wiki_title, reply)])
        except Exception as e:
            debug_log("Exception in send_message:", e)
            set_error(f"AI error: {e}")
        set_is_typing(False)

    def handle_send(_event=None):
        debug_log("handle_send called", user_input, is_typing)
        msg = user_input.strip()
        if not msg or is_typing:
            debug_log("handle_send: No message to send or is_typing is True")
            return
        set_user_input("")
        asyncio.create_task(send_message(msg))

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"class": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/learning/wikichat.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div(
            {"class": "character-chat chat-style"},
            html.h2("Wiki Chat"),
            html.p({"class": "desc"}, "Chat with a Wikipedia page! Paste a link or search for a topic."),
            None if started else html.div(
                {"class": "setup-form"},
                html.div(
                    {"class": "form-group"},
                    html.label({"htmlFor": "wiki-input"}, "Wikipedia search or link:"),
                    html.input({
                        "type": "text",
                        "id": "wiki-input",
                        "value": wiki_input,
                        "onBlur": lambda e: set_wiki_input(e["target"]["value"]),
                        "placeholder": "Search Wikipedia or paste a link..."
                    }),
                ),
                html.button({
                    "class": "btn btn-gradient",
                    "onClick": handle_wiki_start,
                }, "Start Wikipedia Chat"),
                html.p({"class": "error-message"}, wiki_error) if wiki_error else None,
            ),
            None if not started else html.div(
                {"class": "chat-col"},
                html.div(
                    {"class": "profile-header"},
                    html.h3({"class": "article-name"}, wiki_title if wiki_title else "")
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
                        html.span("Wikichat is typing...")
                    ) if is_typing else None,
                ),
                html.div(
                    {"class": "input-form"},
                    html.input({
                        "type": "text",
                        "value": user_input,
                        "onBlur": lambda e: set_user_input(e["target"]["value"]),
                        "placeholder": f"Type to chat with {wiki_title}…" if wiki_title else "Type a message…",
                        "disabled": is_typing
                    }),
                    html.button(
                        {
                            "class": "btn btn-gradient",
                            "onClick": handle_send,
                            "disabled": is_typing,
                        },
                        "Send"
                    ),
                    html.p({"class": "error-message"}, error) if error else None,
                ),
            ),
        )
    )