from reactpy import component, html, use_state
import urllib.parse
import datetime
import threading, time
import re
import requests
import json
import random
import string
import components.common.calendar_db as calendar_db

DEBUG_MODE = False  # Set to True to enable verbose debug output

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG]", *args, **kwargs)


def call_ai_schedule(tasks):
    debug_print("call_ai_schedule called with tasks:", tasks)
    debug_print("---- USER INPUT ----")
    debug_print(json.dumps(tasks, indent=2, ensure_ascii=False))
    debug_print("---- END USER INPUT ----")
    instructions = [
        "You are a helpful assistant for organizing a user's daily tasks into a full calendar view.",
        "Given the following list of tasks as JSON, organize them into a detailed, efficient daily schedule.",
        "For each block in the day, output: type (prep, task, rest), name/label, start_time (hh:mm, 24h), duration (min), and any other relevant info.",
        "For each task, include a preparation block before it (if needed), the task itself, and a rest block after (if needed).",
        "If a task has an estimated start time, try to honor it, but optimize the schedule overall.",
        "Estimate preparation time and rest time as needed, but do not ask the user for more info.",
        "Convert any natural language time expressions (e.g. 'half an hour', '8 in the morning', '1h 30min') to hh:mm or minutes as appropriate.",
        "Do not include any rest or preparation blocks with a duration of 0 minutes.",
        "Use your own judgement to estimate how important each task is, and if it can be delayed. If there is an overlap, try to push less important tasks later, or shorten the rest time to fit more important tasks.",
        "Return only a JSON array of all blocks in the day's schedule, in order. No explanations or markdown.",
    ]
    try:
        debug_print("Sending request to AI endpoint with payload:", json.dumps(tasks, indent=2, ensure_ascii=False))
        resp = requests.post(
            "https://ai.hackclub.com/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": "\n".join(instructions)},
                    {"role": "user", "content": json.dumps(tasks)}
                ]
            },
            timeout=60
        )
        debug_print("AI endpoint response status:", resp.status_code)
        debug_print("AI endpoint response body:", resp.text)
        ai_raw = resp.json()["choices"][0]["message"]["content"]
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

def generate_ics(organized_tasks):
    debug_print("Generating ICS for organized tasks:", organized_tasks)
    # Standards-compliant .ics generator using actual AI-scheduled times
    import uuid
    from datetime import datetime, date, timedelta, timezone
    
    today = date.today()
    now = datetime.now(timezone.utc)
    events = []
    for b in organized_tasks:
        debug_print("Processing block for ICS:", b)
        start = b.get('start_time', '08:00')
        duration = int(b.get('duration', 30))
        # Parse start time (assume 24h format from AI)
        try:
            start_dt = datetime.combine(today, datetime.strptime(start, "%H:%M").time(), tzinfo=timezone.utc)
        except Exception:
            debug_print(f"Skipping event due to invalid start time: {start}")
            continue
        end_dt = start_dt + timedelta(minutes=duration)
        summary = f"{b.get('type','Task').capitalize()}: {b.get('name', b.get('label',''))}"
        uid = str(uuid.uuid4()) + "@ai-task-organizer"
        dtstamp = now.strftime('%Y%m%dT%H%M%SZ')
        events.append(
            f"""BEGIN:VEVENT\nUID:{uid}\nDTSTAMP:{dtstamp}\nSUMMARY:{summary}\nDTSTART:{start_dt.strftime('%Y%m%dT%H%M%SZ')}\nDTEND:{end_dt.strftime('%Y%m%dT%H%M%SZ')}\nEND:VEVENT"""
        )
    ics_content = (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "CALSCALE:GREGORIAN\n"
        "PRODID:-//AI Task Organizer//EN\n"
        "METHOD:PUBLISH\n"
        "X-WR-TIMEZONE:UTC\n"
        f"{chr(10).join(events)}\n"
        "END:VCALENDAR"
    )
    debug_print("Generated ICS content:\n", ics_content)
    return ics_content

