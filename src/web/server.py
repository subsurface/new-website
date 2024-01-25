import json
import os
import pathlib
import sys

from setuptools import Require

from .assetdownloader import AssetDownloader
from .env import Env
from .globals import globals

from flask_babel import Babel, get_translations, get_locale as gl
from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
)


description = """
Simple backend to run the Subsurface website
"""


languages = ["en", "de_DE", "fr_FR", "nl_NL", "it_IT", "es_ES", "pt_PT"]


def get_locale():
    # try to guess the language from the user accept header the browser transmits.
    # At the moment we support en/de/fr/nl/it/es/pt_pt.
    if request.args.get("lang"):
        session["lang"] = request.args.get("lang")
    if session.get("lang"):
        return session.get("lang")
    return request.accept_languages.best_match(languages)


app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
babel = Babel(app, locale_selector=get_locale)
env = {
    "lrelease": Env("lrelease", default="6.0.5067"),
    "lrelease_date": Env("lrelase_date", default="2024-01-21"),
    "crelease": Env("crelease", default="6.0.5054"),
    "crelease_date": Env("crelease_date", default="2024-01-13"),
}


@app.context_processor
def utility_processor():
    def get_env(key):
        if key in env.keys():
            return env[key].value
        if key == "lwindows":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease']}-CICD-release/subsurface-{env['lrelease']}-CICD-release-installer.exe"
        if key == "lmacos":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease']}-CICD-release/Subsurface-{env['lrelease']}-CICD-release.dmg"
        if key == "landroid":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease']}-CICD-release/Subsurface-mobile-{env['lrelease']}-CICD-release.apk"
        if key == "lappimage":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease']}-CICD-release/Subsurface-v{env['lrelease']}-CICD-release.AppImage"
        if key == "cwindows":
            return f"https://subsurface-divelog.org/download/subsurface-{env['crelease']}-CICD-release-installer.exe"
        if key == "cmacos":
            return f"https://subsurface-divelog.org/downloads/Subsurface-{env['crelease']}-CICD-release.dmg"
        if key == "candroid":
            return f"https://subsurface-divelog.org/downloads/Subsurface-mobile-{env['crelease']}-CICD-release.apk"
        if key == "cappimage":
            return f"https://subsurface-divelog.org/downloads/Subsurface-v{env['crelease']}-CICD-release.AppImage"
        return ""

    return dict(get_env=get_env)


# helper function to consistently redirect multi-level paths to the new flat url scheme
def redirector(urlpath=""):
    print(
        f"universal redirector for request {request.full_path} with urlpath {urlpath}"
    )
    first = request.path.split("/")[1]
    if first == "misc" or first == "documentation":
        print(f"converting to {request.full_path.replace(f'/{first}', '')}")
        return redirect(f"{request.full_path.replace(f'/{first}', '')}")
    return redirect(f"/{urlpath}?lang={first}")


# next set up the various language routes as well as the misc and documentation routes
for l in languages:
    app.add_url_rule(f"/{l}/", view_func=redirector)
    app.add_url_rule(f"/{l}/<path:urlpath>", view_func=redirector)
    if len(l) > 2 and l[2] == "_":
        app.add_url_rule(f"/{l[:2]}/", view_func=redirector)
        app.add_url_rule(f"/{l[:2]}/<path:urlpath>", view_func=redirector)
app.add_url_rule(f"/misc/<path:urlpath>", view_func=redirector)
app.add_url_rule(f"/docuementation/<path:urlpath>", view_func=redirector)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static/images"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.get("/")
def home():
    return render_template("home.html", request=request)


@app.get("/latest-release/")
def latest_release():
    return render_template("latest-release.html", request=request)


@app.get("/current-release/")
def current_release():
    return render_template("current-release.html", request=request)


@app.get("/user-forum/")
def user_forum():
    return render_template("user-forum.html", request=request)


@app.get("/contributing/")
def contributing():
    return render_template("contributing.html", request=request)


@app.get("/bugtracker/")
def bugtracker():
    return render_template("bugtracker.html", request=request)


@app.get("/privacy-policy/")
def privacy_policy():
    return render_template("privacy-policy.html", request=request)


@app.get("/faq/")
def faq():
    return render_template("faq.html", request=request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8002", debug=True)
