from reactpy import component, html, use_state
import threading, time
import aiohttp
import asyncio
import json
import random
import string
import components.common.calendar_db as calendar_db

DEBUG_MODE = False  # Set to True to enable verbose debug output

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)


async def call_ai_schedule(tasks):
    debug_print("call_ai_schedule called with tasks:", tasks)
    debug_print("---- USER INPUT ----")
    debug_print(json.dumps(tasks, indent=2, ensure_ascii=False))
    debug_print("---- END USER INPUT ----")
    instructions = [
        "You are a helpful assistant for organizing a user's daily tasks into a full calendar view.",
        "Given the following list of tasks as JSON, organize them into a detailed, efficient daily schedule.",
        "For each block in the day, output: type (prep, task, rest), name/label, start_time (hh:mm, 24h), duration (min), and any other relevant info.",
        "For each task, include a preparation block before it (if needed), the task itself, and a rest block after (if needed). Estimate the duration of each block.",
        "If a task has an estimated start time, try to honor it, but optimize the schedule overall.",
        "Estimate preparation time and rest time as needed, but do not ask the user for more info.",
        "Convert any natural language time expressions (e.g. 'half an hour', '8 in the morning', '1h 30min') to hh:mm or minutes as appropriate.",
        "Do not include any rest or preparation blocks with a duration of 0 minutes.",
        "Use your own judgement to estimate how important each task is, and if it can be delayed. If there is an overlap, try to push less important tasks later, or shorten the rest time to fit more important tasks.",
        "Return only a JSON array of all blocks in the day's schedule, in order. No explanations or markdown.",
    ]
    try:
        debug_print("Sending request to AI endpoint with payload:", json.dumps(tasks, indent=2, ensure_ascii=False))
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://ai.hackclub.com/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [
                        {"role": "system", "content": "\n".join(instructions)},
                        {"role": "user", "content": json.dumps(tasks)}
                    ]
                },
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                debug_print("AI endpoint response status:", resp.status)
                ai_raw = (await resp.json())["choices"][0]["message"]["content"]
        ai_clean = ai_raw.strip()
        if ai_clean.startswith("```"):
            ai_clean = ai_clean.lstrip("`\n ")
        if ai_clean.endswith("```"):
            ai_clean = ai_clean.rstrip("`\n ")
        if ai_clean.startswith("json"):
            ai_clean = ai_clean[4:].lstrip("\n ")
        debug_print("---- AI OUTPUT ----")
        debug_print(ai_clean)
        debug_print("---- END AI OUTPUT ----")
        scheduled = json.loads(ai_clean)
        return scheduled
    except Exception as e:
        debug_print(f"[TaskOrganizer] AI scheduling error: {e}")
        # Error will be set in the component's thread, just return empty
        return []

def generate_random_id(length=16):
    debug_print(f"Generating random ID of length {length}")
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_ics(organized_tasks, tzid, user_timezone=None):
    # Use detected user_timezone if available, else fallback to UTC
    tz = user_timezone or 'UTC'
    debug_print(f"[ICS] Called generate_ics with tzid={tzid}, user_timezone={user_timezone} (using: {tz})")
    debug_print(f"[TZ-DETECT] Using timezone for ICS: {tz}")
    import uuid
    from datetime import datetime, date, timedelta
    from zoneinfo import ZoneInfo
    today = date.today()
    now = datetime.now(ZoneInfo(tz))
    events = []
    for b in organized_tasks:
        debug_print("Processing block for ICS:", b)
        start = b.get('start_time', '08:00')
        duration = int(b.get('duration', 30))
        try:
            start_dt_naive = datetime.combine(today, datetime.strptime(start, "%H:%M").time())
        except Exception:
            debug_print(f"Skipping event due to invalid start time: {start}")
            continue
        end_dt_naive = start_dt_naive + timedelta(minutes=duration)
        summary = f"{b.get('type','Task').capitalize()}: {b.get('name', b.get('label',''))}"
        uid = str(uuid.uuid4()) + "@ai-task-organizer"
        dtstamp = now.strftime('%Y%m%dT%H%M%S')
        # Localize to detected timezone
        zone = ZoneInfo(tz)
        start_dt_local = start_dt_naive.replace(tzinfo=zone)
        end_dt_local = end_dt_naive.replace(tzinfo=zone)
        dtstart_str = start_dt_local.strftime('%Y%m%dT%H%M%S')
        dtend_str = end_dt_local.strftime('%Y%m%dT%H%M%S')
        events.append(
            f"""BEGIN:VEVENT\nUID:{uid}\nDTSTAMP:{dtstamp}\nSUMMARY:{summary}\nDTSTART;TZID={tz}:{dtstart_str}\nDTEND;TZID={tz}:{dtend_str}\nEND:VEVENT"""
        )
    ics_content = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "CALSCALE:GREGORIAN\n"
        "PRODID:-//AI Task Organizer//EN\n"
        "METHOD:PUBLISH\n"
        f"X-WR-TIMEZONE:{tz}\n"
        f"{chr(10).join(events)}\n"
        "END:VCALENDAR"
    )
    debug_print("Generated ICS content (with user timezone):\n", ics_content)
    return ics_content

