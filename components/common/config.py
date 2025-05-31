disable_css_cache = True  # Set to False to allow browser to cache CSS (GITHUB_ACTIONS_RUN = 'STABLE')
GITHUB_ACTIONS_RUN = None

def set_github_actions_run(run_number=None):
    global GITHUB_ACTIONS_RUN
    if not disable_css_cache:
        GITHUB_ACTIONS_RUN = "STABLE"
    else:
        GITHUB_ACTIONS_RUN = run_number