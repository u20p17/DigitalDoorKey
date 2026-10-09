from pathlib import Path
from SCons.Script import Dir
Import("env")
root = Path(Dir(".").srcnode().abspath)
env.Append(CPPPATH=[str(root / "priv")])
env.Append(CPPDEFINES=[("CONFIG_DDK_PROTOCOL_HOMEKEY", 1), ("CONFIG_IDF_CMAKE", 1), ("LOG_LOCAL_LEVEL", 0)])
