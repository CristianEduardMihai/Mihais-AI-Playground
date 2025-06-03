from reactpy import component, html, use_state
import asyncio
import aiohttp
import json
import os

with open(os.path.join(os.path.dirname(__file__), "../../static/assets/language-codes.json"), encoding="utf-8") as f:
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
        asyncio.create_task(translate())
        return False

    async def fetch_translate(text, src, tgt):
        await asyncio.sleep(0)
        try:
            system_prompt = (
                f"You are a helpful AI that translates text from {src.upper()} to {tgt.upper()}. "
                "Output only the translated text, no explanations, and preserve the original formatting as much as possible. "
                "Do not use Markdown or HTML formatting. "
                "Never include explanations or preamble, just the translation."
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
            raise Exception(f"Translation failed: {e}")

    def render_lang_option(lang):
        # lang is a dict with 'code' and 'label' (label is '🇺🇸 English')
        # Output: EN - 🇺🇸 English
        code = lang["code"].upper()
        flag_and_name = lang["label"]
        return html.option({"value": lang["code"]}, f"{code} - {flag_and_name}")

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/learning/translator.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
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
                        *[render_lang_option(l) for l in LANGUAGES]
                    ),
                    html.span({"style": {"fontWeight": "bold", "fontSize": "1.3em", "margin": "0 0.5em"}}, "→"),
                    html.select(
                        {
                            "id": "tgt-lang",
                            "value": tgt_lang,
                            "onChange": handle_tgt_lang,
                        },
                        *[render_lang_option(l) for l in LANGUAGES]
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "className": f"btn btn-gradient spellcheck-btn-small{' disabled' if loading else ''}",
                        "onClick": handle_submit if not loading else None,
                        "disabled": loading or not text.strip() or src_lang == tgt_lang
                    },
                    "Translating..." if loading else "Translate"
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
                        {"className": "spellcheck-output", "style": {"whiteSpace": "pre-wrap"}},
                        translated if translated else html.span({"className": "placeholder"}, "Translated text will appear here.")
                    ),
                ),
                error and html.p({"style": {"color": "red"}}, error),
            ),
        ),
    )