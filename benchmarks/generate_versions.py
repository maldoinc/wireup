import re
import os

# Configuration
RUNNER_PATH = "benchmarks/bench_runner.py"
DOCS_PATH = "docs/pages/benchmarks.md"


def extract_versions() -> list[str]:
    with open(RUNNER_PATH, "r") as f:
        content = f.read()

    lines = content.splitlines()
    dep_lines: list[str] = []
    in_deps = False

    for line in lines:
        clean = line.strip()
        if "dependencies = [" in clean:
            in_deps = True
            continue
        if in_deps:
            if re.match(r"^#\s*\]\s*$", clean):
                break

            if "# bench-keep" in clean:
                match = re.search(r'"([^"]+==[^"]+)"', clean)
                if match:
                    dep_lines.append(match.group(1))

    return dep_lines


def get_wireup_version() -> str:
    return os.getenv("BENCH_WIREUP_VERSION", "unknown")


def update_docs() -> None:
    versions = extract_versions()

    # Build the table lines (without indentation yet)
    table_lines = ["| Package | Version |", "| :--- | :--- |"]
    table_lines.append(f"| wireup | {get_wireup_version()} |")
    for v in versions:
        if "==" in v:
            name, version = v.split("==")
            table_lines.append(f"| {name} | {version} |")

    with open(DOCS_PATH, "r") as f:
        content = f.read()

    # Find the versions block and its indentation
    # We match from the start tag to the end tag
    match = re.search(r"^([ \t]*)<!-- versions-start -->.*?<!-- versions-end -->", content, re.DOTALL | re.MULTILINE)
    if not match:
        print("Versions placeholder not found in docs")
        return

    indent = match.group(1)

    # Indent all table lines
    indented_table = "\n".join(f"{indent}{line}" for line in table_lines)

    # Construction of the replacement block
    # We need a blank line between the tag and the table    # Construction of the replacement block
    # We need a blank line between the tag and the table for proper MD rendering
    replacement = f"{indent}<!-- versions-start -->\n\n{indented_table}\n\n{indent}<!-- versions-end -->"

    # Replace the captured block with the new one
    new_content = content[: match.start()] + replacement + content[match.end() :]

    with open(DOCS_PATH, "w") as f:
        f.write(new_content)

    print(f"Successfully updated versions in {DOCS_PATH}")


if __name__ == "__main__":
    update_docs()
