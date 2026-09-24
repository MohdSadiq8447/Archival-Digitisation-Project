from pathlib import Path
import subprocess

from extract_andhra_tables import PAGE_MAP, SOURCE_DIR


RENDER_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-next-pages")
PDFTOPPM = Path(r"C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def main() -> None:
    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    for source_name, table_map in PAGE_MAP.items():
        source = SOURCE_DIR / source_name
        start = max(table_map["medical_educational_amenities"]) + 1
        end = start + 1
        prefix = RENDER_DIR / source.stem
        subprocess.run(
            [str(PDFTOPPM), "-f", str(start), "-l", str(end), "-png", "-r", "90", "-q", str(source), str(prefix)],
            check=True,
        )


if __name__ == "__main__":
    main()
