import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from urllib.parse import urlencode
from semver.version import Version

from .globals import globals
from .subsurfacesync import NightlyBuilds, SubsurfaceSync

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
    make_response,
)
from werkzeug.exceptions import Forbidden


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


def resolve_language(lang_code):
    if not lang_code:
        return None
    normalized = lang_code.replace("-", "_")
    parts = normalized.split("_", 1)
    base = parts[0].lower()
    region = parts[1].upper() if len(parts) == 2 else ""
    normalized = f"{base}_{region}" if region else base
    if normalized in languages:
        return normalized
    if base in languages:
        return base
    for candidate in languages:
        if candidate.startswith(f"{base}_"):
            return candidate
    return None


def get_locale():
    lang_from_query = resolve_language(request.args.get("lang"))
    if lang_from_query:
        return lang_from_query

    lang_from_cookie = resolve_language(request.cookies.get("lang"))
    if lang_from_cookie:
        return lang_from_cookie

    lang_from_header = resolve_language(request.accept_languages.best_match(languages))
    if lang_from_header:
        return lang_from_header

    return "en"


app = Flask(__name__)
babel = Babel(app, locale_selector=get_locale)
globals["subsurfacesync"] = SubsurfaceSync()
globals["nightlybuilds"] = NightlyBuilds()
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
            # we don't know how long we've been waiting, so give it a few seconds and then check
            AssetDownloader(release_id, 10)
    else:
        print(f"worker {lock} is dealing with release IDs")
else:
    globals["subsurfacesync"].setup()
    globals["subsurfacesync"].sync()


@app.before_request
def persist_language_and_clean_url():
    if request.method != "GET":
        return None
    lang_from_query = resolve_language(request.args.get("lang"))
    if not lang_from_query:
        return None
    remaining_args = request.args.to_dict(flat=False)
    remaining_args.pop("lang", None)
    target = request.path
    if remaining_args:
        target = f"{target}?{urlencode(remaining_args, doseq=True)}"
    if target != request.full_path.rstrip("?"):
        resp = make_response(redirect(target))
        resp.set_cookie("lang", lang_from_query, max_age=31536000, samesite="Lax", secure=request.is_secure)  # 1 year
        return resp


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
            return f"https://github.com/subsurface/nightly-builds/releases/download/v{env['lrelease'].value}-CICD-release/Subsurface-{env['lrelease'].value}-CICD-release.AppImage"
        if key == "cwindows":
            return f"/downloads/subsurface-{env['crelease'].value}-CICD-release-installer.exe"
        if key == "cmacos":
            return f"/downloads/Subsurface-{env['crelease'].value}-CICD-release.dmg"
        if key == "candroid":
            return (
                f"/downloads/Subsurface-mobile-{env['crelease'].value}-CICD-release.apk"
            )
        if key == "cappimage":
            return f"/downloads/Subsurface-{env['crelease'].value}-CICD-release.AppImage"
        if key == "lang":
            return f"/{get_locale()}"
        return ""

    return dict(get_env=get_env)


# helper function to consistently redirect multi-level paths to the new flat url scheme
def redirector(urlpath=""):
    print(f"universal redirector for request {request.full_path} with urlpath {urlpath}")
    first = request.path.split("/")[1]
    lang_from_path = resolve_language(first)

    if first == "misc" or first == "documentation":
        print(f"converting to {request.full_path.replace(f'/{first}', '')}")
        target = request.full_path.replace(f"/{first}", "")
        if target.endswith("?"):
            target = target[:-1]
        return redirect(target or "/")

    target_path = f"/{urlpath}" if urlpath else "/"
    query_args = request.args.to_dict(flat=False)
    query_args.pop("lang", None)
    if query_args:
        target_path = f"{target_path}?{urlencode(query_args, doseq=True)}"
    resp = make_response(redirect(target_path))
    if lang_from_path:
        resp.set_cookie("lang", lang_from_path, max_age=31536000, samesite="Lax", secure=request.is_secure)  # 1 year
    return resp


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


