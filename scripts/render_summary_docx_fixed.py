import os
import runpy
import shutil
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = ROOT / "tmp" / "docx_fixed_temp"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)


class FixedTemporaryDirectory:
    _counter = 0

    @classmethod
    def __class_getitem__(cls, _item):
        return cls

    def __init__(self, prefix="tmp"):
        type(self)._counter += 1
        self.name = str(TEMP_ROOT / f"{prefix}{type(self)._counter}")
        os.makedirs(self.name, exist_ok=True)

    def __enter__(self):
        return self.name

    def __exit__(self, _exc_type, _exc_value, _traceback):
        return False

    def cleanup(self):
        return None


tempfile.TemporaryDirectory = FixedTemporaryDirectory

original_which = shutil.which


def which(name, mode=0, path=None):
    if name.lower() == "soffice.exe":
        return r"C:\Program Files\LibreOffice\program\soffice.exe"
    return original_which(name, mode=mode, path=path)


shutil.which = which
runpy.run_path(
    r"C:\Users\USER\.codex\plugins\cache\openai-primary-runtime\documents\26.904.11930\skills\documents\render_docx.py",
    run_name="__main__",
)
