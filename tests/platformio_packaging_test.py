"""Check protocol selection and parity with native IDF source selection."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch
import fnmatch
import json
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Environment(dict):
    def __init__(self, frameworks, **options):
        super().__init__(PIOFRAMEWORK=frameworks)
        self.options = options

    def GetProjectOption(self, key, default=None):
        return self.options.get(key, default)

    def Append(self, **items):
        for key, values in items.items():
            self.setdefault(key, []).extend(values)

    def Replace(self, **items):
        self.update(items)


def configure(env):
    script = ModuleType("SCons.Script")
    script.Dir = lambda path: SimpleNamespace(srcnode=lambda: SimpleNamespace(abspath=str(ROOT)))
    with patch.dict(sys.modules, {"SCons": ModuleType("SCons"), "SCons.Script": script}):
        runpy.run_path(str(ROOT / "platformio.py"), init_globals={"env": env, "Import": lambda name: None})


def selected_sources(filters):
    selected = set()
    for path in (ROOT / "src").rglob("*.cpp"):
        relative = path.relative_to(ROOT / "src").as_posix()
        include = False
        for rule in filters:
            pattern = rule[2:-1]
            if pattern.endswith("/"):
                matches = relative.startswith(pattern)
            else:
                matches = fnmatch.fnmatchcase(relative, pattern)
            if matches:
                include = rule.startswith("+")
        if include:
            selected.add(relative)
    return selected


class PackagingTest(unittest.TestCase):
    def test_arduino_default_is_aliro_and_logging_is_not_forced(self):
        env = Environment(["arduino"])
        configure(env)
        self.assertEqual(env["CPPDEFINES"], [("CONFIG_DDK_PROTOCOL_ALIRO", 1)])
        sources = selected_sources(env["SRC_FILTER"])
        self.assertIn("aliro/Profile.cpp", sources)
        self.assertIn("transport/BleTransport.cpp", sources)
        self.assertNotIn("homekey/Profile.cpp", sources)

    def test_homekey_and_library_local_logging_override(self):
        env = Environment(["arduino"], custom_ddk_protocol="homekey", custom_ddk_log_level="0")
        configure(env)
        self.assertEqual(env["CPPDEFINES"], [("CONFIG_DDK_PROTOCOL_HOMEKEY", 1), ("LOG_LOCAL_LEVEL", 0)])
        sources = selected_sources(env["SRC_FILTER"])
        self.assertIn("homekey/Profile.cpp", sources)
        self.assertNotIn("aliro/Profile.cpp", sources)
        self.assertNotIn("transport/BleTransport.cpp", sources)
        self.assertNotIn("CONFIG_IDF_CMAKE", dict(env["CPPDEFINES"]))

    def test_idf_and_host_environments_are_untouched(self):
        for frameworks in (["espidf"], ["arduino", "espidf"], []):
            env = Environment(frameworks, custom_ddk_protocol="invalid", custom_ddk_log_level="invalid")
            before = env.copy()
            configure(env)
            self.assertEqual(env, before)

    def test_invalid_options_fail_early(self):
        for options in ({"custom_ddk_protocol": "both"}, {"custom_ddk_log_level": "6"}):
            with self.assertRaises(ValueError):
                configure(Environment(["arduino"], **options))

    def test_manifest_and_arduino_only_cbor_headers(self):
        manifest = json.loads((ROOT / "library.json").read_text())
        self.assertEqual(set(manifest["frameworks"]), {"arduino", "espidf"})
        self.assertNotIn("srcFilter", manifest["build"])
        self.assertFalse((ROOT / "include/tinycbor").exists())
        self.assertTrue((ROOT / "compat/arduino/tinycbor/cbor.h").exists())

    @unittest.skipUnless(shutil.which("cmake"), "CMake is needed for native IDF source parity")
    def test_source_filters_match_native_idf_cmake(self):
        for protocol in ("aliro", "homekey"):
            with self.subTest(protocol=protocol), tempfile.TemporaryDirectory(prefix="ddk-idf-selection-") as temp:
                directory = Path(temp)
                (directory / "dummy.cpp").write_text("int dummy;\n")
                cmake = """cmake_minimum_required(VERSION 3.16)
project(ddk_idf_selection LANGUAGES CXX)
set(ESP_PLATFORM TRUE)
set(CONFIG_DDK_PROTOCOL_@PROTOCOL@ TRUE)
function(idf_component_register)
    cmake_parse_arguments(IDF "" "" "SRCS;REQUIRES;PRIV_REQUIRES;INCLUDE_DIRS;PRIV_INCLUDE_DIRS" ${ARGN})
    if(NOT "cbor" IN_LIST IDF_PRIV_REQUIRES)
        message(FATAL_ERROR "Native IDF must keep its managed CBOR dependency")
    endif()
    add_library(ddk_component STATIC "${PROJECT_SOURCE_DIR}/dummy.cpp")
    set(COMPONENT_LIB ddk_component PARENT_SCOPE)
    file(WRITE "${CMAKE_BINARY_DIR}/sources.txt" "${IDF_SRCS}")
    file(WRITE "${CMAKE_BINARY_DIR}/includes.txt" "${IDF_INCLUDE_DIRS};${IDF_PRIV_INCLUDE_DIRS}")
endfunction()
add_subdirectory("@ROOT@" ddk)
""".replace("@PROTOCOL@", protocol.upper()).replace("@ROOT@", ROOT.as_posix())
                (directory / "CMakeLists.txt").write_text(cmake)
                result = subprocess.run(["cmake", "-S", str(directory), "-B", str(directory / "build")],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                native = {Path(p).relative_to(ROOT / "src").as_posix()
                          for p in (directory / "build/sources.txt").read_text().split(";") if p.endswith(".cpp")}
                env = Environment(["arduino"], custom_ddk_protocol=protocol)
                configure(env)
                self.assertEqual(selected_sources(env["SRC_FILTER"]), native)
                self.assertNotIn("compat/arduino", (directory / "build/includes.txt").read_text())


if __name__ == "__main__":
    unittest.main()
