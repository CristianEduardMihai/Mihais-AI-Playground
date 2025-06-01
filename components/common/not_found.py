from reactpy import component, html

@component
def NotFound():
    from components.common.config import CACHE_SUFFIX
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": f"/static/css/common/not_found.css?v={CACHE_SUFFIX}"}),
        html.div({"className": "notfound-container"},
            html.h1({"className": "notfound-title"}, "404"),
            html.h2({"className": "notfound-subtitle"}, "Page Not Found"),
            html.p({"className": "notfound-message"}, "Sorry, the page you are looking for doesn't exist or has been moved."),
            html.a({"href": "/", "className": "btn-gradient notfound-home-btn"}, "🏠 Go Home")
        )
    )
