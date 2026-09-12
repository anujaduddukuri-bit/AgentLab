"""Shared navigation context for templates."""


def navigation(request):
    return {
        "nav_items": [
            ("dashboard", "Dashboard"),
            ("tools", "Tools"),
            ("playground", "Playground"),
            ("tasks", "Tasks"),
            ("activity", "Activity"),
            ("history", "History"),
            ("settings", "Settings"),
        ]
    }
