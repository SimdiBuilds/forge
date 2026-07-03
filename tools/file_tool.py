import shutil
from pathlib import Path

CATEGORY_RULES = {
    ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
    ".svg": "Images", ".webp": "Images",
    ".mp4": "Videos", ".mov": "Videos", ".avi": "Videos", ".mkv": "Videos",
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents", ".txt": "Documents",
    ".xls": "Spreadsheets", ".xlsx": "Spreadsheets", ".csv": "Spreadsheets",
    ".zip": "Archives", ".tar": "Archives", ".gz": "Archives", ".rar": "Archives",
    ".py": "Code", ".js": "Code", ".html": "Code", ".css": "Code", ".json": "Code",
}

FILE_TOOL_SCHEMA = {
    "name": "organise_files",
    "description": (
        "Organise files in a folder into category subfolders (Images, Documents, "
        "Videos, etc) based on file extension. Always call with dry_run=true first "
        "to preview the changes before the user confirms a real run."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "folder_path": {
                "type": "string",
                "description": "Path to the folder to organise",
            },
            "dry_run": {
                "type": "boolean",
                "description": "If true, only preview changes without moving any files",
                "default": True,
            },
        },
        "required": ["folder_path"],
    },
    "requires_confirmation": True,
}


def organise_files(folder_path: str, dry_run: bool = True) -> dict:
    source = Path(folder_path)

    if not source.exists() or not source.is_dir():
        return {"error": f"Folder not found: {folder_path}"}

    actions = []
    for file in source.iterdir():
        if not file.is_file():
            continue

        category = CATEGORY_RULES.get(file.suffix.lower(), "Other")
        target_dir = source / category
        destination = target_dir / file.name

        actions.append({
            "file": file.name,
            "category": category,
            "destination": str(destination),
        })

        if not dry_run:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(file), destination)

    return {
        "dry_run": dry_run,
        "folder": str(source),
        "files_found": len(actions),
        "actions": actions,
    }