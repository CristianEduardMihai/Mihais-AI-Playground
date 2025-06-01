from reactpy import component, html, use_state
import markdown

@component
def CoderProfile():
    code, set_code = use_state("")
    result_md, set_result_md = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    def handle_submit(_event=None):
        set_loading(True)
        set_result_md("")
        set_error("")
        import threading
        def run_async():
            import asyncio
            import aiohttp
            async def do_request():
                prompt = (
                    "You are a playful code analyst. "
                    "Given a user's code (max 300 lines), analyze their coding style and habits. "
                    "Write a fun, friendly coder profile in Markdown. "
                    "Include bullet lists for strengths, quirks, and fun insights. "
                    "Add a playful summary at the end. "
                    "Use emojis, but don't overdo it. "
                    "Do not repeat the code or its comments directly. "
                    "Keep in mind that this code is just a snippet of their work. "
                    "Do not analyze the code literally or focus on technical details. "
                    "Instead, infer personality traits, habits, and possible preferences from the code. "
                    "Use second person perspective (you, your). "
                    "Be creative and interpretive, not literal. "
                    "Keep it positive and fun!"
                )
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://ai.hackclub.com/chat/completions",
                            json={
                                "messages": [
                                    {"role": "system", "content": prompt},
                                    {"role": "user", "content": f"User's code (max 300 lines):\n{code[:12000]}"},
                                ],
                                "max_tokens": 350
                            },
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=40)
                        ) as resp:
                            resp.raise_for_status()
                            data = await resp.json()
                    text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if text:
                        text = text.replace("\n*", "\n\n*").replace("\n-", "\n\n-")
                    set_result_md(text)
                except Exception as e:
                    set_error(f"Error: {e}")
                finally:
                    set_loading(False)
            asyncio.run(do_request())
        threading.Thread(target=run_async, daemon=True).start()

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {"className": "coder-profile"},
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/coder_profile.css?v={CACHE_SUFFIX}"}),
        html.div({"className": "background-gradient-blur"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-home"}, "🏠 Home")
        ),
        html.div(
            {"className": "form"},
            html.h2({"style": {"textAlign": "center", "color": "#7b2ff2"}}, "AI Coder Profile"),
            html.p({"className": "desc"}, "Paste your code (max 300 lines) and get a playful coder personality analysis!"),
            html.div({"className": "form-group"},
                html.label({"htmlFor": "code"}, "Paste your code here (max 300 lines)"),
                html.textarea({
                    "id": "code", "value": code,
                    "onInput": lambda e: set_code(e["target"]["value"]),
                    "rows": 12,
                    "maxLength": 12000,
                    "placeholder": "Paste your code here..."
                }),
            ),
            html.button(
                {
                    "className": "btn btn-gradient",
                    "onClick": handle_submit,
                    "disabled": loading or not code.strip()
                },
                "Get My Coder Profile" if not loading else "Loading..."
            ),
            html.div({"className": "error-message"}, error) if error else None
        ),
        html.div(
            {"className": "coder-output"},
            html.h3("Your Coder Profile:"),
            html.i({"className": "no-analysis"}, "No analysis yet.") if not result_md.strip() else
            html.div({
                "dangerouslySetInnerHTML": {"__html": markdown.markdown(result_md)},
                "key": hash(result_md)
            })
        )
    )
