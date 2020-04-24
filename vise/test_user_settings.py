# -*- coding: utf-8 -*-
#  Copyright (c) 2020. Distributed under the terms of the MIT License.

import os
import tempfile
from pathlib import Path

from vise.defaults import Defaults, UserSettings

# @patch("vise.config.get_user_settings",
#        ({"SYMMETRY_TOLERANCE": 10, "xc": "a"}, "b"))
# class ConfigTest(ViseTest):
#     from vise.config import \
#         SYMMETRY_TOLERANCE, MAIN_SETTINGS, VISE_YAML_FILES

    # def test_override(self):
    #     self.assertEqual(10, self.SYMMETRY_TOLERANCE)
    #     self.assertEqual("a", self.MAIN_SETTINGS["xc"])
    #     self.assertEqual("b", self.VISE_YAML_FILES[0])

"""
TODO
* Parse vise.yaml file and create related attributes.
DONE

"""


def test_user_settings_in_defaults():
    with tempfile.TemporaryDirectory() as dirname:

        os.chdir(dirname)
        path = Path.cwd()
        with open('vise.yaml', mode="w") as f:
            f.write("""
        ldauu: 
            Mn: 5""")
        defaults = Defaults()

    actual = defaults.user_settings["ldauu"]
    expected = {"Mn": 5}

    assert actual == expected



"""
TODO

DONE
- Get current working directory Path.
- Find all the yaml files with the given name to the root directory.
- Method to return the file names and their respective setting keys.
- Allow hidden files, e.g., .test.yaml
- When the key includes "/", the absolute path is added as a prefix.
  E.g., unitcell/unitcell.json -> /something/../unitcell/unitcell.json
"""


def test_get_yaml_filenames():
    with tempfile.TemporaryDirectory() as dirname:

        os.chdir(dirname)
        path_second_last_dirname = Path.cwd()
        Path("test.yaml").touch()

        Path("terminal_dir").mkdir()
        os.chdir("terminal_dir")
        Path("test.yaml").touch()

        user_settings = UserSettings(yaml_filename="test.yaml")

    actual = user_settings.yaml_files_from_root_dir

    path_last_dirname = path_second_last_dirname / "terminal_dir"
    expected = [path_second_last_dirname / "test.yaml",
                path_last_dirname / "test.yaml"]

    assert actual == expected


def test_user_settings():
    with tempfile.TemporaryDirectory() as dirname:

        os.chdir(dirname)
        with open('test.yaml', mode="w") as f:
            f.write("""
        float: 0.01
        dict:
          d1: 5
          d2: 3""")

        Path("terminal_dir").mkdir()
        os.chdir("terminal_dir")
        with open('test.yaml', mode="w") as f:
            f.write("""
        str: s1 s2
        dict:
          d1: 10 
          d2: 3""")

        user_settings = UserSettings(yaml_filename="test.yaml")
    actual = user_settings.user_settings
    expected = {"float": 0.01,
                "dict": {"d1": 10, "d2": 3},
                "str": "s1 s2",
                }

    assert actual == expected


def test_parse_hidden_file():
    with tempfile.TemporaryDirectory() as dirname:

        os.chdir(dirname)
        with open('.test.yaml', mode="w") as f:
            f.write("""
        float: 0.01""")

        user_settings = UserSettings(yaml_filename="test.yaml")
    actual = user_settings.user_settings
    expected = {"float": 0.01}

    assert actual == expected


def test_add_absolute_path():
    with tempfile.TemporaryDirectory() as dirname:

        os.chdir(dirname)
        path = Path.cwd()
        with open('test.yaml', mode="w") as f:
            f.write("""
        path: a/b""")

        user_settings = UserSettings(yaml_filename="test.yaml")

    actual = user_settings.user_settings["path"]
    expected = path / "a/b"

    assert actual == expected
