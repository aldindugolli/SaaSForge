from flask import render_template, request


def handle_400(e):
    if request.headers.get("HX-Request"):
        return render_template("components/error_toast.html", message=str(e) or "Bad request"), 400
    return render_template("errors/400.html", error=e), 400


def handle_403(e):
    if request.headers.get("HX-Request"):
        return render_template("components/error_toast.html", message="You don't have permission to do that."), 403
    return render_template("errors/403.html", error=e), 403


def handle_404(e):
    if request.headers.get("HX-Request"):
        return render_template("components/error_toast.html", message="Page not found."), 404
    return render_template("errors/404.html", error=e), 404


def handle_429(e):
    if request.headers.get("HX-Request"):
        return render_template("components/error_toast.html", message="Too many requests. Please slow down."), 429
    return render_template("errors/429.html", error=e), 429


def handle_500(e):
    if request.headers.get("HX-Request"):
        return render_template("components/error_toast.html", message="Internal server error. Our team has been notified."), 500
    return render_template("errors/500.html", error=e), 500
