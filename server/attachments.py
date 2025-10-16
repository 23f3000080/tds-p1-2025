# server/attachments.py
import os
import base64

def save_data_uri(data_uri: str, dest_folder: str, index: int = 0):
    """
    Save a data: URI string to a file inside dest_folder.
    Returns the full saved file path.
    """
    assert data_uri.startswith("data:"), "Invalid data URI"
    header, b64 = data_uri.split(",", 1)
    mediatype = header.split(";")[0][5:]  # e.g. image/png or text/csv

    # Choose proper extension
    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "text/csv": ".csv",
        "application/json": ".json",
        "text/markdown": ".md",
        "text/plain": ".txt"
    }.get(mediatype, ".dat")

    filename = f"attachment_{index}{ext}"
    path = os.path.join(dest_folder, filename)

    # Decode and write the file
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))

    return path  # ✅ Return full path instead of just filename
