from reactpy import component, html

@component
def Navbar():
    return html.nav(
        html.a({"href": "/"}, "Home"),
        html.a({"href": "/health"}, "Health"),
        html.a({"href": "/fun"}, "Fun"),
    )