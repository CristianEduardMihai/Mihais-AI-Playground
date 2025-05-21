from reactpy import component, html, use_state
import requests
import markdown

# Popular story-based subreddits and their descriptions
STORY_SUBREDDITS = {
    "r/AskReddit": "Crowdsourced stories, confessions, and wild questions answered by the masses.",
    "r/nosleep": "Creepy, horror, and supernatural stories told as if true.",
    "r/AITA": "Am I The Asshole? Moral dilemmas and social drama.",
    "r/TIFU": "Today I F***ed Up. Embarrassing, funny, or disastrous personal stories.",
    "r/relationships": "Relationship advice, drama, and confessions.",
    "r/ProRevenge": "Epic tales of revenge and justice served cold.",
    "r/MaliciousCompliance": "Stories of following the rules to the letter, with unexpected results.",
    "r/TrueOffMyChest": "Personal confessions and things people need to get off their chest.",
    "r/UnresolvedMysteries": "Unsolved mysteries and open-ended stories.",
    "r/ChoosingBeggars": "Stories of entitled people demanding more than they deserve.",
    "r/EntitledParents": "Tales of parents (and sometimes kids) with a wild sense of entitlement.",
    "r/LegalAdvice": "Legal drama, questions, and stories (not real legal advice!).",
    "r/Glitch_in_the_Matrix": "Weird, reality-bending, or deja-vu stories.",
    "r/TwoSentenceHorror": "Horror stories told in just two sentences.",
    "r/PettyRevenge": "Small-scale, satisfying revenge stories.",
    "r/Confession": "Anonymous confessions of all kinds.",
}

@component
def RedditLikeStoryteller():
    subreddit, set_subreddit = use_state("r/AskReddit")
    theme, set_theme = use_state("")
    story_html, set_story_html = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")

    def handle_generate_story(event):
        set_loading(True)
        set_error("")
        set_story_html("")
        try:
            prompt = (
                "You are a creative Reddit storyteller AI. "
                "Write a story in the style of the given subreddit, and if any, given theme. "
                "Format it as a Reddit post, with a title, body, and (if appropriate) comments or responses. "
                "Stay true to the tone, tropes, and conventions of the selected subreddit. "
                "Output only the story in Markdown, no extra commentary, explanations, or preamble. "
                "Do not include any text outside the Markdown story. "
                "Make a decently long story, but not too long. "
                "Add engaging comments or responses if the subreddit typically has them. "
                "Stay true to the subreddit style."
                "If the subreddit is r/TwoSentenceHorror, make it exactly two sentences. "
                "If the subreddit is r/AITA, include a verdict at the end (YTA, NTA, ESH, NAH). "
            )
            response = requests.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {
                            "role": "system",
                            "content": prompt
                        },
                        {"role": "user", "content": (
                            f"Write a story in the style of {subreddit}. "
                            f"Theme: {theme if theme.strip() else 'Any'}. "
                        )}
                    ]
                },
                timeout=60
            )
            if response.status_code != 200:
                raise RuntimeError(f"AI model returned {response.status_code}")
            data = response.json()
            md = data["choices"][0]["message"]["content"]
            html_content = markdown.markdown(md, extensions=["tables", "nl2br"])
            # Fix Reddit-style comment lists: convert lines starting with * u/ or *u/ to real Markdown list items
            import re
            html_content = re.sub(r'<li>\s*([*•])\s*u/', r'<li>u/', html_content)  # Remove stray asterisks/bullets
            html_content = re.sub(r'(?:<br\s*/?>)?\s*[*•]\s*(u/\w+)', r'<li>\1', html_content)
            # If the AI outputs comments as plain lines, convert them to <ul><li>...</li></ul>
            if re.search(r'\n[*•]\s*u/', md):
                comments = re.findall(r'^[*•]\s*(u/\w+.*)$', md, re.MULTILINE)
                if comments:
                    comments_html = '<ul>' + ''.join(f'<li>{c}</li>' for c in comments) + '</ul>'
                    html_content = html_content + comments_html
            set_story_html(f"<div class='markdown-body'>{html_content}</div>")
        except Exception as e:
            set_error(str(e))
        finally:
            set_loading(False)

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/reddit_like_storyyteller.css"}),
        html.nav(
            {"className": "navbar"},
            html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")
        ),
        html.div(
            {"className": "reddit-storyteller"},
            html.h2("Reddit-like Storyteller"),
            html.div(
                {"className": "form-group"},
                html.label({"for": "subreddit"}, "Choose a subreddit style:"),
                html.select({
                    "id": "subreddit",
                    "value": subreddit,
                    "onChange": lambda e: set_subreddit(e["target"]["value"])
                }, *[
                    html.option({"value": k}, f"{k} – {v}") for k, v in STORY_SUBREDDITS.items()
                ])
            ),
            html.div(
                {"className": "form-group"},
                html.label({"for": "theme"}, "Theme or prompt for the story:"),
                html.input({
                    "id": "theme",
                    "type": "text",
                    "value": theme,
                    "placeholder": "e.g. haunted house, awkward family dinner, time travel...",
                    "onChange": lambda e: set_theme(e["target"]["value"])
                })
            ),
            html.button(
                {
                    "className": "btn btn-gradient",
                    "onClick": handle_generate_story,
                    "disabled": loading or not subreddit
                },
                ("Generating..." if loading else "Generate Story")
            ),
            html.div(
                {"className": "story-output"},
                html.h3("Generated Story:"),
                (
                    html.i({"style": {"color": "#888"}}, "No story generated yet.")
                    if not story_html and not error else
                    html.div({
                        "dangerouslySetInnerHTML": {"__html": story_html},
                        "key": hash(story_html)
                    }) if story_html else
                    html.p({"style": {"color": "red"}}, f"Error: {error}")
                )
            )
        )
    )
