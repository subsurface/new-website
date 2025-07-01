import os
import shutil
import subprocess
from .globals import globals


class SubsurfaceSync:
    def __init__(self) -> None:
        self._myroot = globals["app_path"]

    def setup(self):
        if not os.path.isdir(f"{self._myroot}/subsurface"):
            # ok - this is a brand new setup. Weeee
            print(f"Initial setup - cloning Subsurface repo into {self._myroot}/subsurface")
            try:
                subprocess.run(
                    f"cd {self._myroot}; git clone --depth 10 https://github.com/subsurface/subsurface",
                    shell=True,
                    check=True,
                )
            except:
                print(
                    f"cloning the Subsurface repo into {self._myroot}/subsurface failed; the server will mostly run but "
                    "will be missing the user manual and the list of supported dive computers; please clone "
                    "the repo manually and restart"
                )

    def sync(self):
        try:
            subprocess.run(f"cd {self._myroot}/subsurface; git pull", shell=True, check=True)
        except:
            print("issue pulling the latest Subsurface sources - please check")
        shutil.copy(
            f"{self._myroot}/subsurface/SupportedDivecomputers.html",
            f"{self._myroot}/src/web/templates/",
        )
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/user-manual.html.git",
            f"{self._myroot}/src/web/static/user-manual.html",
        )
        shutil.copy(
            f"{self._myroot}/subsurface/Documentation/mobile-manual-v3.html.git",
            f"{self._myroot}/src/web/static/mobile-user-manual.html",
        )
        shutil.copytree(
            f"{self._myroot}/subsurface/Documentation/images",
            f"{self._myroot}/src/web/static/images",
            dirs_exist_ok=True,
        )
        shutil.copytree(
            f"{self._myroot}/subsurface/Documentation/mobile-images",
            f"{self._myroot}/src/web/static/mobile-images",
            dirs_exist_ok=True,
        )
