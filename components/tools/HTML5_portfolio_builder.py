from reactpy import component, html, use_state
import requests
import json
import re
import base64

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
        try:
            input_obj = {
                "title": title,
                "subtitle": subtitle,
                "color_style": color_style,
                "projects": projects
            }
            instructions = [
                "You are a helpful assistant for building personal portfolio websites.",
                "Given the following portfolio data as JSON, rewrite the fields as requested and extract color hex codes:",
                "- Do NOT deviate too much from the original user input."
            ]
            instructions.append("- Rewrite the 'title'..." if refine_title else "- Leave the 'title' unchanged.")
            instructions.append("- Rewrite the 'subtitle'..." if refine_subtitle else "- Leave the 'subtitle' unchanged.")
            instructions.append("- Rewrite project titles..." if refine_project_titles else "- Leave project titles unchanged.")
            instructions.append("- Rewrite project descriptions..." if refine_projects else "- Leave project descriptions unchanged.")
            instructions.append("- For the 'color_style', extract 2-3 hex color codes as an array called 'hexes', and rewrite as 'color_style_desc'.")
            instructions.append("Return JSON only. No explanations or ```.")

            response = requests.post(
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
            if response.status_code != 200:
                return input_obj | {"color_style_desc": color_style, "hexes": []}

            result = json.loads(response.json()["choices"][0]["message"]["content"])
            return {
                "title": result.get("title", title),
                "subtitle": result.get("subtitle", subtitle),
                "color_style_desc": result.get("color_style_desc", color_style),
                "hexes": result.get("hexes", []),
                "projects": result.get("projects", projects)
            }
        except Exception:
            return {"title": title, "subtitle": subtitle, "color_style_desc": color_style, "hexes": [], "projects": projects}

    def handle_generate(event):
        set_loading(True)
        set_output_html("")
        set_error("")
        try:
            ai_result = ai_refine_portfolio_all(title, subtitle, color_style, projects,
                                                refine_title, refine_subtitle,
                                                refine_projects, refine_project_titles)

            final_title = ai_result["title"]
            final_subtitle = ai_result["subtitle"]
            refined_projects = ai_result["projects"]
            refined_desc = ai_result.get("color_style_desc", color_style)
            hexes = ai_result.get("hexes", [])

            projects_html = "\n".join(
                f'<div class="project">'
                f'<div class="project-title">{p["title"]}</div>'
                f'<div class="project-desc">{p["desc"]}</div>'
                + (f'<a class="project-link" href="{p["link"]}" target="_blank">{p["link"]}</a>' if p["link"] else "")
                + '</div>'
                for p in refined_projects if p["title"] or p["desc"] or p["link"]
            )

            if not hexes:
                hexes = re.findall(r"#[0-9a-fA-F]{6}", color_style)
            bg1 = hexes[0] if len(hexes) > 0 else "#7b2ff2"
            bg2 = hexes[1] if len(hexes) > 1 else "#f357a8"
            accent = hexes[2] if len(hexes) > 2 else "#7b2ff2"

            with open("static/assets/html5_portfolio_template.html", encoding="utf-8") as f:
                template = f.read()

            html_out = (
                template
                .replace("__PORTFOLIO_TITLE__", final_title or "My Portfolio")
                .replace("__PORTFOLIO_SUBTITLE__", final_subtitle or "")
                .replace("__BG_COLOR1__", bg1)
                .replace("__BG_COLOR2__", bg2)
                .replace("__ACCENT_COLOR__", accent)
                .replace("__PROJECTS_HTML__", projects_html or "<i>No projects yet.</i>")
                .replace("__COLOR_STYLE_DESC__", refined_desc or color_style)
            )

            set_output_html(html_out)

            b64 = base64.b64encode(html_out.encode("utf-8")).decode("utf-8")
            set_download_url(f"data:text/html;base64,{b64}")

        except Exception as e:
            set_error(f"Error: {e}")
        finally:
            set_loading(False)

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/tools/HTML5_portfolio_builder.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "portfolio-builder"},
            html.h2("HTML5 Portfolio Builder"),

            html.div({"className": "form-group"},
                html.label({"for": "portfolio-title"}, "Portfolio Title:"),
                html.input({
                    "id": "portfolio-title", "type": "text", "value": title,
                    "placeholder": "e.g. John Doe's Portfolio",
                    "onBlur": lambda e: set_title(e["target"]["value"])
                }),
                html.label({},
                    html.input({
                        "type": "checkbox", "checked": refine_title,
                        "onChange": lambda e: set_refine_title(e["target"]["checked"])
                    }),
                    " Refine with AI"
                )
            ),

            html.div({"className": "form-group"},
                html.label({"for": "portfolio-subtitle"}, "Subtitle / Tagline:"),
                html.input({
                    "id": "portfolio-subtitle", "type": "text", "value": subtitle,
                    "placeholder": "e.g. Web Developer & Designer",
                    "onBlur": lambda e: set_subtitle(e["target"]["value"])
                }),
                html.label({},
                    html.input({
                        "type": "checkbox", "checked": refine_subtitle,
                        "onChange": lambda e: set_refine_subtitle(e["target"]["checked"])
                    }),
                    " Refine with AI"
                )
            ),

            html.div({"className": "form-group"},
                html.label({"for": "color-style"}, "Describe your color Style:"),
                html.input({
                    "id": "color-style", "type": "text", "value": color_style,
                    "placeholder": "e.g. A purple and pink gradient with a blue accent",
                    "onBlur": lambda e: set_color_style(e["target"]["value"])
                })
            ),

            html.div({"className": "ai-refine-options"},
                html.label({"className": "ai-refine-checkbox"},
                    html.input({
                        "type": "checkbox", "checked": refine_project_titles,
                        "onChange": lambda e: set_refine_project_titles(e["target"]["checked"])
                    }),
                    " Generate/Refine all project titles with AI"
                ),
                html.label({"className": "ai-refine-checkbox"},
                    html.input({
                        "type": "checkbox", "checked": refine_projects,
                        "onChange": lambda e: set_refine_projects(e["target"]["checked"])
                    }),
                    " Refine all project descriptions with AI"
                )
            ),

            html.h3("Projects & Accomplishments"),
            html.div({"className": "projects-list"},
                *[
                    html.div({"className": "project-card"},
                        html.label({}, f"Project #{i+1}"),
                        html.input({
                            "type": "text", "placeholder": "Title", "value": p["title"],
                            "onBlur": lambda e, idx=i: handle_project_change(idx, "title", e["target"]["value"])
                        }),
                        html.input({
                            "type": "text", "placeholder": "Description", "value": p["desc"],
                            "onBlur": lambda e, idx=i: handle_project_change(idx, "desc", e["target"]["value"])
                        }),
                        html.input({
                            "type": "text", "placeholder": "Link (optional)", "value": p["link"],
                            "onBlur": lambda e, idx=i: handle_project_change(idx, "link", e["target"]["value"])
                        }),
                        html.button({"className": "btn btn-secondary", "onClick": lambda e, idx=i: remove_project(idx)}, "Remove")
                        if len(projects) > 1 else None
                    ) for i, p in enumerate(projects)
                ]
            ),

            html.button({"className": "btn btn-gradient add-project-btn" , "onClick": add_project}, "+ Add Another Project"),

            html.button({
                "className": "btn btn-gradient",
                "onClick": handle_generate,
                "disabled": loading
            }, "Generate Portfolio HTML" if not loading else "Generating..."),

            html.div({"className": "error-message"}, error) if error else None,

            html.div({"className": "interview-output"},
                html.h3("Generated HTML Preview:"),
                html.i({"className": "preview-placeholder"}, "No portfolio generated yet.") if not output_html.strip() else
                html.iframe({
                    "className": "portfolio-html-iframe",
                    "srcDoc": output_html,
                    "sandbox": "allow-scripts allow-same-origin"
                }),

                html.a({
                    "href": download_url,
                    "download": "portfolio.html",
                    "className": "btn btn-navy download-btn",
                    "target": "_blank"
                }, "⬇ Download HTML") if download_url else None
            )
        )
    )
