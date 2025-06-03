from reactpy import component, html, use_state
import asyncio
import aiohttp
import markdown

@component
def TextSummarizer():
    text, set_text = use_state("")
    summary_html, set_summary_html = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    summary_type, set_summary_type = use_state("bullets")  # 'bullets' or 'plain'

    def handle_text(e):
        set_text(e["target"]["value"])

    def handle_type(e):
        set_summary_type(e["target"]["value"])

    async def summarize_text():
        set_loading(True)
        set_error("")
        try:
            resp = await fetch_summary(text, summary_type)
            html_content = markdown.markdown(resp, extensions=["tables"])
            set_summary_html(f"<div class='markdown-body'>{html_content}</div>")
        except Exception as ex:
            set_error(str(ex))
        set_loading(False)

    def handle_submit(e):
        asyncio.create_task(summarize_text())
        return False

    async def fetch_summary(text, summary_type):
        await asyncio.sleep(0)
        try:
            if summary_type == "bullets":
                system_prompt = (
                    "You are a helpful AI that summarizes text. "
                    "Summarize the user's input in a concise, clear way. "
                    "Output the summary as Markdown"
                    "You can use Markdown formatting for lists, tables, and other elements. "
                    "Do not use HTML formatting. "
                    "Preserve important details and main points. "
                    "If the text is very short, just rephrase it concisely. "
                    "Never include explanations or preamble, just the summary."
                )
            else:
                system_prompt = (
                    "You are a helpful AI that summarizes text. "
                    "Summarize the user's input in a concise, clear way. "
                    "Output the summary as plain text only. "
                    "Do not use Markdown or HTML formatting. "
                    "Preserve important details and main points. "
                    "If the text is very short, just rephrase it concisely. "
                    "Never include explanations or preamble, just the summary."
                )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ai.hackclub.com/chat/completions",
                    json={
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "max_tokens": 400
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=60,
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return content
        except Exception as e:
            raise Exception(f"Summarization failed: {e}")

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/learning/text_summarizer.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div(
            {"className": "spellcheck-main-container"},
            html.h2("AI Text Summarizer"),
            html.form(
                {"onSubmit": lambda e: False, "className": "spellcheck-form"},
                html.div(
                    {"className": "form-group lang-select"},
                    html.label({"for": "summary-type"}, "Summary style:"),
                    html.select(
                        {
                            "id": "summary-type",
                            "value": summary_type,
                            "onChange": handle_type,
                            "className": "summary-type-select"
                        },
                        html.option({"value": "bullets"}, "Bullet Points / List"),
                        html.option({"value": "plain"}, "Plain Text")
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "className": f"btn btn-gradient spellcheck-btn-small{' disabled' if loading else ''}",
                        "onClick": handle_submit if not loading else None,
                        "disabled": loading or not text.strip()
                    },
                    "Summarizing..." if loading else "Summarize"
                ),
                html.div(
                    {"className": "spellcheck-split"},
                    html.textarea(
                        {
                            "className": "spellcheck-input",
                            "value": text,
                            "onBlur": handle_text,
                            "placeholder": "Paste or type your text here...",
                            "rows": 10,
                            "autoFocus": True,
                        }
                    ),
                    html.div(
                        {
                            "className": "spellcheck-output",
                            "style": {"whiteSpace": "pre-wrap"},
                            "dangerouslySetInnerHTML": {"__html": summary_html} if summary_html else None
                        },
                        None if summary_html else html.span({"className": "placeholder"}, "Summary will appear here.")
                    ),
                ),
                error and html.p({"style": {"color": "red"}}, error),
            ),
        ),
    )