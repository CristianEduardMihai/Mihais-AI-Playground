from reactpy import component, html, use_state
import asyncio
import aiohttp
import markdown
from bs4 import BeautifulSoup
import re
import os
import time


# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[reddit_like_storyteller.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[reddit_like_storyteller.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[reddit_like_storyteller.py DEBUG]", *args)

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

import platform
arch = platform.machine().lower()
system = platform.system().lower()

@component
def RedditLikeStoryteller():
    subreddit, set_subreddit = use_state("r/AskReddit")
    theme, set_theme = use_state("")
    story_html, set_story_html = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    audio_url, set_audio_url = use_state("")
    audio_loading, set_audio_loading = use_state(False)
    audio_error, set_audio_error = use_state("")
    generate_comments, set_generate_comments = use_state(True)

    def handle_generate_story(_event=None):
        set_loading(True)
        set_error("")
        set_story_html("")
        def run_async():
            async def do_request():
                try:
                    if generate_comments:
                        system_prompt = (
                            "You are a creative Reddit storyteller AI. "
                            "Write a story in the style of the given subreddit, and if any, given theme. "
                            "Include engaging comments or responses if the subreddit typically has them. "
                            "Format it as a Reddit post, with a title, body, and (if appropriate) comments or responses. "
                            "Make the names of the comments and users realistic, but do not use real Reddit usernames. "
                            "Stay true to the tone, tropes, and conventions of the selected subreddit. "
                            "Output only the story in Markdown, no extra commentary, explanations, or preamble. "
                            "Do not include any text outside the Markdown story. "
                            "Make a decently long story, but not too long. "
                            "Add engaging comments or responses if the subreddit typically has them. "
                            "Stay true to the subreddit style. "
                            "For the comments, use the format: - **u/username** comment text. "
                            "If the subreddit is r/TwoSentenceHorror, make it exactly two sentences. "
                            "If the subreddit is r/AITA, include a verdict at the end (YTA, NTA, ESH, NAH)."
                        )
                    else:
                        system_prompt = (
                            "You are a creative Reddit storyteller AI. "
                            "Write a story in the style of the given subreddit, and if any, given theme. "
                            "Do NOT include any comments or responses, only the main story body. "
                            "Format it as a Reddit post, with a title and body only. "
                            "Make the story realistic and true to the tone, tropes, and conventions of the selected subreddit. "
                            "Output only the story in Markdown, no extra commentary, explanations, or preamble. "
                            "Do not include any text outside the Markdown story. "
                            "Make a decently long story, but not too long. "
                            "If the subreddit is r/TwoSentenceHorror, make it exactly two sentences. "
                            "If the subreddit is r/AITA, include a verdict at the end (YTA, NTA, ESH, NAH)."
                        )
                    user_prompt = (
                        f"Write a story in the style of {subreddit}. "
                        f"Theme: {theme.strip() or 'Any'}."
                    )
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://ai.hackclub.com/chat/completions",
                            headers={"Content-Type": "application/json"},
                            json={
                                "messages": [
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": user_prompt},
                                ]
                            },
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as resp:
                            resp.raise_for_status()
                            data = await resp.json()
                    md = data["choices"][0]["message"]["content"]
                    html_content = markdown.markdown(md, extensions=["tables", "nl2br"])
                    html_content = re.sub(r'<li>\s*([*•])\s*u/', r'<li>u/', html_content)
                    html_content = re.sub(r'(?:<br\s*/?>)?\s*[*•]\s*(u/\w+)', r'<li>\1', html_content)
                    comments = re.findall(r'^[*•]\s*(u/\w+.*)$', md, re.MULTILINE)
                    if comments:
                        comments_html = "<ul>" + "".join(f"<li>{c}</li>" for c in comments) + "</ul>"
                        html_content += comments_html
                    set_story_html(f"<div class='markdown-body'>{html_content}</div>")
                except Exception as e:
                    set_error(str(e))
                finally:
                    set_loading(False)
            asyncio.run(do_request())
        import threading
        threading.Thread(target=run_async, daemon=True).start()

    def extract_story_text(md: str) -> str:
        """Strip out comments/verdicts for plain narration to TTS."""
        lines = md.splitlines()
        filtered = [
            l for l in lines
            if not l.strip().startswith(('* u/', '*u/', '- u/', '-u/', 'YTA', 'NTA', 'ESH', 'NAH'))
        ]
        text = "\n".join(filtered)
        text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^[-*]\s+', '', text, flags=re.MULTILINE)
        return text.strip()

    # Set piper_bin_dir
    if system == "windows":
        piper_bin_dir = os.path.join("server-assets", "piper", "win-amd64")
    elif system == "linux":
        if arch in ("x86_64", "amd64"):
            piper_bin_dir = os.path.join("server-assets", "piper", "linux-amd64")
        elif arch in ("aarch64", "arm64"):
            piper_bin_dir = os.path.join("server-assets", "piper", "linux-arm64")
        else:
            piper_bin_dir = os.path.join("server-assets", "piper", "linux-amd64")  # fallback
    else:
        piper_bin_dir = os.path.join("server-assets", "piper", "linux-amd64")  # fallback

    voice_model = os.path.join("server-assets", "piper", "lessac-medium", "en_US-lessac-medium.onnx")
    voice_config = os.path.join("server-assets", "piper", "lessac-medium", "en_US-lessac-medium.onnx.json")

    def handle_generate_audio(_event=None):
        set_audio_loading(True)
        set_audio_error("")
        set_audio_url("")
        import threading
        def run_piper():
            try:
                temp_dir = os.path.join("static", "assets", "tts_temp")
                os.makedirs(temp_dir, exist_ok=True)
                # Prepare text
                soup = BeautifulSoup(story_html, "html.parser")
                text = soup.get_text("\n").strip()
                if not text:
                    set_audio_error("No story text to synthesize.")
                    set_audio_loading(False)
                    return
                # Generate unique filename by using a timestamp
                ts = int(time.time() * 1000)
                wav_path = os.path.join(temp_dir, f"tts_story_{ts}.wav")
                # Piper binary and model paths
                if system == "windows":
                    piper_bin = os.path.join(piper_bin_dir, "piper.exe")
                else:
                    piper_bin = os.path.join(piper_bin_dir, "piper")
                import subprocess
                try:
                    result = subprocess.run(
                        [piper_bin, "--model", voice_model, "--config", voice_config, "--output_file", wav_path],
                        input=text.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=60
                    )
                    if result.returncode != 0:
                        set_audio_error(f"Piper error: {result.stderr.decode('utf-8')}")
                        set_audio_loading(False)
                        return
                except Exception as e:
                    set_audio_error(f"Piper execution failed: {e}")
                    set_audio_loading(False)
                    return
                # Set audio URL for playback, but check file exists and is non-empty
                import time as _time
                for _ in range(10):  # Wait up to 1s for file to be written
                    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1000:
                        break
                    _time.sleep(0.1)
                if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
                    set_audio_error("Audio file was not created or is empty.")
                else:
                    # Add a small delay to ensure file is ready before setting URL
                    _time.sleep(0.15)
                    rel_url = f"/static/assets/tts_temp/tts_story_{ts}.wav"
                    set_audio_url(rel_url)
            except Exception as e:
                set_audio_error(f"Audio generation failed: {e}")
            set_audio_loading(False)
        threading.Thread(target=run_piper, daemon=True).start()

    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/reddit_like_storyteller.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div(
            {"className": "reddit-storyteller"},
            html.h2("Reddit-style Storyteller"),
            html.div(
                {"className": "form-group"},
                html.label({"for": "theme"}, "Theme or prompt for the story:"),
                html.input({
                    "id": "theme",
                    "type": "text",
                    "value": theme,
                    "placeholder": "e.g. haunted house, awkward family dinner…",
                    "onBlur": lambda e: set_theme(e["target"]["value"])
                })
            ),
            html.div(
                {"className": "form-group"},
                html.label({"for": "subreddit"}, "Choose a subreddit style:"),
                html.select(
                    {
                        "id": "subreddit",
                        "value": subreddit,
                        "onChange": lambda e: set_subreddit(e["target"]["value"])
                    },
                    *[
                        html.option({"value": k}, f"{k} – {v}")
                        for k, v in STORY_SUBREDDITS.items()
                    ]
                )
            ),
            html.div(
                {"className": "form-group"},
                html.label({"for": "generate-comments"},
                    html.input({
                        "id": "generate-comments",
                        "type": "checkbox",
                        "checked": generate_comments,
                        "onChange": lambda e: set_generate_comments(e["target"]["checked"])
                    }),
                    " Include comments (if subreddit style supports them)"
                )
            ),
            # Button area: show Generate Story or Generate Audio depending on state
            html.div(
                {"className": "button-area"},
                (
                    (not story_html and not error) or loading
                )
                and html.button(
                    {
                        "className": f"btn btn-gradient{' disabled' if loading or not subreddit else ''}",
                        "onClick": handle_generate_story if not (loading or not subreddit) else None,
                        "disabled": loading or not subreddit
                    },
                    "Generating…" if loading else "Generate Story"
                )
                or (
                    story_html and not loading
                )
                and html.button(
                    {
                        "className": f"btn btn-blue-gradient{' disabled' if audio_loading or audio_url else ''}",
                        "onClick": handle_generate_audio if not (audio_loading or audio_url) else None,
                        "disabled": audio_loading or audio_url
                    },
                    "⚙️Generating Audio…" if audio_loading else (
                        "🔊 Generate Audio" if not audio_url else "🔊 Audio Ready"
                    )
                )
            ),
            # Audio player and error, above the story markdown
            (audio_loading or audio_url or audio_error) and html.div(
                {"className": "audio-area"},
                audio_loading and html.div({"className": "audio-loading"}, "") or None,
                audio_error and html.p({"style": {"color": "red"}}, audio_error) or None,
                audio_url and html.audio({
                    "controls": True,
                    "src": audio_url,
                    "key": audio_url,  # Force re-mount on new audio
                    "style": {"marginTop": "1rem", "width": "100%"},
                    "onError": lambda e: set_audio_error("Audio failed to load. Try again or check file permissions.")
                }) or None
            ),
            html.div(
                {"className": "story-output"},
                html.h3("Generated Story:"),
                (not story_html and not error) and html.i({"style": {"color": "#888"}}, "No story generated yet.")
                or (story_html and html.div({"dangerouslySetInnerHTML": {"__html": story_html}, "key": hash(story_html)}))
                or html.p({"style": {"color": "red"}}, f"Error: {error}")
            )
        )
    )