from reactpy import component, html, use_state
import aiohttp
import json
import asyncio

@component
def AIColorPicker():
    description, set_description = use_state("")
    num_colors, set_num_colors = use_state("5")
    palette, set_palette = use_state([])
    ai_message, set_ai_message = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    copied_idx, set_copied_idx = use_state(None)
    color_meanings, set_color_meanings = use_state([])
    import time

    async def handle_generate_palette(event=None):
        # Limit the number of colors to 12 for safety
        try:
            n = int(num_colors)
            if n < 2:
                n = 2
            elif n > 12:
                n = 12
            set_num_colors(str(n))
        except Exception:
            set_num_colors("5")
            n = 5
        set_loading(True)
        set_palette([])
        set_ai_message("")
        set_error("")
        set_color_meanings([])
        try:
            prompt = (
                "You are an expert and helpful AI color palette designer. "
                "Given a project description and a number of colors, generate a harmonious color palette. "
                "Reply ONLY with a JSON object like this: "
                '{"colors": ["#HEX1", ...], "message": "A short friendly message about the palette.", "meanings": ["short meaning for color 1", ...]} '
                "For each color, provide a very short (1 phrase) meaning or feeling it represents, in the 'meanings' array, same order as 'colors'. "
                "Do not include any text outside the JSON object."
            )
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ai.hackclub.com/chat/completions",
                    headers={"Content-Type": "application/json"},
                    json={
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Project description: {description}\nNumber of colors: {n}\n"}
                        ]
                    },
                    timeout=60
                ) as response:
                    if response.status != 200:
                        raise RuntimeError(f"AI model returned {response.status}")
                    data = await response.json()
                    content = data["choices"][0]["message"]["content"].strip()
                    import re
                    match = re.search(r'\{.*\}', content, re.DOTALL)
                    if not match:
                        raise ValueError("No JSON found in AI response.")
                    json_str = match.group(0)
                    palette_data = json.loads(json_str)
                    set_palette(palette_data.get("colors", []))
                    set_ai_message(palette_data.get("message", ""))
                    set_color_meanings(palette_data.get("meanings", []))
        except Exception as e:
            set_error(f"Error: {e}")
        set_loading(False)

    def handle_generate_palette_click(event=None):
        asyncio.create_task(handle_generate_palette())

    def handle_swatch_click(idx, color):
        try:
            import pyperclip
            pyperclip.copy(color)
        except ImportError:
            try:
                import subprocess
                subprocess.run('echo ' + color.strip() + '| clip', shell=True)
            except Exception:
                pass
        set_copied_idx(idx)
        # Show color meaning in ai-message
        if color_meanings and idx < len(color_meanings):
            set_ai_message(color_meanings[idx])
        def clear():
            time.sleep(1.1)
            set_copied_idx(None)
        import threading
        threading.Thread(target=clear, daemon=True).start()

    def render_palette():
        if not palette:
            return html.div({"className": "palette-empty"}, "No palette generated yet.")
        return html.div(
            {"className": "palette-row"},
            *[
                html.div(
                    {
                        "className": f"color-swatch" + (" copied" if copied_idx == idx else ""),
                        "tabIndex": 0,
                        "onClick": lambda e, idx=idx, color=color: handle_swatch_click(idx, color),
                        "onKeyDown": lambda e, idx=idx, color=color: handle_swatch_click(idx, color) if e.get("key") in ["Enter", " "] else None,
                        "title": "Click to copy hex"
                    },
                    html.div({"className": "color-swatch-fill", "style": {"background": color}}),
                    html.div({"className": "color-hex"}, color),
                    html.div({"className": "copied-tooltip"}, "Copied!") if copied_idx == idx else None
                )
                for idx, color in enumerate(palette)
            ]
        )

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/color_picker.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div(
            {"className": "color-picker-app"},
            html.h2("AI Color Palette Picker"),
            html.div(
                {"className": "form-group"},
                html.label({"htmlFor": "project-desc"}, "Describe your project:"),
                html.input({
                    "id": "project-desc",
                    "type": "text",
                    "value": description,
                    "placeholder": "e.g. Modern SaaS dashboard, bakery logo, cozy blog...",
                    "onBlur": lambda e: set_description(e["target"]["value"])
                }),
            ),
            html.div(
                {"className": "form-group"},
                html.label({"htmlFor": "num-colors"}, "How many colors?"),
                html.input({
                    "id": "num-colors",
                    "type": "number",
                    "min": "2",
                    "max": "12",
                    "value": num_colors,
                    "onBlur": lambda e: set_num_colors(e["target"]["value"])
                }),
            ),
            html.button(
                {
                    "className": "btn btn-gradient",
                    "onClick": handle_generate_palette_click if not loading else None,
                    "disabled": loading or not description or not num_colors
                },
                "Generating..." if loading else "Generate Palette"
            ),
            html.div(
                {"className": "palette-output"},
                html.h3("Generated Palette:"),
                render_palette(),
                html.div(
                    {"className": "ai-message"},
                    ai_message
                ) if ai_message else None,
                html.p({"className": "error-message"}, error) if error else None
            )
        )
    )