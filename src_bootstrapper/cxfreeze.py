#cx freeze is for making a windows exe. this file is used by the release script to invoke it
import sys
from cx_Freeze import setup, Executable

sys.argv.append("build")
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="bootstrapper.exe",
    options={"build_exe": {"build_exe": "src_bootstrapper/dist"}},
    executables=[Executable("src_bootstrapper/bootstrapper.py", icon="mind.ico", base=base)],
)
