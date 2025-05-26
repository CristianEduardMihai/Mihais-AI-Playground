from reactpy import component, html, use_state, use_effect
import json
import os

with open(os.path.join(os.path.dirname(__file__), "../../static/assets/language-codes.json"), encoding="utf-8") as f:
    LANGUAGES = json.load(f)

@component
def SpellCheck():
    text, set_text = use_state("")
    corrected, set_corrected = use_state("")
    lang, set_lang = use_state("en")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    def handle_text(e):
        set_text(e["target"]["value"])

    def handle_lang(e):
        set_lang(e["target"]["value"])

    async def check_spelling():
        set_loading(True)
        set_error("")
        try:
            resp = await fetch_spellcheck(text, lang)
            set_corrected(resp)
        except Exception as ex:
            set_error(str(ex))
        set_loading(False)

    def handle_submit(e):
        import asyncio
        asyncio.create_task(check_spelling())
        return False

    async def fetch_spellcheck(text, lang):
        import asyncio
        import requests
        await asyncio.sleep(0)  # yield control
        try:
            resp = requests.post(
                "https://ai.hackclub.com/chat/completions",
                json={
                    "messages": [
                        {
                            "role": "system", 
                            "content": 
                            f"You are a helpful AI that corrects spelling and grammar in the language: {lang.upper()}."
                            "Output the corrected text as plain text only. Do not use Markdown or HTML formatting."
                            "Only return the corrected text, not explanations."
                            "Preserve the original formatting and line breaks exactly as in the input."
                            "Never collapse multiple lines or paragraphs into a single line."
                            "Output must match the input's line breaks and spacing as closely as possible."
                            "Do not forget spaces, or punctuation(dots at sentence endings, commas etc)."
                            "Keep the text as close to the original as possible, while adding necesary punctuation."
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
            raise Exception(f"Spell check failed: {e}")

    def render_lang_option(lang):
        # lang is a dict with 'code' and 'label' (label is '🇺🇸 English')
        # Output: EN - 🇺🇸 English
        code = lang["code"].upper()
        flag_and_name = lang["label"]
        return html.option({"value": lang["code"]}, f"{code} - {flag_and_name}")

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/learning/spell_check.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home"),
        ),
        html.div(
            {"className": "spellcheck-main-container"},
            html.h2("AI Spell Checker"),
            html.form(
                {"onSubmit": lambda e: False, "className": "spellcheck-form"},
                html.div(
                    {"className": "form-group lang-select"},
#                    html.label({"for": "lang"}, "Language:"),
                    html.select(
                        {
                            "id": "lang",
                            "value": lang,
                            "onChange": handle_lang,
                        },
                        *[render_lang_option(l) for l in LANGUAGES]
                    ),
                ),
                html.button(
                    {
                        "type": "button",
                        "className": "btn btn-gradient spellcheck-btn-small",
                        "onClick": handle_submit,
                        "disabled": loading or not text.strip()
                    },
                    "Check Spelling"
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
                        corrected
                        if corrected else html.span({"className": "placeholder"}, "Corrected text will appear here.")
                    ),
                ),
                error and html.p({"style": {"color": "red"}}, error),
            ),
        ),
    )