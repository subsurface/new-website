import copy
import json
from os import path
from .globals import globals


class Env:
    def __init__(
        self,
        name: str,
        value: str = None,
        default: any = None,
        value_call: callable = None,
    ):
        self._name = name
        self._value = self._default = default
        if (
            value != None
        ):  # only overwrite the default value if an actual Value was passed in
            self._value = value
        self._value_call = value_call
        # Let's make sure we have an env file
        if not path.isfile(globals.get("env_file_path")):
            open(globals.get("env_file_path"), "w").close()
        # Always reconcile from file
        self._reconcile(value=None, pull=True)

    def _reconcile(self, value, pull: bool = False):
        value_in_file = self._get_value_from_file()
        if pull and value_in_file != None:
            self._value = value_in_file
            return
        if value == value_in_file:
            return  # do not write to file if value is the same
        if value == None or value == "None":
            self._write_value_to_file("")
        else:
            self._write_value_to_file(value)

    def _get_values_from_file(self):
        ret = {}
        try:
            with open(globals.get("env_file_path"), "r") as f:
                for line in f.readlines():
                    if line.strip().startswith("#"):
                        continue
                    key, var = line.partition("=")[::2]
                    ret[key.strip()] = json.loads(var)
        except:
            pass

        return ret

    def _get_value_from_file(self):
        return self._get_values_from_file().get(self._name, None)

    def _write_value_to_file(self, new_value):
        values = self._get_values_from_file()
        values[self._name] = new_value
        with open(globals.get("env_file_path"), "w") as f:
            for key, value in values.items():
                if key:
                    f.write(f"{key}={json.dumps(value)}\n")

    def __str__(self):
        return f"Env({self._name}, {self._value})"

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        if self._value_call:
            return self._value_call()
        elif self._value != None:
            return copy.copy(self._value)
        elif self._default != None:
            return copy.copy(self._default)
        return ""

    @value.setter
    def value(self, value):
        if value != self._value:
            self._value = copy.copy(value)
            self._reconcile(value)


env = {
    "lrelease": Env("lrelease", default="6.0.5067"),
    "lrelease_date": Env("lrelease_date", default="2024-01-21"),
    "crelease": Env("crelease", default="6.0.5054"),
    "crelease_date": Env("crelease_date", default="2024-01-13"),
    "release_ids": Env("release_ids", default=[]),
    "pr_summary": Env("pr_summary", default=""),
}
