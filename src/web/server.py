import hashlib
import hmac
import json
import os
from pathlib import Path
from semver.version import Version

from .globals import globals
from .subsurfacesync import SubsurfaceSync

# if we are running standalone for testing, we don't need or want redis
if __name__ != "__main__":
    from .redis import redis
else:
    globals["testrun"] = True
    path = Path(__file__)
    globals["app_path"] = path.parent.parent.parent.absolute()


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
languages = [
    "en",
    "ca",
    "de_DE",
    "de",
    "el_GR",
    "el",
    "es_ES",
    "es",
    "fi_FI",
    "fi",
    "fr_FR",
    "fr",
    "hr_HR",
    "hr",
    "hu_HU",
    "hu",
    "it_IT",
    "it",
    "ko_KR",
    "ko",
    "nl_NL",
    "nl",
    "pt_BR",
    "pt_PT",
    "pt",
    "sv_SE",
    "sv",
]
load_dotenv()


def get_locale():
    # try to guess the language from the user accept header the browser transmits.
    if request.args.get("lang"):
        session["lang"] = request.args.get("lang")
    if session.get("lang"):
        return session.get("lang")
    return request.accept_languages.best_match(languages)


app = Flask(__name__)
app.secret_key = os.urandom(16).hex()
babel = Babel(app, locale_selector=get_locale)
globals["subsurfacesync"] = SubsurfaceSync()
if __name__ != "__main__":
    # if this runs under gunicorn as a production server,
    # we want only one of the workers to process any outstanding release IDs
    # try to create the lock in Redis and hold it for 30 seconds
    # (by which time all the other workers have gotten past this code)
    redis.set(name="initWorker", value=os.getpid(), nx=True, ex=30)
    lock = int(redis.get(name="initWorker"))
    print(f"process {os.getpid()} got lock {lock}")
    if lock == os.getpid():
        print("this is the initWorker")
        print("make sure Subsurface tree is checked out and current")
        globals["subsurfacesync"].setup()
        globals["subsurfacesync"].sync()
        print("processing any remembered release IDs")
        for release_id in env["release_ids"].value:
            # we got restarted while waiting for releases to populate - remove their locks
            redis.delete(f"processing_{release_id}")
            # we don't know how long we've been waiting, so give it a minute and then check
            AssetDownloader(release_id, 60)
    else:
        print(f"worker {lock} is dealing with release IDs")
else:
    globals["subsurfacesync"].setup()
    globals["subsurfacesync"].sync()


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
        if key == "lang":
            return f"/{get_locale()}"
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


@app.route("/subsurface-user-manual/images/<path:path>")
def user_manual_images(path):
    return send_from_directory(os.path.join(app.root_path, "static/images"), path)


@app.route("/subsurface-mobile-v3-user-manual/mobile-images/<path:path>")
@app.route("/subsurface-mobile-user-manual/mobile-images/<path:path>")
def mobile_user_manual_images(path):
    return send_from_directory(
        os.path.join(app.root_path, "static/mobile-images"), path
    )


@app.route("/subsurface-user-manual/")
def static_user_manual():
    return send_from_directory(
        os.path.join(app.root_path, "static"), "user-manual.html"
    )


@app.route("/subsurface-mobile-v3-user-manual/")
@app.route("/subsurface-mobile-user-manual/")
def static_mobile_user_manual():
    return send_from_directory(
        os.path.join(app.root_path, "static"), "mobile-user-manual.html"
    )


@app.route("/release-changes/")
def release_changes():
    return render_template("release-changes.html", request=request)


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


@app.get("/contribute/")
def contribute():
    return render_template("contribute.html", request=request)


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


@app.get("/credits/")
def credits():
    return render_template("credits.html", request=request)


@app.get("/sponsoring/")
def sponsoring():
    return render_template("sponsoring.html", request=request)


@app.get("/documentation/")
def documentation():
    return render_template("documentation.html", request=request)


@app.get("/supported-dive-computers/")
def supported_dive_computers():
    return render_template("supported-dive-computers.html", request=request)


@app.get("/tutorial-video/")
def tutorial_video():
    return render_template("tutorial-video.html", request=request)


@app.get("/data-deletion/")
def data_deletion():
    return render_template("data-deletion.html", request=request)


@app.get("/updatecheck.html")
@app.get("/updatecheck.html/")
def updatecheck():
    # semver makes this easy - but for the build-extra text to be handled correctly, it needs to be separated with a '+'
    uv = request.args.get("version")
    if uv:
        uv = uv.replace("-", "+", 1)
    if not Version.is_valid(uv):
        print(f"{uv} is not a semVer - let's try something else")
        # so this could be an old 4 part version number like 5.0.10.0
        last_dot = uv.rfind(".")
        if last_dot > 4:
            uv = uv[:last_dot] + "+" + uv[last_dot + 1 :]
            print(f"rewrote version as {uv}")
        else:
            print(f"cannot parse version {uv} - last_dot was {last_dot}")
            return f"System error: cannot parse version {uv}"
    user_version = Version.parse(uv)

    # and before we do anything else, parse the current version as well (with the same modification)
    cv = env.get("crelease").value.replace("-", "+", 1)
    if not Version.is_valid(cv):
        print(f"cannot parse internal current version {cv}")
        return "System error: cannot retrieve current version"
    current_version = Version.parse(cv)

    os = request.args.get("os")
    user_agent = request.headers.get("User-Agent")
    print(f"got a request for {os}, {user_version}, {user_agent}")

    analysis = version_check(current_version, user_version)
    ret = analysis.get("ret")
    print(f"returning: {ret}")
    return ret


@app.get("/updatecheck2/")
def updatecheck2():
    # new version with json data being returned to the client - requires newer Subsurface version that can parse this
    # this will be expanded to provide specific download links in the future.
    # semver makes this easy - but for the build-extra text to be handled correctly, it needs to be separated with a '+'
    uv = request.args.get("version").replace("-", "+", 1)
    if not Version.is_valid(uv):
        print(f"cannot parse version {uv}")
        return {"err": f"System error: cannot parse version {uv}"}, 400
    user_version = Version.parse(uv)

    # and before we do anything else, parse the current version as well (with the same modification)
    cv = env.get("crelease").value.replace("-", "+", 1)
    if not Version.is_valid(cv):
        print(f"cannot parse internal current version {cv}")
        return {"err": "System error: cannot retrieve current version"}, 500
    current_version = Version.parse(cv)

    os = request.args.get("os")
    user_agent = request.headers.get("User-Agent")
    print(f"got a request for {os}, {user_version}, {user_agent}")

    ret = version_check(current_version, user_version)
    print(f"returning: {ret}")
    return ret


def version_check(current_version: Version, user_version: Version):
    ret = "Server error"
    link = ""
    if current_version < user_version:
        ret = "You are running a build that is newer than the current release."
    elif current_version == user_version:
        if user_version.build == "CICD-release":
            ret = "OK"
        else:
            ret = "You are running a local build that is based on the current release"
    elif current_version > user_version:
        link = "https://subsurface-divelog.org/current-release/"
        if user_version.build == "CICD-release" or user_version.build == "0":
            ret = f"There is a newer release {current_version} available at {link}"
        else:
            ret = f"You appear to be running a local build that is based on an older release. Please upgrade to {current_version} at {link}"
    else:
        print(f"semver comparison is broken for {current_version} and {user_version}")
    return {"ret": ret, "link": link}


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
