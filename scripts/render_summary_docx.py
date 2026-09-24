import runpy
import shutil

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
