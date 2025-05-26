from reactpy import component, html, use_state
import markdown
import requests
import json

@component
def InterviewPrep():
    job_role, set_job_role = use_state("")
    experience_level, set_experience_level = use_state("entry")
    question_type, set_question_type = use_state("behavioral")
    output_html, set_output_html = use_state("")
    
    # Interview question categories
    categories = [
        "Technical Skills", "Problem Solving", "Leadership",
        "Communication", "Team Work", "Project Management",
        "Cultural Fit", "Time Management", "Conflict Resolution"
    ]
    selected_categories, set_selected_categories = use_state(categories[:3])
    def handle_category_change(e):
        value = e["target"]["value"]
        checked = e["target"].get("checked", False)
        if checked:
            set_selected_categories(lambda prev: prev + [value] if value not in prev else prev)
        else:
            set_selected_categories(lambda prev: [c for c in prev if c != value])
            
    def handle_generate_questions(event):
        set_output_html("")  # Clear previous output
        try:
            categories_str = ", ".join(selected_categories)
            role = job_role if job_role.strip() else "Software Developer"
            
            prompt = (
                "You are an expert interview coach and HR specialist. "
                "Output ONLY the interview questions and answers in Markdown format, with no extra comments. "
                "Do not include any text outside the Markdown content. "
                "Follow the provided template exactly."
                "Generate a set of interview questions and example answers in Markdown format using this template:\n\n"
                "# Interview Questions for {job} Position\n\n" # Yes, not f"{job_role}", this is intentional to avoid confusion in the prompt
                "## Question Set\n\n"
                "### {Category 1}\n"
                "**1. Q: [Question]**\n\n"
                "   - Expected Answer: [Detailed answer with key points]\n"
                "   - Tips: [Interview tips and what the interviewer is looking for]\n\n"
                "**2. Q: [Next question...]**\n\n"
                "### {Category 2}\n"
                "[...continue for each category...]\n\n"
                "## Preparation Tips\n"
                "- [General tips for this type of interview]\n"
                "- [Specific advice for the role]\n\n"
                
                "\nProvide 2-3 questions per selected category, with detailed sample answers and interviewer tips."
            )

            # Call the AI API to generate interview questions
            response = requests.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {
                            "role": "system",
                            "content": prompt},
                        {
                            "role": "user", "content": (
                            f"Role: {role}\n"
                            f"Experience Level: {experience_level}\n"
                            f"Question Type: {question_type}\n"
                            f"Categories to focus on: {categories_str}\n"
                            )
                        }
                    ]
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"AI model returned {response.status_code}")

            data = response.json()
            md_content = data["choices"][0]["message"]["content"]
            
            # Convert the markdown to HTML
            html_content = markdown.markdown(md_content, extensions=["tables", "extra"])
            set_output_html(f"<div class='markdown-body'>{html_content}</div>")

        except Exception as e:
            set_output_html(f"An error occurred: {str(e)}")

    return html.div(
        {},
        # External CSS and background
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/tools/interview_prep.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "interview-prep"},
            html.h2("AI Interview Prep Assistant"),
            # Job Role
            html.div(
                {"className": "form-group"},
                html.label({"for": "job-role"}, "Job Role:"),
                html.input({
                    "id": "job-role", "type": "text", "value": job_role,
                    "placeholder": "e.g. Software Engineer, Product Manager",
                    "onBlur": lambda e: set_job_role(e["target"]["value"])
                }),
            ),
            # Experience Level
            html.div(
                {"className": "form-group"},
                html.label({"for": "experience-level"}, "Experience Level:"),
                html.select({
                    "id": "experience-level", "value": experience_level,
                    "onChange": lambda e: set_experience_level(e["target"]["value"])
                },
                    html.option({"value": "entry"}, "Entry Level"),
                    html.option({"value": "mid"}, "Mid Level"),
                    html.option({"value": "senior"}, "Senior Level"),
                    html.option({"value": "lead"}, "Lead/Management"),
                ),
            ),
            # Question Type
            html.div(
                {"className": "form-group"},
                html.label({"for": "question-type"}, "Question Type:"),
                html.select({
                    "id": "question-type", "value": question_type,
                    "onChange": lambda e: set_question_type(e["target"]["value"])
                },
                    html.option({"value": "behavioral"}, "Behavioral"),
                    html.option({"value": "technical"}, "Technical"),
                    html.option({"value": "mixed"}, "Mixed"),
                ),
            ),
            # Categories
            html.div(
                {"className": "form-group"},
                html.label({}, "Focus Areas:"),
                html.div(
                    {"className": "interview-categories"},
                    *[
                        html.label(
                            {"className": "category-label"},
                            html.input({
                                "type": "checkbox",
                                "value": category,
                                "checked": category in selected_categories,
                                "onChange": handle_category_change
                            }),
                            category
                        ) for category in categories
                    ]
                )
            ),
            # Generate button
            html.button(
                {"className": "btn btn-gradient", "onClick": handle_generate_questions},
                "Generate Interview Questions"
            ),
            # Output + Save as PDF
            html.div(
                {"className": "interview-output"},
                html.h3("Generated Questions:"),                (
                    html.i({"style": {"color": "#888"}}, "No questions generated yet.")
                    if not output_html.strip()
                    else html.div({
                        "dangerouslySetInnerHTML": {"__html": output_html},
                        "key": hash(output_html)
                    })
                )
            )
        )
    )