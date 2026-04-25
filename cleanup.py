"""Cleanup script — restore .tobedeleted images so they can be reprocessed."""
import sqlite3
import sys
from pathlib import Path

if __name__ == "__main__":
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from src import config, db


def restore_tobedeleted(folder: Path) -> list[tuple[str, str]]:
    restored = []
    for f in sorted(folder.glob("*")):
        if not f.is_file():
            continue
        if f.name.endswith(".tobedeleted"):
            name = f.name[: -len(".tobedeleted")]
            original = f.parent / name
            try:
                f.rename(original)
                restored.append((f.name, name))
            except Exception as e:
                print(f"  ERROR {e}: {f.name}")
    return restored


def reset_db_entries(folder: Path, restored: list[tuple[str, str]]) -> None:
    db_path = db.get_db_path()
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    for old, new in restored:
        for path in [str((folder / old).resolve()), str((folder / new).resolve())]:
            conn.execute("DELETE FROM processed_files WHERE file_path = ?", (path,))
    conn.commit()
    conn.close()


def main():
    cfg = config.load_config()
    folder = cfg.source_folder

    tobedeleted = [
        f for f in sorted(folder.glob("*"))
        if f.is_file() and f.name.endswith(".tobedeleted")
    ]

    if not tobedeleted:
        print(f"No .tobedeleted images in:\n  {folder}")
        return

    print(f"Found {len(tobedeleted)} .tobedeleted image(s):")
    for f in tobedeleted:
        print(f"  {f.name[: -len('.tobedeleted')]}")
    print()

    while True:
        choice = input("Restore [a]ll / [n]one / [q]uit: ").strip().lower()
        if choice in ("a", "n", "q"):
            break
        print("Enter a, n, or q")

    if choice == "q":
        return
    if choice == "n":
        print("Nothing changed.")
        return

    print()
    restored = restore_tobedeleted(folder)
    print(f"Restored {len(restored)} image(s):")
    for old, new in restored:
        print(f"  {old}  ->  {new}")

    print(f"\nResetting DB entries...")
    db.init_db()
    reset_db_entries(folder, restored)
    print("Done.")


if __name__ == "__main__":
    main()