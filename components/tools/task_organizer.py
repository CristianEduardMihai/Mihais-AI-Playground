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
from datetime import timedelta

DEBUG_MODE = True  # Set to True to enable verbose debug output

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
    loading, set_loading = use_state(False)
    error, set_error = use_state("")
    show_link_modal, set_show_link_modal = use_state(False)
    calendar_url, set_calendar_url = use_state("")
    user_id, set_user_id = use_state("")
    link_error, set_link_error = use_state("")

    # Day selector state
    today = datetime.date.today()
    days = [(today + timedelta(days=i)) for i in range(15)]
    day_options = [d.strftime('%Y-%m-%d (%a)') for d in days]
    selected_day, set_selected_day = use_state(day_options[0])

    # Save/Load box state
    link_mode, set_link_mode = use_state('existing')  # 'existing' or 'new'
    link_input, set_link_input = use_state("")

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
            except Exception as e:
                set_error(f"AI scheduling error: {e}")
                set_organized_tasks([])
                debug_print("Error in ai_schedule:", e)
            set_loading(False)
            debug_print("ai_schedule thread finished")
        threading.Thread(target=ai_schedule, daemon=True).start()

    def handle_save_to_link(_):
        debug_print("handle_save_to_link called")
        set_show_link_modal(True)
        set_link_error("")
        # Only auto-generate a new link if 'Create New Link' is selected and no user_id
        if link_mode == 'new' and not user_id:
            new_id = generate_random_id()
            set_user_id(new_id)
            set_calendar_url(f"/calendars/{new_id}")
            debug_print("Auto-generated calendar link in modal:", f"/calendars/{new_id}")
            # Immediately save the current schedule to the new link if there are tasks
            if organized_tasks and len(organized_tasks) > 0:
                ics = generate_ics(organized_tasks)
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
        # Save the current schedule as a new or existing calendar
        ics = generate_ics(organized_tasks)
        calendar_db.save_calendar(user_id, ics)
        set_calendar_url(f"/calendars/{user_id}")
        set_link_error("")
        debug_print(f"Calendar saved for user_id {user_id}")

    def handle_day_change(e):
        set_selected_day(e['target']['value'])
        # On day change, if link is selected, load tasks for that day
        if user_id:
            ics = calendar_db.get_calendar(user_id)
            if ics:
                # Parse tasks for the selected day (simple: all events for that day)
                import re
                day_str = selected_day[:10].replace('-', '')
                vevents = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics, re.DOTALL)
                tasks_for_day = []
                for block in vevents:
                    dtstart = re.search(r'DTSTART:(\d{8})T(\d{4})Z', block)
                    summary = re.search(r'SUMMARY:([^\n]+)', block)
                    duration = re.search(r'DTEND:(\d{8})T(\d{4})Z', block)
                    if dtstart and dtstart.group(1) == day_str:
                        tasks_for_day.append({
                            'name': summary.group(1) if summary else '',
                            'prep_time': '',
                            'ai_estimate': False,
                            'est_start': dtstart.group(2)[:2] + ':' + dtstart.group(2)[2:],
                            'est_duration': ''
                        })
                set_tasks(tasks_for_day if tasks_for_day else [{"name": "", "prep_time": "", "ai_estimate": False, "est_start": "", "est_duration": ""}])

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
            # Always load tasks for selected day as soon as link is entered
            ics = calendar_db.get_calendar(uid)
            if ics:
                import re
                day_str = selected_day[:10].replace('-', '')
                vevents = re.findall(r'BEGIN:VEVENT(.*?)END:VEVENT', ics, re.DOTALL)
                tasks_for_day = []
                for block in vevents:
                    dtstart = re.search(r'DTSTART:(\d{8})T(\d{4})Z', block)
                    summary = re.search(r'SUMMARY:([^\n]+)', block)
                    if dtstart and dtstart.group(1) == day_str:
                        # Only treat as a task if it's not a rest/prep block
                        summary_val = summary.group(1) if summary else ''
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
            # Do nothing on input for new link mode
            pass

    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": "/static/css/tools/task_organizer.css"}),
        html.nav({"className": "navbar"}, html.a({"href": "/", "className": "btn btn-gradient"}, "🏠 Home")),
        html.div({"className": "task-organizer"},
            html.div({"className": "day-selector"},
                html.select({"value": selected_day, "onChange": handle_day_change, "className": "day-selector"},
                    *[html.option({"value": d}, d) for d in day_options]
                )
            ),
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
                        html.div({"className": "save-load-box"},
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
                            (calendar_url and html.div({},
                                html.p({}, "Add this link to Google Calendar via 'Add other calendars > From URL':"),
                                html.code({}, f"https://mihais-ai-playground.xyz{calendar_url}")
                            ) or None)
                        ),
                        html.button({"onClick": handle_save_schedule, "className": "btn btn-gradient"}, "Save Schedule"),
                        link_error and html.div({"className": "error-message"}, link_error),
                        html.button({"onClick": lambda e: set_show_link_modal(False), "className": "btn btn-secondary", "style": {"marginTop": "1rem"}}, "Close")
                    )
                ) or None
            ) or None
        )
    )