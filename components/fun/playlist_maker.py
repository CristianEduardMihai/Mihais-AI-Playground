from reactpy import component, html, use_state
import asyncio
import threading
from components.common.config import CACHE_SUFFIX
import os
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import re
import json
import aiohttp


# Load Spotify credentials from .env
load_dotenv(os.path.join(os.path.dirname(__file__), '../../server-assets/persistent/.env'))

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())


# ───────────────────────────────────────────────────────────────────────────────
#  DEBUG LOGGER
# ───────────────────────────────────────────────────────────────────────────────

try:
    from components.common.config import DEBUG_MODE, REACTPY_DEBUG_MODE
    if REACTPY_DEBUG_MODE:
        import reactpy
        reactpy.config.REACTPY_DEBUG_MODE.current = True
        print("[playlist_maker.py DEBUG] REACTPY_DEBUG_MODE imported from config.py, using value:", REACTPY_DEBUG_MODE)
    if DEBUG_MODE:
        print("[playlist_maker.py DEBUG] DEBUG_MODE imported from config.py, using value:", DEBUG_MODE)
except ImportError:
    DEBUG_MODE = False
    print("Warning: DEBUG_MODE not imported from config.py, using default value False.")

def debug_log(*args):
    if DEBUG_MODE:
        print("[playlist_maker.py DEBUG]", *args)


