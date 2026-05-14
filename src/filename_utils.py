import os

def get_unique_filename(filename):
    """Return a filename that does not overwrite an existing file."""
    base, ext = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(new_filename):
        new_filename = f"{base}{counter}{ext}"
        counter += 1
    return new_filename
