import os
import re
import shutil
import subprocess
from .globals import globals


class NightlyBuilds:
    def __init__(self) -> None:
        self._myroot = globals["app_path"]

    def sync(self):
        try:
            subprocess.run(f"cd {self._myroot}/subsurface/nightly-builds; git pull", shell=True, check=True)
        except subprocess.CalledProcessError:
            print("issue pulling the latest nightly builds repo - please check")

    def get_buildnr_for_sha(self, sha):
        self.sync()
        try:
            result = subprocess.run(
                f"cd {self._myroot}/subsurface/nightly-builds; git diff origin/branch-for-{sha} latest-subsurface-buildnumber",
                shell=True,
                stdout=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError:
            # that sha doesn't exist
            return "unknown"
        output = result.stdout.decode("utf-8").strip()
        bnr = open(f"{self._myroot}/subsurface/nightly-builds/latest-subsurface-buildnumber", "r").read().strip()
        if output:
            m = re.match(r"^-(\d+)", output)
            if m:
                bnr = m.group(1).strip()
        return bnr

    def get_sha_for_buildnr(self, bnr):
        self.sync()
        try:
            result = subprocess.run(
                f"cd {self._myroot}/subsurface; bash ./scripts/get-changeset-id.sh {bnr}",
                shell=True,
                stdout=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError:
            # that buildnr doesn't exist
            return "unknown"
        output = result.stdout.decode("utf-8").strip()
        if output:
            return output
        return "unknown"


class SubsurfaceSync:
    def __init__(self) -> None:
        self._myroot = globals["app_path"]

    def setup(self):
        if not os.path.isdir(f"{self._myroot}/subsurface"):
            # ok - this is a brand new setup. Weeee
            print(f"Initial setup - cloning Subsurface repo into {self._myroot}/subsurface")
            try:
                subprocess.run(
                    f"cd {self._myroot}; git clone --depth 10 https://github.com/subsurface/subsurface ; cd subsurface ; git clone https://github.com/subsurface/nightly-builds; git config --global --add safe.directory {self._myroot}/subsurface",
                    shell=True,
                    check=True,
                )
            except subprocess.CalledProcessError:
                print(
                    f"cloning the Subsurface repo into {self._myroot}/subsurface failed; the server will mostly run but "
                    "will be missing the user manual and the list of supported dive computers; please clone "
                    "the repo manually and restart"
                )

    def sync(self):
        try:
            subprocess.run(f"cd {self._myroot}/subsurface; git pull", shell=True, check=True)
        except subprocess.CalledProcessError:
            print("issue pulling the latest Subsurface sources - please check")
        shutil.copy(
            f"{self._myroot}/subsurface/SupportedDivecomputers.html",
            f"{self._myroot}/src/web/templates/",
        )
        try:
            subprocess.run(
                f"cd {self._myroot}/subsurface/Documentation; rm -rf output/images output/mobile-images; make output/user-manual.html output/user-manual_de.html output/mobile-manual-v3.html output/mobile-manual_de.html", shell=True, check=True
            )
        except subprocess.CalledProcessError:
            print("issue building the latest Subsurface documentation - please check")
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/output/user-manual.html",
            f"{self._myroot}/src/web/static/user-manual.html",
        )
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/output/user-manual_de.html",
            f"{self._myroot}/src/web/static/user-manual_de.html",
        )
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/output/mobile-manual-v3.html",
            f"{self._myroot}/src/web/static/mobile-user-manual.html",
        )
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/output/mobile-manual_de.html",
            f"{self._myroot}/src/web/static/mobile-user-manual_de.html",
        )
        shutil.copytree(
            f"{self._myroot}/subsurface/Documentation/output/images",
            f"{self._myroot}/src/web/static/images",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            f"{self._myroot}/subsurface/Documentation/output/mobile-images",
            f"{self._myroot}/src/web/static/mobile-images",
            dirs_exist_ok=True,
        )
