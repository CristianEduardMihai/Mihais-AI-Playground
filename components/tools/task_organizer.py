from reactpy import component, html, use_state
import urllib.parse
import datetime
import threading, time
import re
import requests
import json

# --- AI logic for scheduling tasks efficiently ---
def call_ai_schedule(tasks):
    print("---- USER INPUT ----")
    print(json.dumps(tasks, indent=2, ensure_ascii=False))
    print("---- END USER INPUT ----")
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
        ai_raw = resp.json()["choices"][0]["message"]["content"]
        ai_clean = ai_raw.strip()
        if ai_clean.startswith("```"):
            ai_clean = ai_clean.lstrip("`\n ")
        if ai_clean.endswith("```"):
            ai_clean = ai_clean.rstrip("`\n ")
        if ai_clean.startswith("json"):
            ai_clean = ai_clean[4:].lstrip("\n ")
        print("---- AI OUTPUT ----")
        print(ai_clean)
        print("---- END AI OUTPUT ----")
        scheduled = json.loads(ai_clean)
        return scheduled
    except Exception as e:
        print(f"[TaskOrganizer] AI scheduling error: {e}")
        # Error will be set in the component's thread, just return empty
        return []

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
        set_loading(True)
        set_error("")
        def ai_schedule():
            time.sleep(0.7)
            print("[TaskOrganizer] User tasks:", tasks)
            try:
                scheduled = call_ai_schedule(tasks)
                set_organized_tasks(scheduled)
                # Generate Google Calendar link for the scheduled block (use first and last block)
                if scheduled:
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
                else:
                    set_calendar_link("")
            except Exception as e:
                set_error(f"AI scheduling error: {e}")
                set_organized_tasks([])
                set_calendar_link("")
            set_loading(False)
        threading.Thread(target=ai_schedule, daemon=True).start()

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
                calendar_link and html.a({
                    "href": calendar_link,
                    "target": "_blank",
                    "className": "btn btn-navy download-btn"
                }, "Add to Google Calendar") or None
            ) or None
        )
    )