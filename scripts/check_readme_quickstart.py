import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def extract_quickstart_section(readme: str) -> str:
    match = re.search(
        r"^## Quick Start[ \t]*\n(.*?)(?=^## |\Z)",
        readme,
        flags=re.MULTILINE | re.DOTALL,
    )

    if match is None:
        raise RuntimeError("README Quick Start section not found.")

    return match.group(1)


def extract_code_block(section: str, language: str) -> str:
    match = re.search(
        rf"^```{re.escape(language)}[ \t]*\n(.*?)^```[ \t]*$",
        section,
        flags=re.MULTILINE | re.DOTALL,
    )

    if match is None:
        raise RuntimeError(f"Quick Start is missing a {language} code block.")

    return match.group(1)


def main() -> None:
    readme = README.read_text(encoding="utf-8")

    quickstart = extract_quickstart_section(readme)

    csv_content = extract_code_block(quickstart, "csv")
    python_content = extract_code_block(quickstart, "python")

    with TemporaryDirectory() as temporary_directory:
        directory = Path(temporary_directory)

        csv_file = directory / "products.csv"
        python_file = directory / "quickstart.py"

        csv_file.write_text(csv_content, encoding="utf-8")
        python_file.write_text(python_content, encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, "-I", str(python_file)],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )

        if completed.returncode != 0:
            raise RuntimeError(
                "README Quick Start failed.\n"
                f"STDOUT:\n{completed.stdout}\n"
                f"STDERR:\n{completed.stderr}"
            )

        expected_lines = {
            "Processed: 2",
            "Valid: 2",
            "Rejected: 0",
        }

        actual_lines = set(completed.stdout.splitlines())

        missing_lines = expected_lines - actual_lines

        if missing_lines:
            raise RuntimeError(
                "README Quick Start produced unexpected results. "
                f"Missing output: {sorted(missing_lines)}"
            )

        print(completed.stdout, end="")

    print("README Quick Start verification passed.")


if __name__ == "__main__":
    main()
