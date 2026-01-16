#!/usr/bin/env python3
"""Format indentation for Fortran free-form source files (*.f90).

Heuristic-based formatter that adjusts indentation for typical block keywords
(module, subroutine, function, do, if ... then, select case, type, where, associate, block).

Usage:
  format_fortran_indent.py [paths...] [--indent-size N] [--dry-run] [--inplace]

Examples:
  # Preview changes (dry-run):
  ./format_fortran_indent.py --dry-run .

  # Apply changes in place with 4-space indents:
  ./format_fortran_indent.py --inplace --indent-size 4 src/ tests/
"""

from __future__ import annotations
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple


LABEL = r"[a-zA-Z0-9_]\w*"

# Keywords that start a new block (increase indent after the line)
OPENING_RE = re.compile(
    rf"""^\s*(?:
        (?:{LABEL}\s*:\s*)?module\b|
        (?:{LABEL}\s*:\s*)?subroutine\b|
        (?:{LABEL}\s*:\s*)?(?:{LABEL}(?:\s*\([^)]*\))?\s+)*function\b|
        (?:{LABEL}\s*:\s*)?program\b|
        (?:{LABEL}\s*:\s*)?block\b(?!\s*data\b)|
        (?:{LABEL}\s*:\s*)?do\b(?!\w)|
        if\b[^!]*\bthen\b|
        if\b[^!]*&\s*$|
        select\s+(case|type|rank)\b|
        type\b\s*::|
        interface\b|
        where\b|
        associate\b|
        enum\b|
        critical\b
    )""",
    re.IGNORECASE | re.VERBOSE
)

# Keywords that close a block (decrease indent before the line)
CLOSING_RE = re.compile(
    rf"""^\s*(?:
        end\b|
        end\s+module\b|
        end\s+subroutine\b|
        end\s+function\b|
        end\s+program\b|
        end\s+block\b|
        end\s*do\b(?:\s+{LABEL})?|
        end\s+select\b|
        end\s+type\b|
        end\s+interface\b|
        end\s+where\b|
        end\s+associate\b|
        end\s*if\b
    )""",
    re.IGNORECASE | re.VERBOSE
)

# Mid-block keywords that don't change block nesting but are dedented (else/elseif/case)
MIDDLE_DEDENT_RE = re.compile(r"^\s*(?:else\b|elseif\b|else\s+if\b|case\b)", re.IGNORECASE)
# Lines that indicate continuation in free-form Fortran (starting with & or previous line ending with &)
CONTINUATION_START = re.compile(r"^\s*&")
CONTINUATION_END = re.compile(r"&\s*$")
# Comment detection (Fortran comment starts with !)
COMMENT_RE = re.compile(r"^\s*!")


def format_lines(lines: List[str], indent_size: int = 4) -> List[str]:
    """Return a new list of lines with adjusted indentation."""
    out: List[str] = []
    indent_level = 0
    prev_line_ended_with_amp = False

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        is_middle_dedent = False
        is_closing = False

        # Blank lines are preserved as-is
        if stripped == "":
            out.append("")
            prev_line_ended_with_amp = False
            continue

        # If this is a continuation line (starts with &), keep previous indent
        if CONTINUATION_START.match(line):
            indent = max(indent_level, 0)
            out.append((" " * (indent * indent_size)) + stripped)
            prev_line_ended_with_amp = CONTINUATION_END.search(line) is not None
            continue

        # Comments: keep at current indent, but if comment has block-like keywords we don't treat them
        if COMMENT_RE.match(line):
            out.append((" " * (indent_level * indent_size)) + stripped)
            prev_line_ended_with_amp = False
            continue

        # Detect closing/middle keywords
        is_middle_dedent = MIDDLE_DEDENT_RE.match(line) is not None
        is_closing = CLOSING_RE.match(line) is not None

        # If middle-dedent (else/elseif/case), dedent once for the line
        if is_middle_dedent:
            indent_level = max(indent_level - 1, 0)

        # If current line is a block closer, dedent before emitting
        if is_closing:
            indent_level = max(indent_level - 1, 0)

        # Emit the line at current indent
        out.append((" " * (indent_level * indent_size)) + stripped)
        
        # If middle-dedent (else/elseif/case), add back the indent level
        if is_middle_dedent:
            indent_level = indent_level +1 

        # Determine if this line opens a new block. Note: do not increase if the same line also closes (one-line if .. end if)
        opens_block = OPENING_RE.match(line) is not None
        closes_on_same_line = re.search(r"\bend\b", line, re.IGNORECASE) is not None or re.search(r"\bendif\b", line, re.IGNORECASE) is not None

        # Special: a line like "case ..." should not increase indent; likewise 'else'/'elseif' don't increase
        if opens_block and not is_middle_dedent and not closes_on_same_line:
            indent_level += 1

        # Track continuation
        prev_line_ended_with_amp = CONTINUATION_END.search(line) is not None

    return [l + "\n" for l in out]


def format_file(path: Path, indent_size: int = 4, inplace: bool = True, dry_run: bool = False, backup: bool = True) -> Tuple[bool, str]:
    """Format a single file. Returns (changed, message)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"Failed to read {path}: {e}"

    orig_lines = text.splitlines(True)
    new_lines = format_lines(orig_lines, indent_size=indent_size)

    if orig_lines == new_lines:
        return False, f"No changes for {path}"

    if dry_run:
        return True, f"Would change {path}"

    # Make backup
    if inplace:
        if backup:
            bak = path.with_suffix(path.suffix + ".bak")
            bak.write_text(text, encoding="utf-8")
        # The `path` variable in this script is used to represent a file path. It is of type `Path`
        # from the `pathlib` module in Python. The script reads the content of the file specified by
        # the `path` variable, processes the content to adjust the indentation for Fortran free-form
        # source files, and then writes the modified content back to the same file if the `inplace`
        # flag is set to `True`. The `format_file` function takes a `Path` object as an argument to
        # format a single file.
        path.write_text(''.join(new_lines), encoding="utf-8")
        return True, f"Updated {path} (backup: {bak.name if backup else 'none'})"

    return True, f"Changes prepared for {path} (not written)"


def collect_files(paths: List[Path]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        if p.is_dir():
            for f in sorted(p.rglob('*.f90')):
                files.append(f)
        elif p.is_file() and p.suffix.lower() == '.f90':
            files.append(p)
    return files


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Format indentation for Fortran free-form files (*.f90)")
    parser.add_argument('paths', nargs='*', default=['.'], help='Files or directories to process (default: current directory)')
    parser.add_argument('--indent-size', type=int, default=4, help='Number of spaces per indent level (default 4)')
    parser.add_argument('--inplace', action='store_true', help='Modify files in place')
    parser.add_argument('--no-backup', action='store_true', help='Do not keep backup when writing files')
    parser.add_argument('--dry-run', action='store_true', help='Show which files would change without modifying them')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress')
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    files = collect_files(paths)

    if not files:
        print('No .f90 files found in the specified paths.')
        return 0

    changed_any = False
    for f in files:
        changed, msg = format_file(f, indent_size=args.indent_size, inplace=args.inplace, dry_run=args.dry_run, backup=(not args.no_backup))
        if args.verbose:
            print(msg)
        else:
            if changed:
                print(msg)
        changed_any = changed_any or changed

    if args.dry_run and changed_any:
        print('\nRun with --inplace to apply these changes.')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
