from reactpy import component, html, use_state
import requests
import json
import base64
import re


@component
def HTML5PortfolioBuilder():
    title, set_title = use_state("")
    subtitle, set_subtitle = use_state("")
    color_style, set_color_style = use_state("")
    projects, set_projects = use_state([{"title": "", "desc": "", "link": ""}])
    output_html, set_output_html = use_state("")
    download_url, set_download_url = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    refine_title, set_refine_title = use_state(True)
    refine_subtitle, set_refine_subtitle = use_state(True)
    refine_projects, set_refine_projects = use_state(True)
    refine_project_titles, set_refine_project_titles = use_state(True)

    show_json_modal, set_show_json_modal = use_state(False)
    json_text, set_json_text = use_state("")
    show_json_export, set_show_json_export = use_state(False)
    json_export_text, set_json_export_text = use_state("")
    copied_json, set_copied_json = use_state(False)

    def handle_project_change(idx, field, value):
        def updater(prev):
            updated = prev.copy()
            updated[idx] = {**updated[idx], field: value}
            return updated
        set_projects(updater)

    def add_project(_):
        set_projects(lambda prev: prev + [{"title": "", "desc": "", "link": ""}])

    def remove_project(idx):
        set_projects(lambda prev: [p for i, p in enumerate(prev) if i != idx])

    def ai_refine_portfolio_all(title, subtitle, color_style, projects, refine_title, refine_subtitle, refine_projects, refine_project_titles):
        #print("--------- [DEBUG] ai_refine_portfolio_all called with:")
        #print("  title:", title)
        #print("  subtitle:", subtitle)
        #print("  color_style:", color_style)
        #print("  projects:", projects)
        import time, random
        request_id = f"{int(time.time()*1000)}_{random.randint(1000,9999)}"
        try:
            input_obj = {
                "title": title,
                "subtitle": subtitle,
                "color_style": color_style,
                "projects": projects,
                "request_id": request_id
            }
            instructions = [
                "You are a helpful assistant for building personal portfolio websites.",
                "Given the following portfolio data as JSON, rewrite the fields as requested and extract color hex codes:",
                "- Do NOT deviate too much from the original user input.",
                "- Rewrite the 'title'..." if refine_title else "- Leave the 'title' unchanged.",
                "- Rewrite the 'subtitle'..." if refine_subtitle else "- Leave the 'subtitle' unchanged.",
                "- Rewrite project titles..." if refine_project_titles else "- Leave project titles unchanged.",
                "- Rewrite project descriptions..." if refine_projects else "- Leave project descriptions unchanged.",
                "- For the 'color_style', extract 2-3 hex color codes as an array called 'hexes', and rewrite as 'color_style_desc'.",
                "Return JSON only. No explanations or ```.",
            ]
            resp = requests.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": "\n".join(instructions)},
                        {"role": "user", "content": json.dumps(input_obj)}
                    ]
                },
                timeout=90
            )
            ai_raw = resp.json()["choices"][0]["message"]["content"]
            #print("--------- [DEBUG] AI raw response:")
            #print(ai_raw)
            # Remove triple backticks and whitespace if present
            ai_clean = ai_raw.strip()
            if ai_clean.startswith("```"):
                ai_clean = ai_clean.lstrip("`\n ")
            if ai_clean.endswith("```"):
                ai_clean = ai_clean.rstrip("`\n ")
            # Try again if still wrapped
            if ai_clean.startswith("json"):
                ai_clean = ai_clean[4:].lstrip("\n ")
            result = json.loads(ai_clean)
            return {
                "title": result.get("title", title),
                "subtitle": result.get("subtitle", subtitle),
                "color_style_desc": result.get("color_style_desc", color_style),
                "hexes": result.get("hexes", []),
                "projects": result.get("projects", projects)
            }
        except Exception as e:
            #print(f"--------- [DEBUG] AI exception: {e}")
            return {"title": title, "subtitle": subtitle, "color_style_desc": color_style, "hexes": [], "projects": projects}

    def handle_generate(_):
        # Blur all text inputs to trigger onBlur and update state
        blur_script = html.script({
            "dangerouslySetInnerHTML": """
            Array.from(document.querySelectorAll('input[type="text"]')).forEach(el => el.blur());
            """
        })
        set_loading(True)
        set_output_html("")
        set_error("")
        # Wait a short time to allow onBlur to fire and state to update
        import threading
        def delayed_generate():
            import time
            time.sleep(0.05)
            # Re-read state inside the thread to avoid closure issues
            current_title = title
            current_subtitle = subtitle
            current_color_style = color_style
            current_projects = projects
            current_refine_title = refine_title
            current_refine_subtitle = refine_subtitle
            current_refine_projects = refine_projects
            current_refine_project_titles = refine_project_titles
            #print("[DEBUG] handle_generate state before AI call:")
            #print("  title:", current_title)
            #print("  subtitle:", current_subtitle)
            #print("  color_style:", current_color_style)
            #print("  projects:", current_projects)
            ai_res = ai_refine_portfolio_all(
                current_title, current_subtitle, current_color_style, current_projects,
                current_refine_title, current_refine_subtitle, current_refine_projects, current_refine_project_titles
            )
            final_title = ai_res["title"]
            final_subtitle = ai_res["subtitle"]
            refined_projects = ai_res["projects"]
            refined_desc = ai_res.get("color_style_desc", color_style)
            hexes = ai_res.get("hexes", [])

            if not hexes:
                hexes = re.findall(r"#[0-9A-Fa-f]{6}", color_style)
            bg1 = hexes[0] if len(hexes) > 0 else "#7b2ff2"
            bg2 = hexes[1] if len(hexes) > 1 else "#f357a8"
            accent = hexes[2] if len(hexes) > 2 else "#7b2ff2"

            with open("static/assets/html5_portfolio_template.html", encoding="utf-8") as f:
                template = f.read()

            html_out = (
                template
                .replace("__PORTFOLIO_TITLE__", final_title)
                .replace("__PORTFOLIO_SUBTITLE__", final_subtitle)
                .replace("__BG_COLOR1__", bg1)
                .replace("__BG_COLOR2__", bg2)
                .replace("__ACCENT_COLOR__", accent)
                .replace("__COLOR_STYLE_DESC__", refined_desc)
                .replace("__PROJECTS_HTML__", "\n".join(
                    f'<div class="project"><div class="project-title">{p["title"]}</div>'
                    f'<div class="project-desc">{p["desc"]}</div>'
                    + (f'<a href="{p["link"]}" target="_blank">{p["link"]}</a>' if p["link"] else "")
                    + "</div>" for p in refined_projects if any(p.values())
                ) or "<i>No projects yet.</i>")
            )

            set_output_html(html_out)
            b64 = base64.b64encode(html_out.encode("utf-8")).decode("utf-8")
            set_download_url(f"data:text/html;base64,{b64}")
            set_loading(False)
        threading.Thread(target=delayed_generate, daemon=True).start()
        return blur_script

    def open_json_modal(_):
        set_json_text("")
        set_show_json_modal(True)

    def close_json_modal(_):
        set_show_json_modal(False)
        set_json_text("")

    def handle_json_paste(_):
        try:
            data = json.loads(json_text)
            set_title(data.get("title", ""))
            set_subtitle(data.get("subtitle", ""))
            set_color_style(data.get("color_style", ""))
            set_projects(data.get("projects", [{"title": "", "desc": "", "link": ""}]))
            set_refine_title(data.get("refine_title", True))
            set_refine_subtitle(data.get("refine_subtitle", True))
            set_refine_projects(data.get("refine_projects", True))
            set_refine_project_titles(data.get("refine_project_titles", True))
            set_error("")
            set_show_json_modal(False)
        except Exception as e:
            set_error(f"Invalid JSON: {e}")

    def handle_save_json(_):
        payload = {
            "title": title,
            "subtitle": subtitle,
            "color_style": color_style,
            "projects": projects,
            "refine_title": refine_title,
            "refine_subtitle": refine_subtitle,
            "refine_projects": refine_projects,
            "refine_project_titles": refine_project_titles
        }
        set_json_export_text(json.dumps(payload, indent=2, ensure_ascii=False))
        set_show_json_export(True)

    def handle_copy_json(_):
        try:
            import pyperclip
            pyperclip.copy(json_export_text)
        except ImportError:
            try:
                import subprocess
                subprocess.run('echo ' + json_export_text.strip().replace('"', '\"') + '| clip', shell=True)
            except Exception:
                pass
        set_copied_json(True)
        import threading, time
        def clear():
            time.sleep(1.1)
            set_copied_json(False)
        threading.Thread(target=clear, daemon=True).start()

    def close_json_export(_):
        set_show_json_export(False)
        set_json_export_text("")

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/HTML5_portfolio_builder.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "navbar"}, html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")),
        html.div(
            {"className": "portfolio-builder"},
            html.h2("HTML5 Portfolio Builder"),
            html.div({"className": "top-buttons"},
                html.button({"className": "btn btn-secondary", "onClick": handle_save_json}, "⬇ Save Backup"),
                html.button({"className": "btn btn-secondary", "onClick": open_json_modal}, "⬆ Restore Backup"),
            ),
            # Modal for JSON paste (Restore)
            (html.div({"className": "modal-overlay"},
                html.div({"className": "modal-content"},
                    html.h3("Paste Portfolio Backup JSON"),
                    html.textarea({
                        "className": "modal-textarea",
                        "value": json_text,
                        "onInput": lambda e: set_json_text(e["target"]["value"])
                    }),
                    html.div({"className": "modal-actions"},
                        html.button({"className": "btn btn-secondary", "onClick": handle_json_paste}, "Restore"),
                        html.button({"className": "btn btn-gradient", "onClick": close_json_modal}, "Cancel")
                    )
                )
            )) if show_json_modal else None,
            # Modal for JSON export/copy (Save)
            (html.div({"className": "modal-overlay"},
                html.div({"className": "modal-content"},
                    html.h3("Copy Portfolio Backup JSON"),
                    html.textarea({
                        "className": "modal-textarea",
                        "value": json_export_text,
                        "readOnly": True
                    }),
                    html.div({"className": "modal-actions"},
                        html.button({"className": "btn btn-secondary", "onClick": handle_copy_json}, "Copy"),
                        copied_json and html.span({"className": "copied-message"}, "Copied!") or None,
                        html.button({"className": "btn btn-gradient", "onClick": close_json_export}, "Close")
                    )
                )
            )) if show_json_export else None,
            html.div({"className": "form-group"},
                html.input({"type": "text", "className": "input-title", "value": title, "onBlur": lambda e: set_title(e["target"]["value"]), "placeholder": "Portfolio Title"}),
                html.label({}, html.input({"type": "checkbox", "checked": refine_title, "onChange": lambda e: set_refine_title(e["target"]["checked"])}), " Refine Title")
            ),
            html.div({"className": "form-group"},
                html.input({"type": "text", "className": "input-subtitle", "value": subtitle, "onBlur": lambda e: set_subtitle(e["target"]["value"]), "placeholder": "Subtitle"}),
                html.label({}, html.input({"type": "checkbox", "checked": refine_subtitle, "onChange": lambda e: set_refine_subtitle(e["target"]["checked"])}), " Refine Subtitle")
            ),
            html.div({"className": "form-group"},
                html.input({"type": "text", "className": "input-color-style", "value": color_style, "onBlur": lambda e: set_color_style(e["target"]["value"]), "placeholder": "Color Gradient Style"})
            ),
            html.div({"className": "ai-refine-options"},
                html.label({}, html.input({"type": "checkbox", "checked": refine_project_titles, "onChange": lambda e: set_refine_project_titles(e["target"]["checked"])}), " Refine Project Titles"),
                html.label({}, html.input({"type": "checkbox", "checked": refine_projects, "onChange": lambda e: set_refine_projects(e["target"]["checked"])}), " Refine Project Descriptions")
            ),
            html.h3("Projects & Accomplishments"),
            html.div({"className": "projects-list"},
                *[
                    html.div({"className": "project-card"},
                        html.input({"type": "text", "className": "input-project-title", "value": p["title"], "placeholder": "Title", "onBlur": lambda e, idx=i: handle_project_change(idx, "title", e["target"]["value"])}),
                        html.input({"type": "text", "className": "input-project-desc", "value": p["desc"], "placeholder": "Description", "onBlur": lambda e, idx=i: handle_project_change(idx, "desc", e["target"]["value"])}),
                        html.input({"type": "text", "className": "input-project-link", "value": p["link"], "placeholder": "Link", "onBlur": lambda e, idx=i: handle_project_change(idx, "link", e["target"]["value"])}),
                        (len(projects) > 1 and html.button({"className": "btn btn-secondary btn-remove-project", "onClick": lambda e, idx=i: remove_project(idx)}, "Remove")) or None
                    ) for i, p in enumerate(projects)
                ]
            ),
            html.button({"className": "btn btn-gradient add-project-btn", "onClick": add_project}, "+ Add Project"),
            html.button({"className": "btn btn-gradient", "onClick": handle_generate, "disabled": loading}, "Generate HTML" if not loading else "Generating..."),
            output_html and html.a({
                "className": "btn btn-navy download-btn",
                "href": download_url,
                "download": "portfolio.html",
                "target": "_blank"
            }, "⬇ Download HTML") or None,
            html.div({"className": "error-message"}, error) if error else None,
            html.div({"className": "interview-output"},
                html.h3("Generated HTML Preview:"),
                output_html and html.iframe({
                    "className": "portfolio-html-iframe",
                    "srcDoc": output_html,
                    "sandbox": "allow-same-origin"
                }),
            )
        )
    )
