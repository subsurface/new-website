import re
import sys
from github import Auth, Github
from threading import Timer


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
        self._release_id = release_id
        self._bg = Background(delay, self._downloadAssets)
        print(
            f"setting up to update the assets for release id {release_id} in {delay/60} minutes"
        )

    def _downloadAssets(self):
        updateReleaseWebsite(self._release_id)


def updateReleaseWebsite(release_id):
    with open("/app/.token", "r") as token_file:
        token = token_file.read().strip()
    auth = Auth.Token(token)
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
        for a in r.get_assets():
            url = a.browser_download_url
            print(f"{url}")
            match = re.search("Subsurface-mobile-6.*-CICD-release.apk", url)
            if match:
                apkurl = url
                apkname = match.group(0)
            if re.search("subsurface-6.*-CICD-release-installer.exe", url):
                windowsurl = url
            if re.search("Subsurface-6.*-CICD-release.dmg", url):
                macosurl = url
            match = re.search(r"Subsurface-(v6.*)-CICD-release.AppImage", url)
            if match:
                appimageurl = url
                appimagename = match.group(0)
                version = match.group(1)
        print(
            f"so far I found apkurl {apkurl} windowsurl {windowsurl} macosurl {macosurl} appimagename {appimagename} appimageurl {appimageurl} version {version}"
        )
        if all([apkurl, windowsurl, macosurl, appimagename, appimageurl, version]):
            # only use complete releases
            replacements = [
                ["ANDROIDAPKLINK", apkurl],
                ["ANDROIDAPKFILE", apkname],
                ["WINDOWSINSTALLER", windowsurl],
                ["MACDMG", macosurl],
                ["APPIMAGELINK", appimageurl],
                ["APPIMAGEBINARY", appimagename],
                ["VERSION", version],
            ]
            with open("/www/latest-release/index-template.html") as template, open(
                "/www/latest-release/index.html", "w"
            ) as html:
                text = template.read()
                for [old, new] in replacements:
                    text = text.replace(old, new)
                html.write(text)
        else:
            a = AssetDownloader(release_id, 150)


if __name__ == "__main__":
    # ok, doing it manually
    if len(sys.argv) != 2:
        print("call with the release id as argument")
        sys.exit()
    release_id = int(sys.argv[1])
    print(f"updating website for release with release_id {release_id}")
    updateReleaseWebsite(release_id=release_id)
