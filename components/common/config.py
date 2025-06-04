# Cache mode: 'STABLE', 'ACTIONS', or 'DEV'
# DEV mode is for development purposes and will not use cache. The suffix will be the current timestamp.
CACHE_MODE = 'ACTIONS'  # Change to 'STABLE', 'ACTIONS', or 'DEV' as needed
DEBUG_MODE = False  # Set to True to enable global debug mode
REACTPY_DEBUG_MODE = False  # Set to True to enable ReactPy debug mode

CACHE_SUFFIX = None
def set_CACHE_SUFFIX(run_number=None):
    global CACHE_SUFFIX
    if CACHE_MODE == 'STABLE':
        CACHE_SUFFIX = 'STABLE'
    elif CACHE_MODE == 'ACTIONS':
        CACHE_SUFFIX = run_number
    elif CACHE_MODE == 'DEV':
        import time
        CACHE_SUFFIX = str(int(time.time()))
    else:
        CACHE_SUFFIX = run_number


# Untrack config file for testing purposes
# git rm --cached components/common/config.py