@app.route("/downloads/<path:filename>")
def downloads(filename):
    downloads_path = os.environ.get("DOWNLOADS_PATH", "/data/www/subsurfacestaticsite/downloads")
    if not os.path.isabs(downloads_path):
        downloads_path = os.path.join(app.root_path, downloads_path)

    # Validate path to prevent directory traversal attacks
    requested_file = os.path.normpath(os.path.join(downloads_path, filename))
    normalized_downloads_path = os.path.normpath(os.path.abspath(downloads_path))
    if not requested_file.startswith(normalized_downloads_path + os.sep):
        raise Forbidden("Access denied")

    # Determine MIME type based on file extension
    mime_type = "application/octet-stream"  # default for binary downloads
    if filename.endswith(".exe"):
        mime_type = "application/vnd.microsoft.portable-executable"
    elif filename.endswith(".dmg"):
        mime_type = "application/x-apple-diskimage"
    elif filename.endswith(".apk"):
        mime_type = "application/vnd.android.package-archive"
    elif filename.endswith(".AppImage"):
        mime_type = "application/x-iso9660-appimage"
    return send_from_directory(downloads_path, filename, mimetype=mime_type)


@app.route("/subsurface-mobile-v3-user-manual/mobile-images/<path:path>")
@app.route("/subsurface-mobile-user-manual/mobile-images/<path:path>")
def mobile_user_manual_images(path):
    return send_from_directory(os.path.join(app.root_path, "static/mobile-images"), path)


def _serve_user_manual(base_filename):
    language = resolve_language(request.args.get("lang"))
    if not language:
        language = resolve_language(request.cookies.get("lang"))
    if not language:
        language = resolve_language(request.accept_languages.best_match(languages))
    static_dir = os.path.join(app.root_path, "static")

    if language and language[:2].isalpha():
        file_name = f"{base_filename}_{language[:2]}.html"
        file_path = os.path.join(static_dir, file_name)
        if os.path.exists(file_path):
            return send_from_directory(static_dir, file_name)

    return send_from_directory(static_dir, f"{base_filename}.html")


@app.route("/subsurface-user-manual/")
def static_user_manual():
    return _serve_user_manual("user-manual")


@app.route("/subsurface-mobile-v3-user-manual/")
@app.route("/subsurface-mobile-user-manual/")
def static_mobile_user_manual():
    return _serve_user_manual("mobile-user-manual")


@app.route("/subsurface-user-manual/images/<path:path>")
def user_manual_images(path):
    return send_from_directory(os.path.join(app.root_path, "static/images"), path)


@app.route("/release-changes/")
def release_changes():
    return render_template("release-changes.html", request=request)


@app.get("/")
def home():
    return render_template("home.html", request=request)


@app.get("/latest-release/")
def latest_release():
    # print(f"request for latest-release with lrelease {env['lrelease'].value}")
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
    print("got a request for thanks")
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
        print(f"Relase: {release.get('name')} id {release_id} from repo {name} with action {action}")
        print(f"With assets URL {assets_url}")
        if release_id not in release_ids:
            release_ids.append(release_id)
            env["release_ids"].value = release_ids
            a = AssetDownloader(release_id, 900)

    # in any case, report success
    response = app.response_class(response=json.dumps({"success": True}), status=200, mimetype="application/json")
    return response


@app.route("/api/build-nr-by-sha/<sha>")
def build_nr_by_sha(sha):
    if not re.match(r"^[a-fA-F0-9]+$", sha):
        return app.response_class(response=json.dumps({"success": False}), status=400, mimetype="application/json")
    bnr = redis.get(f"bnr_{sha}")
    if not bnr:
        bnr = globals["nightlybuilds"].get_buildnr_for_sha(sha)
        redis.set(f"bnr_{sha}", bnr)
    else:
        bnr = bnr.decode("utf-8")
    redis.set(f"sha_{sha}", bnr)
    response = app.response_class(
        response=json.dumps({"build_nr": bnr, "success": True}), status=200, mimetype="application/json"
    )
    return response


@app.route("/api/sha-by-build-nr/<build_nr>")
def sha_by_build_nr(build_nr):
    if not re.match(r"^\d+$", build_nr):
        return app.response_class(response=json.dumps({"success": False}), status=400, mimetype="application/json")

    sha = redis.get(f"sha_{build_nr}")
    if not sha:
        sha = globals["nightlybuilds"].get_sha_for_buildnr(build_nr)
        redis.set(f"sha_{build_nr}", sha)
    else:
        sha = sha.decode("utf-8")
    response = app.response_class(
        response=json.dumps({"sha": sha, "success": True}), status=200, mimetype="application/json"
    )
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8002", debug=True)