@component
def PlaylistMaker():
    search, set_search = use_state("")
    num_songs, set_num_songs = use_state("6")
    info_open, set_info_open = use_state(False)
    loading, set_loading = use_state(False)
    results, set_results = use_state([])
    error, set_error = use_state("")

    def handle_info_click(event):
        set_info_open(lambda prev: not prev)

    def handle_search_input(e):
        set_search(e["target"]["value"])

    def handle_num_songs_input(e):
        set_num_songs(e["target"]["value"])

    def handle_submit(event):
        set_loading(True)
        set_results([])
        set_error("")
        debug_log("Submitting search:", search, "Num songs:", num_songs)
        def run_async():
            async def do_request():
                try:
                    # Always use AI to generate the song list, even for Spotify URLs
                    if is_spotify_url(search):
                        # If playlist, get all song titles/artists; if track, get that song
                        if "/playlist/" in search:
                            debug_log("Detected Spotify playlist URL")
                            playlist_songs = get_spotify_playlist_tracks(search)
                            if not playlist_songs:
                                debug_log("Playlist is empty or inaccessible (possibly private or invalid)")
                                set_error("Could not access this playlist. It may be private or invalid. Please use a public playlist or try another input.")
                                set_loading(False)
                                return
                            ai_input = ", ".join(f"{s['title']} by {s['artist']}" for s in playlist_songs)
                            # Instruct AI to avoid recommending songs already in the playlist
                            ai_prompt = (
                                f"User provided a playlist containing: {ai_input}. "
                                f"Recommend {num_songs} songs that are NOT already in this playlist. "
                                f"You must not recommend any song that is already in the provided playlist. "
                                f"List only new songs, not present in the user's playlist."
                            )
                            debug_log("AI prompt for playlist:", ai_prompt)
                            songs = await ai_get_song_list(ai_prompt, int(num_songs))
                        elif "/track/" in search:
                            debug_log("Detected Spotify track URL")
                            m = re.search(r"track/([a-zA-Z0-9]+)", search)
                            if m:
                                track_id = m.group(1)
                                track = sp.track(track_id)
                                debug_log("Fetched track info:", track)
                                ai_prompt = f"User input: {track['name']} by {track['artists'][0]['name']}."
                                debug_log("AI prompt for track:", ai_prompt)
                                songs = await ai_get_song_list(ai_prompt, int(num_songs))
                            else:
                                debug_log("Could not extract track ID from URL")
                                songs = []
                        else:
                            debug_log("Spotify URL but not playlist or track; treating as text input.")
                            songs = await ai_get_song_list(search, int(num_songs))
                    else:
                        debug_log("Non-Spotify input. Feeding directly to AI.")
                        songs = await ai_get_song_list(search, int(num_songs))
                    debug_log("Song list to embed:", songs)
                    # 2. For each song, get Spotify track ID
                    embeds = []
                    not_found = []
                    for song in songs[:int(num_songs)]:
                        debug_log(f"Looking up Spotify track for: {song}")
                        track_id = get_spotify_track_embed(song["title"], song["artist"])
                        if track_id:
                            debug_log(f"Embed for {song['title']} by {song['artist']}: {track_id}")
                            embeds.append({"track_id": track_id, "title": song["title"], "artist": song["artist"]})
                        else:
                            debug_log(f"No Spotify track found for: {song}")
                            not_found.append(song)
                    # If not enough found, fill with artist top tracks
                    if len(embeds) < int(num_songs) and songs:
                        debug_log(f"Filling {int(num_songs)-len(embeds)} missing songs with artist top tracks")
                        embeds = fill_missing_songs_with_artist_top(songs, embeds, int(num_songs))
                    set_results(embeds)
                except Exception as e:
                    debug_log("Error in do_request:", e)
                    set_error(str(e))
                finally:
                    set_loading(False)
            asyncio.run(do_request())
        threading.Thread(target=run_async, daemon=True).start()

    def get_spotify_track_embed(track_name, artist_name):
        debug_log(f"Searching Spotify for: {track_name} by {artist_name}")
        try:
            result = sp.search(q=f'track:{track_name} artist:{artist_name}', type='track', limit=1)
            tracks = result.get('tracks', {}).get('items', [])
            if tracks:
                track_id = tracks[0]['id']
                debug_log(f"Found track ID: {track_id}")
                return track_id
            else:
                debug_log("No track found for:", track_name, artist_name)
                return None
        except Exception as e:
            debug_log("Spotify search error:", e)
            return None

    def get_spotify_playlist_tracks(playlist_url):
        debug_log(f"Fetching playlist tracks for: {playlist_url}")
        try:
            playlist_id = playlist_url.split("playlist/")[-1].split("?")[0]
            results = sp.playlist_tracks(playlist_id)
            tracks = []
            for item in results['items']:
                track = item['track']
                tracks.append({
                    'title': track['name'],
                    'artist': track['artists'][0]['name']
                })
            debug_log(f"Found {len(tracks)} tracks in playlist")
            return tracks
        except Exception as e:
            debug_log("Spotify playlist fetch error:", e)
            return []

    def is_spotify_url(text):
        return 'open.spotify.com' in text

    async def ai_get_song_list(user_input, num_songs=6):
        debug_log("Using AI to parse user input:", user_input, "num_songs:", num_songs)
        prompt = (
            f"You are a helpful music assistant. "
            f"Given a user input (which may be a playlist, a song, or just text), "
            f"generate a playlist of exactly {num_songs} songs the user would like, based on their input. "
            f"You may suggest songs by different artists, not just the same artist. "
            f"Output ONLY a JSON array of objects with 'title' and 'artist' for each song. "
            f"Do not include any explanation, comments, or text outside the JSON. "
            f"If you cannot find enough, fill the rest with popular songs in a similar style. "
            f"Example output: [\n  {{\"title\": \"Song Name\", \"artist\": \"Artist Name\"}}, ... ]\n"
        )
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": user_input}
                    ]
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"AI model returned {response.status}")
                data = await response.json()
        content = data["choices"][0]["message"]["content"]
        debug_log("AI raw output:", content)
        content = content.strip()
        if content.startswith('```json') and content.endswith('```'):
            content = content[len('```json'):].strip()
            content = content[:-3].strip()
        elif content.startswith('```') and content.endswith('```'):
            content = content[3:-3].strip()
        try:
            songs = json.loads(content)
            debug_log("AI parsed songs:", songs)
            return songs
        except Exception as e:
            debug_log("AI JSON parse error:", e)
            return []

    def get_artist_top_tracks(artist_name, exclude_titles=None, country='US'):
        debug_log(f"Getting top tracks for artist: {artist_name}, excluding: {exclude_titles}")
        try:
            # Search for artist
            result = sp.search(q=f'artist:{artist_name}', type='artist', limit=1)
            artists = result.get('artists', {}).get('items', [])
            if not artists:
                debug_log(f"No artist found for: {artist_name}")
                return []
            artist_id = artists[0]['id']
            top_tracks = sp.artist_top_tracks(artist_id, country=country)
            exclude_titles = set(t.lower() for t in (exclude_titles or []))
            filtered = []
            for t in top_tracks['tracks']:
                if t['name'].lower() not in exclude_titles:
                    filtered.append({
                        "title": t['name'],
                        "artist": artist_name,
                        "track_id": t['id']
                    })
            debug_log(f"Top tracks found: {filtered}")
            return filtered
        except Exception as e:
            debug_log("Error getting artist top tracks:", e)
            return []

    def fill_missing_songs_with_artist_top(songs, found_embeds, num_needed):
        from collections import Counter
        artist_counts = Counter(song['artist'] for song in songs)
        main_artist = artist_counts.most_common(1)[0][0] if artist_counts else None
        exclude_titles = [embed['title'] for embed in found_embeds]
        if main_artist:
            top_tracks = get_artist_top_tracks(main_artist, exclude_titles=exclude_titles)
            for t in top_tracks:
                if len(found_embeds) >= num_needed:
                    break
                # Use track_id directly
                found_embeds.append({"track_id": t['track_id'], "title": t['title'], "artist": t['artist']})
        return found_embeds

    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/global.css?v={CACHE_SUFFIX}"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/fun/playlist_maker.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "global-home-btn-row"}, html.a({"href": "/", "className": "global-home-btn"}, "🏠 Home")),
        html.div({"className": "playlist-maker"},
            html.img({"src": "/static/assets/Spotify_logo_with_text.svg", "alt": "Spotify Logo", "className": "playlist-logo"}),
            html.h2({"className": "playlist-title"}, "Playlist Maker"),
            html.div({"className": "playlist-form"},
                html.div({"className": "playlist-label-group"},
                    html.div({"className": "playlist-label-row"},
                        html.button({
                            "type": "button",
                            "className": "home-info-tooltip info-btn",
                            "onClick": handle_info_click
                        }, "i"),
                        html.label({"for": "playlist-search", "className": "playlist-label"}, "Songs/artists/playlists/theme you want")
                    ),
                    html.input({
                        "id": "playlist-search",
                        "type": "text",
                        "value": search,
                        "onBlur": handle_search_input,
                        "placeholder": "Paste a playlist/song link, or type an artist/song...",
                        "className": "playlist-input"
                    })
                ),
                (html.div({"className": "home-info-tooltip info-tooltip-open"},
                    "Enter an existing playlist/song link, artist/song name, or what kind of songs you want. You can paste a Spotify URL or just type names!"
                ) if info_open else None),
                html.div({"className": "form-group playlist-form-row"},
                    html.label({"for": "num-songs", "className": "playlist-label"}, "How many songs?"),
                    html.input({
                        "id": "num-songs",
                        "type": "number",
                        "min": "1",
                        "max": "12",
                        "value": num_songs,
                        "onBlur": handle_num_songs_input,
                        "className": "playlist-num-input"
                    })
                ),
                html.button({
                    "type": "button",
                    "className": f"btn btn-gradient{' disabled' if loading else ''} playlist-submit-btn",
                    "onClick": handle_submit if not loading else None,
                    "disabled": loading
                },
                    "Finding songs..." if loading else "Recommend Songs"
                ),
                error and html.div({"className": "playlist-error"}, error),
                html.div({"className": "playlist-results"},
                    *[
                        html.div({"className": "playlist-embed-row"},
                            html.iframe({
                                "className": "playlist-embed",
                                "style": {"borderRadius": "12px"},
                                "src": f"https://open.spotify.com/embed/track/{song['track_id']}?utm_source=generator",
                                "width": "100%",
                                "height": "152",
                                "frameBorder": "0",
                                "allow": "autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture",
                                "loading": "lazy",
                                "allowfullscreen": True
                            })
                        ) for song in results
                    ]
                )
            )
        )
    )
