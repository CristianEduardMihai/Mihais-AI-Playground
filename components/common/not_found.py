from reactpy import component, html

@component
def NotFound():
    return html.div(
        {},
        html.div({"className": "background-gradient-blur"}),
        html.link({"rel": "stylesheet", "href": "/static/css/common/not_found.css"}),
        html.div({"className": "notfound-container"},
            html.h1({"className": "notfound-title"}, "404"),
            html.h2({"className": "notfound-subtitle"}, "Page Not Found"),
            html.p({"className": "notfound-message"}, "Sorry, the page you are looking for doesn't exist or has been moved."),
            html.a({"href": "/", "className": "btn-gradient notfound-home-btn"}, "🏠 Go Home")
        )
    )
