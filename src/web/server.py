import json
import os
import pathlib
import sys

from setuptools import Require

from .assetdownloader import AssetDownloader
from .env import Env
from .globals import globals

from flask_babel import Babel
from flask import Flask, g, redirect, render_template, request, send_from_directory


description = """
Simple backend to run the Subsurface website
"""


def get_locale():
    # try to guess the language from the user accept header the browser transmits.
    # At the moment we support en/de/fr/nl/it/es/pt_pt.
    return request.accept_languages.best_match(
        ["en", "de_DE", "fr_fr", "nl_nl", "it_it", "es_es", "pt_pt"]
    )


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


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static/images"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.get("/")
def home():
    print("called the / route")
    return render_template("home.html", request=request)


@app.get("/latest-release")
def lrelease():
    return render_template("latest-release.html", request=request)


@app.get("/current-release")
def crelease():
    return render_template("current-release.html", request=request)


@app.get("/user-forum")
def user_forum():
    return render_template("user-forum.html", request=request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8002", debug=True)
