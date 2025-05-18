from reactpy import component, html, use_state
import json
import os

with open(os.path.join(os.path.dirname(__file__), "../../static/assets/country-codes.json"), encoding="utf-8") as f:
    LANGUAGES = json.load(f)

@component
def Translator():
    text, set_text = use_state("")
    translated, set_translated = use_state("")
    src_lang, set_src_lang = use_state("en")
    tgt_lang, set_tgt_lang = use_state("ro")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    def handle_text(e):
        set_text(e["target"]["value"])

    def handle_src_lang(e):
        set_src_lang(e["target"]["value"])
        # Prevent same language selection
        if e["target"]["value"] == tgt_lang:
            set_tgt_lang(next(l["code"] for l in LANGUAGES if l["code"] != e["target"]["value"]))

    def handle_tgt_lang(e):
        set_tgt_lang(e["target"]["value"])
        # Prevent same language selection
        if e["target"]["value"] == src_lang:
            set_src_lang(next(l["code"] for l in LANGUAGES if l["code"] != e["target"]["value"]))

    async def translate():
        set_loading(True)
        set_error("")
        try:
            resp = await fetch_translate(text, src_lang, tgt_lang)
            set_translated(resp)
        except Exception as ex:
            set_error(str(ex))
        set_loading(False)

    def handle_submit(e):
        import asyncio
        asyncio.create_task(translate())
        return False

    async def fetch_translate(text, src, tgt):
        import asyncio
        import requests
        await asyncio.sleep(0)
        try:
            resp = requests.post(
                "https://ai.hackclub.com/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                f"You are a helpful AI that translates text from {src.upper()} to {tgt.upper()}. "
                                "Output the translated text as plain text only. Do not use Markdown or HTML formatting. "
                                "Only return the translated text, not explanations. Preserve the original formatting and line breaks as much as possible. "
                                "Never collapse multiple lines or paragraphs into a single line. Output must match the input's line breaks and spacing as closely as possible. "
                            )
                        },
                        {"role": "user", "content": text}
                    ],
                    "max_tokens": 400
                },
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            raise Exception(f"Translation failed: {e}")

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/translator.css"}),
        html.link({"rel": "stylesheet", "href": "/static/css/recipe_maker.css"}),
        html.link({"rel": "stylesheet", "href": "/static/css/roast_battle.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home"),
        ),
        html.div(
            {"className": "spellcheck-main-container"},
            html.h2("AI Translator"),
            html.form(
                {"onSubmit": lambda e: False, "className": "spellcheck-form"},
                html.div(
                    {"className": "form-group lang-select"},
                    html.select(
                        {
                            "id": "src-lang",
                            "value": src_lang,
                            "onChange": handle_src_lang,
                        },
                        *[html.option({"value": l["code"]}, l["label"]) for l in LANGUAGES]
                    ),
                    html.span({"style": {"fontWeight": "bold", "fontSize": "1.3em", "margin": "0 0.5em"}}, "→"),
                    html.select(
                        {
                            "id": "tgt-lang",
                            "value": tgt_lang,
                            "onChange": handle_tgt_lang,
                        },
                        *[html.option({"value": l["code"]}, l["label"]) for l in LANGUAGES]
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "className": "btn btn-gradient spellcheck-btn-small",
                        "onClick": handle_submit,
                        "disabled": loading or not text.strip() or src_lang == tgt_lang
                    },
                    "Translate"
                ),
                html.div(
                    {"className": "spellcheck-split"},
                    html.textarea(
                        {
                            "className": "spellcheck-input",
                            "value": text,
                            "onChange": handle_text,
                            "placeholder": "Paste or type your text here...",
                            "rows": 10,
                            "autoFocus": True,
                        }
                    ),
                    html.div(
                        {"className": "spellcheck-output", "style": {"whiteSpace": "pre-wrap"}},
                        translated if translated else html.span({"className": "placeholder"}, "Translated text will appear here.")
                    ),
                ),
                error and html.p({"style": {"color": "red"}}, error),
            ),
        ),
    )