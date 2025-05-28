from reactpy import component, html, use_state
import components.common.user_db as user_db
try:
    from reactpy.backend import use_cookie
except ImportError:
    def use_cookie(*args, **kwargs):
        return (None, lambda *a, **k: None)

@component
def LoginPortal(on_login=None, on_signup=None):
    mode, set_mode = use_state('login')  # 'login' or 'signup'
    email, set_email = use_state("")
    password, set_password = use_state("")
    error, set_error = use_state("")
    user_cookie, set_user_cookie = use_cookie('user_id', None)
    
    def handle_submit(_):
        set_error("")
        if not email or not password:
            set_error("Email and password required.")
            return
        if mode == 'signup':
            user_id = user_db.create_user(email, password)
            if user_id:
                set_user_cookie(user_id, max_age=60*60*24*365)  # 1 year
                if on_login:
                    on_login(user_id)
            else:
                set_error("Email already registered.")
        else:
            user_id = user_db.verify_user(email, password)
            if user_id:
                set_user_cookie(user_id, max_age=60*60*24*365)
                if on_login:
                    on_login(user_id)
            else:
                set_error("Invalid email or password.")
    
    return html.div(
        {},
        html.link({"rel": "stylesheet", "href": "/static/css/common/login_portal.css"}),
        html.div(
            {"className": "login-portal"},
            html.h2("Sign In" if mode == 'login' else "Sign Up"),
            error and html.div({"className": "error-message"}, error),
            html.input({
                "type": "email", "placeholder": "Email", "value": email,
                "onInput": lambda e: set_email(e['target']['value']),
                "className": "login-input"
            }),
            html.input({
                "type": "password", "placeholder": "Password", "value": password,
                "onInput": lambda e: set_password(e['target']['value']),
                "className": "login-input"
            }),
            html.button({"className": "btn-gradient", "onClick": handle_submit},
                "Sign In" if mode == 'login' else "Sign Up"
            ),
            html.div({"className": "login-switch"},
                html.span(
                    "Don't have an account? " if mode == 'login' else "Already have an account? ",
                    html.a({"href": "#", "onClick": lambda e: set_mode('signup' if mode == 'login' else 'login')},
                        "Sign up" if mode == 'login' else "Sign in"
                    )
                )
            )
        )
    )
