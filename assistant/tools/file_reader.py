"""file_reader -- read a text file, path-restricted to one sandbox folder.

The model supplies a filename as plain text -- untrusted input, exactly
like a URL path segment from an HTTP request. Without a boundary check, a
filename like "../../../../etc/passwd" would escape wherever you intended
this tool to read from. ALLOWED_DIR below is that boundary; a sample file
lives at tools/sandbox/notes.txt to read for testing.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from .registry import register

ALLOWED_DIR = (Path(__file__).resolve().parent / "sandbox").resolve()


class FileReaderArgs(BaseModel):
    filename: str

"""
   TODO: completed
      1. Build the candidate path: (ALLOWED_DIR / args.filename).resolve()
      2. Verify it's still inside ALLOWED_DIR -- compare resolved paths,
         e.g. candidate.is_relative_to(ALLOWED_DIR) (Python 3.9+). Don't
         just string-check for ".." -- that's bypassable (symlinks,
         absolute paths, etc); resolving and comparing the real path is
         the actual check.
      3. If it escapes ALLOWED_DIR, or doesn't exist, raise ValueError
         with a clear message (registry.py wraps it into a ToolError).
      4. Otherwise return candidate.read_text().
"""
@register("file_reader", FileReaderArgs)
def file_reader(args: FileReaderArgs) -> str:

   """
   Read the contents of a text file, ensuring it is within the allowed sandbox directory.
   args:
       args (FileReaderArgs): The arguments containing the filename to read.
   returns:
       str: The contents of the file as a string.
   """
   candidate = (ALLOWED_DIR / args.filename).resolve()
   if not candidate.is_relative_to(ALLOWED_DIR):
      raise ValueError(f"Filename escapes allowed directory: {args.filename}")
   if not candidate.exists():
      raise ValueError(f"File does not exist: {args.filename}")
   return candidate.read_text()
