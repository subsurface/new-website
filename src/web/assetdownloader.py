import datetime
import os
import re
import requests
import sys
from github import Auth, Github
from threading import Timer

from .env import env
from .globals import globals

if not globals["testrun"]:
    from .redis import redis


class Background:
    def __init__(self, delay, function):
        self._timer = None
        self._delay = delay
        self._function = function
        self._running = False
        self.schedule()

    def schedule(self):
        if not self._running:
            self._running = True
            self._timer = Timer(self._delay, self._run)
            self._timer.start()

    def _run(self):
        # immediately schedule the next instance
        self._running = False
        # we don't want these to be recurring: self.schedule()
        self._function()

    def cancel(self):
        self._timer.cancel()
        self._running = False


class AssetDownloader:
    def __init__(self, release_id, delay):
        lock_name = f"processing_{release_id}"
        if redis.set(lock_name, "1", nx=True):
            self._release_id = release_id
            self._bg = Background(delay, self._downloadAssets)
            print(
                f"setting up to update the assets for release id {release_id} in {delay/60} minutes"
            )

    def _downloadAssets(self):
        updateReleaseWebsite(self._release_id)


def get_pr_title(bn: int):
    r = requests.get(
        f"https://github.com/subsurface/nightly-builds/releases/download/v6.0.{bn}-CICD-release/release_content_title.txt"
    )
    if r.status_code == 200:
        print(f"finished build number {bn}, got PR title {r.content.decode()}")
        return r.content.decode()
    print(f"no PR title for build number {bn}")
    return ""


def updateReleaseWebsite(release_id):
    auth = Auth.Token(os.environ.get("github_token").strip())
    gh = Github(auth=auth)
    repo = gh.get_repo("subsurface/nightly-builds")
    for r in repo.get_releases():
        if r.id != release_id:
            continue
        macosurl = ""
        windowsurl = ""
        appimageurl = ""
        appimagename = ""
        version = ""
        apkname = ""
        apkurl = ""
        missing = ""
        for a in r.get_assets():
            url = a.browser_download_url
            print(f"{url}")
            match = re.search("Subsurface-mobile-6.*-CICD-release.apk", url)
            if match:
                apkurl = url
                apkname = match.group(0)
            else:
                missing += " Android APK,"
            if re.search("subsurface-6.*-CICD-release-installer.exe", url):
                windowsurl = url
            else:
                missing += " Windows Installer,"
            if re.search("Subsurface-6.*-CICD-release.dmg", url):
                macosurl = url
            else:
                missing += " macOS DMG,"
            match = re.search(r"Subsurface-v(6.*)-CICD-release.AppImage", url)
            if match:
                appimageurl = url
                appimagename = match.group(0)
                version = match.group(1)
            else:
                missing += " Linux AppImage,"
        if missing != "":
            # only update the website once the releases is complete
            # the three step update for release_ids is needed since we copy values in the Env class
            print("found all binaries, updating the website")
            release_ids = env["release_ids"].value
            if release_id in release_ids:
                release_ids.remove(release_id)
                env["release_ids"].value = release_ids
                env["lrelease_date"].value = datetime.datetime.today().strftime(
                    "%Y-%m-%d"
                )
                env["lrelease"].value = version
                # finally assemble the last 5 PR titles
                current = version.split(".")
                pr_titles = ""
                if len(current) == 3:
                    buildnr = int(current[2])
                    for bn in range(buildnr, buildnr - 5, -1):
                        pr_title = get_pr_title(bn)
                        if pr_title:
                            pr_titles += "<li>" + pr_title + "</li>"
                env["pr_summary"].value = pr_titles
        else:
            print(f"Still missing {missing[:-1]} - scheduling myself to check again")
            a = AssetDownloader(release_id, 150)


if __name__ == "__main__":
    # ok, doing it manually
    if len(sys.argv) != 2:
        print("call with the release id as argument")
        sys.exit()
    release_id = int(sys.argv[1])
    print(f"updating website for release with release_id {release_id}")
    updateReleaseWebsite(release_id=release_id)
