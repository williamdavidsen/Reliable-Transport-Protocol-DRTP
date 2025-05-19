import os

def get_unique_filename(filename):
    """
    Description:
        Generates a unique file name by appending a numerical suffix if a file
        with the given name already exists in the file system. This function prevents
        overwriting existing files when saving incoming data.

    Arguments:
        filename (str): The proposed file name (e.g., 'received_Photo.jpg').

    Use of other input and output parameters in the function:
        - Splits the filename into a base and extension.
        - Checks for the existence of the filename in the current directory.
        - Increments a counter and appends it to the base name if needed.

    Returns:
        new_filename (str): A unique file name guaranteed not to overwrite an existing file.

    Exceptions:
        - This function does not raise exceptions itself, but relies on os.path.exists.
        - If filename is an invalid path or permission is denied, exceptions could occur elsewhere in the program.
    """
    base, ext = os.path.splitext(filename)  # Separate file into base name and extension
    counter = 1
    new_filename = filename
    while os.path.exists(new_filename):
        new_filename = f"{base}{counter}{ext}"
        counter += 1
    return new_filename