@component
def TaskOrganizer():
    tasks, set_tasks = use_state([
        {"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}
    ])
    ai_estimate_all, set_ai_estimate_all = use_state(True)
    organized_tasks, set_organized_tasks = use_state([])
    calendar_link, set_calendar_link = use_state("")
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    show_link_modal, set_show_link_modal = use_state(False)
    calendar_url, set_calendar_url = use_state("")
    user_id, set_user_id = use_state("")
    link_error, set_link_error = use_state("")

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
        def ai_schedule():
            debug_print("ai_schedule thread started")
            time.sleep(0.7)
            debug_print("User tasks:", tasks)
            try:
                scheduled = call_ai_schedule(tasks)
                debug_print("AI scheduled tasks:", scheduled)
                set_organized_tasks(scheduled)
                # Generate Google Calendar link for the scheduled block (use first and last block)
                if scheduled:
                    debug_print("Generating Google Calendar link for scheduled block")
                    min_start = min(
                        int(b['start_time'].split(':')[0]) * 60 + int(b['start_time'].split(':')[1])
                        for b in scheduled if 'start_time' in b and re.match(r"^\d{1,2}:\d{2}$", b['start_time'])
                    ) if scheduled else 0
                    max_end = max(
                        int(b['start_time'].split(':')[0]) * 60 + int(b['start_time'].split(':')[1]) + int(b.get('duration', 30))
                        for b in scheduled if 'start_time' in b and re.match(r"^\d{1,2}:\d{2}$", b['start_time'])
                    ) if scheduled else 60
                    today = datetime.datetime.now().replace(second=0, microsecond=0)
                    start_dt = today.replace(hour=min_start // 60, minute=min_start % 60)
                    end_dt = today.replace(hour=max_end // 60, minute=max_end % 60)
                    event_title = "My Organized Tasks"
                    details = "\n".join(
                        f"{i+1}. {b.get('type','task').capitalize()}: {b.get('name', b.get('label',''))} (Start: {b.get('start_time','auto')}, Duration: {b.get('duration','?')} min)" for i, b in enumerate(scheduled)
                    )
                    url = (
                        "https://calendar.google.com/calendar/render?action=TEMPLATE"
                        f"&text={urllib.parse.quote(event_title)}"
                        f"&details={urllib.parse.quote(details)}"
                        f"&dates={start_dt.strftime('%Y%m%dT%H%M%S')}/{end_dt.strftime('%Y%m%dT%H%M%S')}"
                    )
                    set_calendar_link(url)
                    debug_print("Set calendar link:", url)
                else:
                    set_calendar_link("")
                    debug_print("No schedule, calendar link cleared")
            except Exception as e:
                set_error(f"AI scheduling error: {e}")
                set_organized_tasks([])
                set_calendar_link("")
                debug_print("Error in ai_schedule:", e)
            set_loading(False)
            debug_print("ai_schedule thread finished")
        threading.Thread(target=ai_schedule, daemon=True).start()

    def handle_save_to_link(_):
        debug_print("handle_save_to_link called")
        set_show_link_modal(True)
        set_link_error("")
        set_calendar_url("")
        set_user_id("")

    def handle_generate_link(_):
        debug_print("handle_generate_link called")
        new_id = generate_random_id()
        set_user_id(new_id)
        set_calendar_url(f"/calendars/{new_id}")
        debug_print("Generated new calendar link:", f"/calendars/{new_id}")
        # Immediately save the current schedule to the new link
        if organized_tasks and len(organized_tasks) > 0:
            ics = generate_ics(organized_tasks)
            try:
                debug_print(f"Auto-saving calendar for user_id {new_id}")
                calendar_db.save_calendar(new_id, ics)
                set_link_error("")
                debug_print(f"Calendar auto-saved for user_id {new_id}")
            except Exception as e:
                set_link_error(f"Failed to auto-save: {e}")
                debug_print(f"Failed to auto-save calendar for user_id {new_id}: {e}")

    def handle_save_schedule(_):
        debug_print("handle_save_schedule called")
        if not user_id:
            debug_print("No user_id provided")
            set_link_error("Please paste or generate a calendar link.")
            return
        if not organized_tasks or len(organized_tasks) == 0:
            debug_print("No organized_tasks to save")
            set_link_error("No schedule to save. Please organize your day first.")
            return
        ics = generate_ics(organized_tasks)
        try:
            debug_print(f"Saving calendar for user_id {user_id}")
            calendar_db.save_calendar(user_id, ics)
            set_calendar_url(f"/calendars/{user_id}")
            set_link_error("")
            debug_print(f"Calendar saved for user_id {user_id}")
        except Exception as e:
            set_link_error(f"Failed to save: {e}")
            debug_print(f"Failed to save calendar for user_id {user_id}: {e}")

    def handle_paste_link(e):
        debug_print("handle_paste_link called with:", e)
        val = e["target"]["value"].strip()
        if val:
            # Accept full URL, /calendars/ID, or just ID
            if "/calendars/" in val:
                # Extract everything after the last /calendars/
                uid = val.split("/calendars/")[-1].split("/")[0]
                set_user_id(uid)
                set_calendar_url(f"/calendars/{uid}")
                debug_print("Pasted calendar link, extracted user_id:", uid)
            else:
                set_user_id(val)
                set_calendar_url(f"/calendars/{val}")
                debug_print("Pasted calendar id:", val)
            # Auto-save to pasted link if there is a schedule
            target_id = val.split("/calendars/")[-1].split("/")[0] if "/calendars/" in val else val
            if organized_tasks and len(organized_tasks) > 0:
                ics = generate_ics(organized_tasks)
                try:
                    debug_print(f"Auto-saving calendar for pasted user_id {target_id}")
                    calendar_db.save_calendar(target_id, ics)
                    set_link_error("")
                    debug_print(f"Calendar auto-saved for pasted user_id {target_id}")
                except Exception as e:
                    set_link_error(f"Failed to auto-save: {e}")
                    debug_print(f"Failed to auto-save calendar for pasted user_id {target_id}: {e}")

    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": "/static/css/tools/task_organizer.css"}),
        html.nav({"className": "navbar"}, html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")),
        html.div({"className": "task-organizer"},
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
                html.ul(
                    {},
                    *[html.li({}, f"{i+1}. {b.get('type','task').capitalize()}: {b.get('name', b.get('label',''))} (Start: {b.get('start_time','auto')}, Duration: {b.get('duration','?')} min)") for i, b in enumerate(organized_tasks)]
                ),
                html.button({"className": "btn btn-navy download-btn", "onClick": handle_save_to_link}, "Save to Link"),
                show_link_modal and html.div({"className": "modal-bg"},
                    html.div({"className": "modal"},
                        html.h4("Save to Calendar Link"),
                        html.input({
                            "type": "text",
                            "placeholder": "Paste your calendar link or ID, or generate new...",
                            "value": calendar_url,
                            "onInput": handle_paste_link,
                            "className": "calendar-link-input"
                        }),
                        html.button({"onClick": handle_generate_link, "className": "btn btn-secondary"}, "Generate New Link"),
                        html.button({"onClick": handle_save_schedule, "className": "btn btn-gradient"}, "Save Schedule"),
                        link_error and html.div({"className": "error-message"}, link_error),
                        calendar_url and html.div({},
                            html.p({}, "Add this link to Google Calendar via 'Add other calendars > From URL':"),
                            html.code({}, f"https://testing.mihais-ai-playground.xyz{calendar_url}")
                        ),
                        html.button({"onClick": lambda e: set_show_link_modal(False), "className": "btn btn-secondary", "style": {"marginTop": "1rem"}}, "Close")
                    )
                )
            ) or None
        )
    )