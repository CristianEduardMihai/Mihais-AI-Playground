from reactpy import component, html, use_state
import requests

@component
def HTML5PortfolioBuilder():
    # State for portfolio fields
    title, set_title = use_state("")
    subtitle, set_subtitle = use_state("")
    color_style, set_color_style = use_state("")
    projects, set_projects = use_state([{"title": "", "desc": "", "link": ""}])
    output_html, set_output_html = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

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

    def handle_generate(event):
        set_loading(True)
        set_output_html("")
        set_error("")
        try:
            # Compose the project HTML for the template
            projects_html = "\n".join(
                f'<div class="project">'
                f'<div class="project-title">{p["title"]}</div>'
                f'<div class="project-desc">{p["desc"]}</div>'
                + (f'<a class="project-link" href="{p["link"]}" target="_blank">{p["link"]}</a>' if p["link"] else "")
                + '</div>'
                for p in projects if p["title"] or p["desc"] or p["link"]
            )
            # Parse color_style (expects two hexes and an accent, fallback if not)
            import re
            hexes = re.findall(r"#[0-9a-fA-F]{6}", color_style)
            bg1 = hexes[0] if len(hexes) > 0 else "#7b2ff2"
            bg2 = hexes[1] if len(hexes) > 1 else "#f357a8"
            accent = hexes[2] if len(hexes) > 2 else "#7b2ff2"
            # Load template
            with open("static/assets/html5_portfolio_template.html", encoding="utf-8") as f:
                template = f.read()
            html_out = (
                template
                .replace("__PORTFOLIO_TITLE__", title or "My Portfolio")
                .replace("__PORTFOLIO_SUBTITLE__", subtitle or "")
                .replace("__BG_COLOR1__", bg1)
                .replace("__BG_COLOR2__", bg2)
                .replace("__ACCENT_COLOR__", accent)
                .replace("__PROJECTS_HTML__", projects_html or "<i>No projects yet.</i>")
            )
            set_output_html(html_out)
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
            ),
            html.div({"className": "form-group"},
                html.label({"for": "portfolio-subtitle"}, "Subtitle / Tagline:"),
                html.input({
                    "id": "portfolio-subtitle", "type": "text", "value": subtitle,
                    "placeholder": "e.g. Web Developer & Designer",
                    "onBlur": lambda e: set_subtitle(e["target"]["value"])
                }),
            ),
            html.div({"className": "form-group"},
                html.label({"for": "color-style"}, "Describe your color Style:"),
                html.input({
                    "id": "color-style", "type": "text", "value": color_style,
                    "placeholder": "e.g. A purple and pink gradient with a blue accent",
                    "onBlur": lambda e: set_color_style(e["target"]["value"])
                }),
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
                            "type": "text", "placeholder": "Description(Will be AI-refined)", "value": p["desc"],
                            "onBlur": lambda e, idx=i: handle_project_change(idx, "desc", e["target"]["value"])
                        }),
                        html.input({
                            "type": "text", "placeholder": "Link (optional)", "value": p["link"],
                            "onBlur": lambda e, idx=i: handle_project_change(idx, "link", e["target"]["value"])
                        }),
                        html.button({"className": "btn btn-secondary", "onClick": lambda e, idx=i: remove_project(idx)}, "Remove") if len(projects) > 1 else None
                    ) for i, p in enumerate(projects)
                ]
            ),
            html.button({"className": "btn btn-gradient add-project-btn" , "onClick": add_project}, "+ Add Another Project"),
            html.button({"className": "btn btn-gradient", "onClick": handle_generate, "disabled": loading}, "Generate Portfolio HTML" if not loading else "Generating..."),
            html.div({"className": "error-message"}, error) if error else None,
            html.div({"className": "interview-output"},
                html.h3("Generated HTML Preview:"),
                html.i({"className": "preview-placeholder"}, "No portfolio generated yet.") if not output_html.strip() else
                html.iframe({
                    "className": "portfolio-html-iframe",
                    "srcDoc": output_html,
                    "sandbox": "allow-scripts allow-same-origin"
                }),
                html.button({
                    "className": "btn btn-navy download-btn",
                    "onClick": lambda e: download_portfolio(output_html),
                    "disabled": not output_html.strip()
                }, "⬇ Download HTML")
            )
        )
    )

def download_portfolio(html_content):
    import base64
    from reactpy import run_js
    if not html_content.strip():
        return
    b64 = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
    data_url = f"data:text/html;base64,{b64}"
    run_js(f'''
        var a = document.createElement('a');
        a.href = "{data_url}";
        a.download = "portfolio.html";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    ''')