@component
def TaskOrganizer():
    tasks, set_tasks = use_state([
        {"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}
    ])
    ai_estimate_all, set_ai_estimate_all = use_state(True)
    organized_tasks, set_organized_tasks = use_state([])
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    show_link_modal, set_show_link_modal = use_state(False)
    calendar_url, set_calendar_url = use_state("")
    user_id, set_user_id = use_state("")
    link_error, set_link_error = use_state("")
    user_timezone, set_user_timezone = use_state("")
    timezone_error, set_timezone_error = use_state("")

    # Save/Load box state
    link_mode, set_link_mode = use_state('existing')  # 'existing' or 'new'
    link_input, set_link_input = use_state("")
    timezone_ai_loading, set_timezone_ai_loading = use_state(False)
    timezone_ai_error, set_timezone_ai_error = use_state("")
    timezone_ai_input, set_timezone_ai_input = use_state("")

    copied_link, set_copied_link = use_state(False)

    def handle_copy_link(link):
        try:
            import pyperclip
            pyperclip.copy(link)
        except Exception:
            try:
                import subprocess
                subprocess.run(f'echo "{link.strip()}" | xclip -selection clipboard', shell=True)
            except Exception:
                pass
        set_copied_link(True)
        def clear():
            time.sleep(1.1)
            set_copied_link(False)
        threading.Thread(target=clear, daemon=True).start()

    def handle_task_change(idx, field, value):
        def updater(prev):
            updated = prev.copy()
            updated[idx] = {**updated[idx], field: value}
            return updated
        set_tasks(updater)

    def handle_ai_estimate_toggle(idx):
        def updater(prev):
            updated = prev.copy()
            updated[idx]["ai_estimate"] = not updated[idx].get("ai_estimate", False)
            if updated[idx]["ai_estimate"]:
                updated[idx]["prep_time"] = ""
            return updated
        set_tasks(updater)

    def add_task(_):
        set_tasks(lambda prev: prev + [{"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}])

    def remove_task(idx):
        set_tasks(lambda prev: [t for i, t in enumerate(prev) if i != idx])

    def handle_organize(_):
        debug_print("handle_organize called")
        set_loading(True)
        set_error("")
        async def ai_schedule():
            debug_print("ai_schedule thread started")
            await asyncio.sleep(0.7)
            debug_print("User tasks:", tasks)
            try:
                scheduled = await call_ai_schedule(tasks)
                debug_print("AI scheduled tasks:", scheduled)
                set_organized_tasks(scheduled)
            except Exception as e:
                set_error(f"AI scheduling error: {e}")
                set_organized_tasks([])
                debug_print("Error in ai_schedule:", e)
            set_loading(False)
            debug_print("ai_schedule thread finished")
        asyncio.create_task(ai_schedule())

    def handle_save_to_link(_):
        debug_print("handle_save_to_link called")
        set_show_link_modal(True)  # Always open modal immediately
        set_link_error("")
        # Only auto-generate a new link if 'Create New Link' is selected and no user_id
        if link_mode == 'new' and not user_id:
            new_id = generate_random_id()
            set_user_id(new_id)
            set_calendar_url(f"/calendars/{new_id}")
            debug_print("Auto-generated calendar link in modal:", f"/calendars/{new_id}")
            # Immediately save the current schedule to the new link if there are tasks
            if organized_tasks and len(organized_tasks) > 0:
                ics = generate_ics(organized_tasks, user_timezone or 'UTC', user_timezone or 'UTC')
                try:
                    debug_print(f"Auto-saving calendar for user_id {new_id} from modal")
                    calendar_db.save_calendar(new_id, ics)
                    set_link_error("")
                    debug_print(f"Calendar auto-saved for user_id {new_id} from modal")
                except Exception as e:
                    set_link_error(f"Failed to auto-save: {e}")
                    debug_print(f"Failed to auto-save calendar for user_id {new_id} from modal: {e}")

    def handle_generate_link(_):
        debug_print("handle_generate_link called")
        new_id = generate_random_id()
        set_user_id(new_id)
        set_calendar_url(f"/calendars/{new_id}")
        debug_print("Generated new calendar link:", f"/calendars/{new_id}")
        # Immediately save the current schedule to the new link
        if organized_tasks and len(organized_tasks) > 0:
            ics = generate_ics(organized_tasks, user_timezone or 'UTC', user_timezone or 'UTC')
            try:
                debug_print(f"Auto-saving calendar for user_id {new_id}")
                calendar_db.save_calendar(new_id, ics)
                set_link_error("")
                debug_print(f"Calendar auto-saved for user_id {new_id}")
            except Exception as e:
                set_link_error(f"Failed to auto-save: {e}")
                debug_print(f"Failed to auto-save calendar for user_id {new_id}: {e}")

    def handle_save_and_copy(_):
        debug_print("handle_save_and_copy called")
        if not user_id:
            debug_print("No user_id provided")
            set_link_error("Please paste or generate a calendar link.")
            return
        if not organized_tasks or len(organized_tasks) == 0:
            debug_print("No organized_tasks to save")
            set_link_error("No schedule to save. Please organize your day first.")
            return
        # Save the current schedule as a new or existing calendar
        ics = generate_ics(organized_tasks, user_timezone or 'UTC', user_timezone or 'UTC')
        calendar_db.save_calendar(user_id, ics)
        set_calendar_url(f"/calendars/{user_id}")
        set_link_error("")
        debug_print(f"Calendar saved for user_id {user_id}")
        # Copy the link
        handle_copy_link(f"https://mihais-ai-playground.xyz/calendars/{user_id}")

    def handle_link_mode_change(e):
        mode = e['target']['value']
        set_link_mode(mode)
        set_link_error("")
        set_link_input("")
        set_user_id("")
        set_calendar_url("")
        set_tasks([{"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}])
        if mode == 'new':
            # Immediately generate a new link and set user_id/calendar_url
            new_id = generate_random_id()
            set_user_id(new_id)
            set_calendar_url(f"/calendars/{new_id}")
            # Immediately save the current schedule to the new link if there are organized tasks
            if organized_tasks and len(organized_tasks) > 0:
                ics = generate_ics(organized_tasks, user_timezone or 'UTC', user_timezone or 'UTC')
                try:
                    calendar_db.save_calendar(new_id, ics)
                    set_link_error("")
                    debug_print(f"Calendar auto-saved for user_id {new_id} after switching to new link mode")
                except Exception as e:
                    set_link_error(f"Failed to auto-save: {e}")
                    debug_print(f"Failed to auto-save calendar for user_id {new_id} after switching to new link mode: {e}")

    def handle_link_input(e):
        val = e['target']['value'].strip()
        set_link_input(val)
        if link_mode == 'existing' and val:
            # Accept full URL, /calendars/ID, or just ID
            if "/calendars/" in val:
                uid = val.split("/calendars/")[-1].split("/")[0]
            else:
                uid = val
            set_user_id(uid)
            set_calendar_url(f"/calendars/{uid}")

            ics = calendar_db.get_calendar(uid)
            if ics:
                import re
                vevents = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics, re.DOTALL)
                tasks_for_day = []
                for block in vevents:
                    summary = re.search(r'SUMMARY:([^\n]+)', block)
                    dtstart = re.search(r'DTSTART:(\d{8})T(\d{4})Z', block)
                    if summary and dtstart:
                        summary_val = summary.group(1)
                        if not summary_val.lower().startswith('rest') and not summary_val.lower().startswith('prep'):
                            tasks_for_day.append({
                                'name': summary_val,
                                'prep_time': '',
                                'ai_estimate': False,
                                'est_start': dtstart.group(2)[:2] + ':' + dtstart.group(2)[2:],
                                'est_duration': ''
                            })
                set_tasks(tasks_for_day if tasks_for_day else [{"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}])
        elif link_mode == 'new':
            pass

    # Inject JS to auto-detect timezone and set it in state
    debug_print('[DEBUG] Injecting timezone detection JS')
    timezone_script = html.script({
        "dangerouslySetInnerHTML": {
            "__html": """
            (function() {
                function getOffsetString() {
                    var offset = -new Date().getTimezoneOffset(); // in minutes, positive for UTC+ zones
                    var sign = offset >= 0 ? '+' : '-';
                    var absOffset = Math.abs(offset);
                    var hours = Math.floor(absOffset / 60);
                    var mins = absOffset % 60;
                    return 'UTC' + sign + hours + (mins ? (':' + (mins < 10 ? '0' : '') + mins) : '');
                }
                try {
                    var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
                    if (!tz || tz === 'UTC') {
                        tz = getOffsetString();
                    }
                    window.dispatchEvent(new CustomEvent('timezone-detected', { detail: tz }));
                } catch (e) {
                    window.dispatchEvent(new CustomEvent('timezone-detected', { detail: getOffsetString() }));
                }
            })();
            """
        }
    })

    def on_timezone_detected(event):
        tz = event['detail']
        debug_print(f"[ReactPy] on_timezone_detected called with: {tz}")
        print(f"[DEBUG] [TZ-DETECT] Browser detected timezone: {tz}")
        if tz:
            debug_print(f"[ReactPy] Setting user_timezone to: {tz}")
            set_user_timezone(tz)
            set_timezone_error("")
        else:
            debug_print("[ReactPy] Could not detect timezone, defaulting to UTC")
            set_user_timezone("")
            set_timezone_error("Could not detect your timezone. Your browser may have blocked detection, so calendar times may be off (defaulting to UTC).")

    # Register event listener for timezone detection (ReactPy pattern)
    debug_print('[DEBUG] Registering timezone-detected event listener')
    html.script({
        "dangerouslySetInnerHTML": {
            "__html": """
            window.addEventListener('timezone-detected', function(e) {
                if (window.reactpyTimezoneCallback) window.reactpyTimezoneCallback(e.detail);
            });
            """
        }
    })
    # Attach callback to window (ReactPy pattern)
    import reactpy
    debug_print('[DEBUG] Registering reactpyTimezoneCallback')
    reactpy.hooks.use_effect(lambda: setattr(__import__('builtins'), 'reactpyTimezoneCallback', lambda tz: on_timezone_detected({'detail': tz})), [])

    # Show detected timezone for debugging
    debug_print(f"[ReactPy] Current detected user_timezone state: {user_timezone}")

    # List of common IANA timezones (can be expanded as needed)
    COMMON_TIMEZONES = [
        'Europe/Bucharest', 'Europe/Berlin', 'Europe/London', 'Europe/Paris', 'Europe/Moscow',
        'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
        'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai',
        'Australia/Sydney', 'Africa/Johannesburg', 'UTC'
    ]

    # Show a warning if timezone is not detected or is UTC or a UTC offset
    show_tz_warning = (not user_timezone or user_timezone.upper() == 'UTC' or user_timezone.startswith('UTC'))

    def handle_timezone_input_blur(e=None):
        if e is not None:
            val = e['target']['value']
            set_timezone_ai_input(val)
            # After setting, call the resolver
            handle_timezone_input_blur_or_enter(val)

    def handle_timezone_submit(_):
        # Get the value from the input box (from state)
        val = timezone_ai_input
        set_timezone_ai_input(val)
        handle_timezone_input_blur_or_enter(val)

    def handle_timezone_input_blur_or_enter(val=None):
        # Accept value as argument, or use state
        if val is None:
            val = timezone_ai_input
        val = val.strip()
        if not val:
            return
        set_timezone_ai_loading(True)
        set_timezone_ai_error("")
        # Call AI endpoint to resolve timezone
        async def resolve_timezone():
            try:
                prompt = f"Given the user input '{val}', return the best matching IANA timezone name (e.g. Europe/Moscow, America/New_York). Only return the timezone name, nothing else. If ambiguous, pick the most likely for a city or region."
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://ai.hackclub.com/chat/completions",
                        headers={"Content-Type": "application/json"},
                        json={
                            "messages": [
                                {"role": "system", "content": "You are a helpful assistant that maps user input to IANA timezone names."},
                                {"role": "user", "content": prompt}
                            ]
                        },
                        timeout=aiohttp.ClientTimeout(total=20)
                    ) as resp:
                        ai_raw = (await resp.json())["choices"][0]["message"]["content"].strip()
                # Clean up any code block formatting
                if ai_raw.startswith("`"):
                    ai_raw = ai_raw.lstrip("`\n ")
                if ai_raw.endswith("`"):
                    ai_raw = ai_raw.rstrip("`\n ")
                # Only take the first line, in case
                tz = ai_raw.split("\n")[0].strip()
                if tz:
                    set_user_timezone(tz)
                    set_timezone_ai_error("")
                    debug_print(f"[ReactPy] AI resolved timezone input '{val}' to: {tz}")
                else:
                    set_timezone_ai_error("Could not resolve to a valid timezone.")
            except Exception as ex:
                set_timezone_ai_error(f"AI error: {ex}")
            set_timezone_ai_loading(False)
        asyncio.create_task(resolve_timezone())
    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        timezone_script,
        html.link({"rel": "stylesheet", "href": f"/static/css/tools/task_organizer.css?v={CACHE_SUFFIX}"}),
        html.nav({"className": "navbar"}, html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")),
        (show_tz_warning and html.div({"className": "error-message"}, "Could not detect your timezone name. Calendar times may be off (using UTC offset only).")) or None,
        html.div({"style": {"color": "#888", "fontSize": "0.9em", "marginBottom": "0.5em"}}, f"Timezone: {user_timezone or 'Defaulting to UTC'}"),
        html.div({"className": "task-organizer"},
            show_tz_warning and html.div({"className": "timezone-row"},
                html.label({}, "Enter your city/region or timezone:"),
                html.input({
                    "type": "text",
                    "value": timezone_ai_input,
                    "onBlur": handle_timezone_input_blur,
                    "placeholder": "e.g. Bucharest, UTC+3, Europe/Moscow",
                    "className": "timezone-input"
                }),
                html.button({
                    "type": "button",
                    "onClick": handle_timezone_submit,
                    "disabled": timezone_ai_loading
                }, "Submit"),
                timezone_ai_loading and html.span({"className": "timezone-status loading"}, "Resolving...") or None,
                timezone_ai_error and html.span({"className": "timezone-status error"}, timezone_ai_error) or None
            ) or None,
            html.h2("AI Task Organizer"),
            html.div({"className": "form-group"},
                html.label({},
                    html.input({
                        "type": "checkbox",
                        "checked": ai_estimate_all,
                        "onChange": lambda e: set_ai_estimate_all(e["target"]["checked"])
                    }),
                    " Let AI estimate all preparation times"
                ),
            ),
            html.h3("Your Tasks"),
            html.div({"className": "tasks-list"},
                *[
                    html.div({"className": "task-card"},
                        html.input({
                            "type": "text",
                            "className": "input-task-title",
                            "value": t["name"],
                            "placeholder": "Task name",
                            "onBlur": lambda e, idx=i: handle_task_change(idx, "name", e["target"]["value"])
                        }),
                        html.input({
                            "type": "text",
                            "className": "input-task-prep",
                            "value": t["prep_time"],
                            "placeholder": "Preparation time (e.g. 'half an hour', '45 minutes')",
                            "onBlur": lambda e, idx=i: handle_task_change(idx, "prep_time", e["target"]["value"]),
                            "disabled": ai_estimate_all or t.get("ai_estimate", False),
                            "style": {"filter": "blur(2px)", "pointerEvents": "none"} if ai_estimate_all or t.get("ai_estimate", False) else {}
                        }),
                        html.input({
                            "type": "text",
                            "className": "input-task-est-start",
                            "value": t.get("est_start", ""),
                            "placeholder": "Est. start (hh:mm or 'quarter past 3')",
                            "onBlur": lambda e, idx=i: handle_task_change(idx, "est_start", e["target"]["value"])
                        }),
                        html.input({
                            "type": "text",
                            "className": "input-task-est-duration",
                            "value": t.get("est_duration", ""),
                            "placeholder": "Est. duration (e.g. '1 hour', '90 minutes')",
                            "onBlur": lambda e, idx=i: handle_task_change(idx, "est_duration", e["target"]["value"])
                        }),
                        html.label({},
                            html.input({
                                "type": "checkbox",
                                "checked": t.get("ai_estimate", False),
                                "onChange": lambda e, idx=i: handle_ai_estimate_toggle(idx),
                                "disabled": ai_estimate_all
                            }),
                            " Let AI estimate"
                        ),
                        (len(tasks) > 1 and html.button(
                            {"className": "btn btn-secondary btn-remove-task", "onClick": lambda e, idx=i: remove_task(idx)},
                            "Remove"
                        )) or None
                    ) for i, t in enumerate(tasks)
                ]
            ),
            html.button({"className": "btn btn-gradient add-task-btn", "onClick": add_task}, "+ Add Task"),
            html.button({"className": "btn btn-gradient", "onClick": handle_organize, "disabled": loading},
                "Organize My Day" if not loading else "Organizing..."
            ),
            error and html.div({"className": "error-message"}, error) or None,
            organized_tasks and html.div({"className": "interview-output"},
                html.h3("Full Day Schedule:"),
                html.div({"className": "schedule-list"},
                    *[
                        html.div({
                            "className": f"schedule-block schedule-{b.get('type','task').lower()}",
                            "key": f"block-{i}"
                        },
                            html.div({"className": "block-header"},
                                (
                                    b.get('type','task').lower() == 'prep' and html.span({"className": "block-icon prep"}, "🛠️")
                                ) or (
                                    b.get('type','task').lower() == 'task' and html.span({"className": "block-icon task"}, "✅")
                                ) or (
                                    b.get('type','task').lower() == 'rest' and html.span({"className": "block-icon rest"}, "☕")
                                ),
                                html.span({"className": "block-type"}, b.get('type','task').capitalize()),
                                html.span({"className": "block-title"}, b.get('name', b.get('label','')))
                            ),
                            html.div({"className": "block-details"},
                                html.span({"className": "block-time"}, f"Start: {b.get('start_time','auto')}"),
                                html.span({"className": "block-duration"}, f"Duration: {b.get('duration','?')} min")
                            )
                        ) for i, b in enumerate(organized_tasks)
                    ]
                ),
                html.button({"className": "btn btn-navy download-btn", "onClick": handle_save_to_link}, "Save to Link"),
                show_link_modal and html.div({"className": "modal-bg"},
                    html.div({"className": "modal"},
                        html.h4("Save to Calendar Link"),
                        html.div({"className": "save-load box"},
                            html.div({"className": "link-mode-group"},
                                html.label({"style": {"justifyContent": "center"}},
                                    html.input({
                                        "type": "radio", "name": "link_mode", "value": "existing", "checked": link_mode == 'existing', "onChange": handle_link_mode_change
                                    }),
                                    " Use Existing Link "
                                ),
                                html.label({"style": {"justifyContent": "center"}},
                                    html.input({
                                        "type": "radio", "name": "link_mode", "value": "new", "checked": link_mode == 'new', "onChange": handle_link_mode_change
                                    }),
                                    " Create New Link "
                                )
                            ),
                            (link_mode == 'existing' and html.input({
                                "type": "text", "placeholder": "Paste or enter calendar link/ID...", "value": link_input, "onInput": handle_link_input, "className": "calendar-link-input"
                            }) or None),
                            (link_error and html.div({"className": "error-message"}, link_error) or None),
                            (calendar_url and html.div({"style": {"display": "flex", "alignItems": "center", "gap": "0.5em", "marginTop": "0.7em"}},
                                html.p({}, "Add this link to Google Calendar via 'Add other calendars > From URL':"),
                                html.code({}, f"https://mihais-ai-playground.xyz{calendar_url}")
                            ) or None)
                        ),
                        html.button({"onClick": handle_save_and_copy, "className": "btn btn-gradient"}, ("Save and Copy" if not copied_link else "Copied!")),
                        link_error and html.div({"className": "error-message"}, link_error),
                        html.button({"onClick": lambda e: set_show_link_modal(False), "className": "btn btn-secondary", "style": {"marginTop": "1rem"}}, "Close")
                    )
                ) or None
            ) or None
        )
    )