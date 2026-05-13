# =====================================================
# 🧠 APRIL BUILD MAP
# =====================================================

import os
import json

# =====================================================
# 🧠 ROOT
# =====================================================

ROOT_DIR = os.getcwd()

# =====================================================
# 🧠 OUTPUT
# =====================================================

OUTPUT_FILE = os.path.join(
    ROOT_DIR,
    "architecture",
    "architecture_snapshot.json"
)

# =====================================================
# 🧠 IGNORE
# =====================================================

IGNORE_FOLDERS = {

    "__pycache__",
    ".git",
    "venv",
    "env"
}

# =====================================================
# 🧠 SCAN PROJECT
# =====================================================

def scan_project():

    result = {

        "folders": [],
        "python_files": [],
        "systems": [],
        "rooms": [],
        "core": []
    }

    for root, dirs, files in os.walk(ROOT_DIR):

        dirs[:] = [

            d for d in dirs
            if d not in IGNORE_FOLDERS
        ]

        result["folders"].append(root)

        for file in files:

            if not file.endswith(".py"):
                continue

            full_path = os.path.join(
                root,
                file
            )

            result[
                "python_files"
            ].append(full_path)

            lower = file.lower()

            if "room" in lower:

                result[
                    "rooms"
                ].append(file)

            if "system" in lower:

                result[
                    "systems"
                ].append(file)

            if (
                root.startswith(
                    os.path.join(
                        ROOT_DIR,
                        "core"
                    )
                )
                or root.endswith("core")
            ):

                result[
                    "core"
                ].append(file)

    return result

# =====================================================
# 🧠 SAVE SNAPSHOT
# =====================================================

def save_snapshot(data):

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

# =====================================================
# 🧠 MAIN
# =====================================================

if __name__ == "__main__":

    snapshot = scan_project()

    save_snapshot(snapshot)

    print(
        "🧠 APRIL ARCHITECTURE MAP UPDATED"
    )
