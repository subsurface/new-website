import hashlib
import hmac
import json
import os

from .globals import testrun

if __name__ != "__main__":
    from .redis import redis
else:
    testrun = True


from .assetdownloader import AssetDownloader
from .env import Env, env

from dotenv import load_dotenv
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
load_dotenv()


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

if __name__ != "__main__":
    # if this runs under gunicorn as a production server,
    # we want only one of the workers to process any outstanding release IDs
    # try to create the lock in Redis and hold it for 30 seconds
    # (by which time all the other workers have gotten past this code)
    redis.set(name="processReleaseIds", value=os.getpid(), nx=True, ex=30)
    lock = int(redis.get(name="processReleaseIds"))
    print(f"process {os.getpid()} got lock {lock}")
    if lock == os.getpid():
        print("processing any remembered release IDs")
        for release_id in env["release_ids"].value:
            # we got restarted while waiting for releases to populate - remove their locks
            redis.delete(f"processing_{release_id}")
            # we don't know how long we've been waiting, so give it a minute and then check
            AssetDownloader(release_id, 60)
    else:
        print(f"worker {lock} is dealing with release IDs")


@app.context_processor
def utility_processor():
    def get_env(key):
        if key in env.keys():
            return env[key].value
        if key == "lwindows":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease'].value}-CICD-release/subsurface-{env['lrelease'].value}-CICD-release-installer.exe"
        if key == "lmacos":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease'].value}-CICD-release/Subsurface-{env['lrelease'].value}-CICD-release.dmg"
        if key == "landroid":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease'].value}-CICD-release/Subsurface-mobile-{env['lrelease'].value}-CICD-release.apk"
        if key == "lappimage":
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease'].value}-CICD-release/Subsurface-v{env['lrelease'].value}-CICD-release.AppImage"
        if key == "cwindows":
            return f"https://subsurface-divelog.org/downloads/subsurface-{env['crelease'].value}-CICD-release-installer.exe"
        if key == "cmacos":
            return f"https://subsurface-divelog.org/downloads/Subsurface-{env['crelease'].value}-CICD-release.dmg"
        if key == "candroid":
            return f"https://subsurface-divelog.org/downloads/Subsurface-mobile-{env['crelease'].value}-CICD-release.apk"
        if key == "cappimage":
            return f"https://subsurface-divelog.org/downloads/Subsurface-v{env['crelease'].value}-CICD-release.AppImage"
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
app.add_url_rule(f"/documentation/<path:urlpath>", view_func=redirector)


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static/images"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@app.route("/images/<path:path>")
def send_report(path):
    return send_from_directory(os.path.join(app.root_path, "images"), path)


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


@app.get("/thanks/")
def thanks():
    return render_template("thanks.html", request=request)


@app.get("/sponsoring/")
def sponsoring():
    return render_template("sponsoring.html", request=request)


@app.get("/documentation/")
def documentation():
    return render_template("documentation.html", request=request)


@app.get("/supported-dive-computers/")
def supported_dive_computers():
    return render_template("supported-dive-computers.html", request=request)


@app.get("/subsurface-user-manual/")
def subsurface_user_manual():
    return render_template("subsurface-user-manual.html", request=request)


#
# GitHub webhook that drives our latest release updates
def verifySignature():
    secret = os.environ.get("webhook_secret").strip()
    signature = (
        "sha256="
        + hmac.new(
            bytes(secret, "utf-8"),
            msg=request.data,
            digestmod=hashlib.sha256,
        )
        .hexdigest()
        .lower()
    )
    print(f"request.data {request.data}")
    print(f"comparing {signature} and {request.headers.get('X-Hub-Signature-256')}")
    return hmac.compare_digest(signature, request.headers.get("X-Hub-Signature-256"))


@app.route("/subsurface-release-webhook", methods=["POST"])
def webhook():
    print("webhook")
    if not verifySignature():
        response = app.response_class(
            response=json.dumps({"success": False}),
            status=403,
            mimetype="application/json",
        )
        return response
    release_ids = env["release_ids"].value
    body = request.data
    with open("/var/log/webhook-requests.log", "a") as logfile:
        print(body, file=logfile)
    data = json.loads(body)
    action = data.get("action")
    release = data.get("release")
    if release:
        release_id = release.get("id")
        assets_url = release.get("assets_url")
        repository = release.get("repository")
        name = repository.get("name") if repository else "unknown"
        print(
            f"Relase: {release.get('name')} id {release_id} from repo {name} with action {action}"
        )
        print(f"With assets URL {assets_url}")
        if release_id not in release_ids:
            release_ids.append(release_id)
            env["release_ids"].value = release_ids
            a = AssetDownloader(release_id, 900)

    # in any case, report success
    response = app.response_class(
        response=json.dumps({"success": True}), status=200, mimetype="application/json"
    )
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8002", debug=True)
