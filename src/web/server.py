import json
import os
import pathlib

from setuptools import Require

from .assetdownloader import AssetDownloader

from flask_babel import Babel
from flask import Flask, g, redirect, render_template, request, send_from_directory


def get_locale():
    # try to guess the language from the user accept header the browser transmits.
    # At the moment we support en/de/fr/nl/it/es/pt_pt.
    return request.accept_languages.best_match(
        ["en", "de", "fr", "nl", "it", "es", "pt_pt"]
    )


app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
babel = Babel(app, locale_selector=get_locale)

description = """
Simple backend to run the Subsurface website
"""


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


if __name__ == "__main__":
    print("Run with:")
    print("uvicorn app:app --host 0.0.0.0 --port 8790")
    print("or for development:")
    print("uvicorn app:app --host 0.0.0.0 --port 8790 --reload")
