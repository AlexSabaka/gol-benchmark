#!/usr/bin/env python3
"""
Text Table Generator - Convert tabular data to formatted ASCII/Unicode tables.

A self-contained Python module for generating formatted text tables with multiple
styles, comment wrappers, and alignment options. Usable as both a module and CLI tool.

Usage as module:
    from src.utils.text_table import create_table, TableStyle
    
    data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "Los Angeles"],
    ]
    
    # Simple usage
    print(create_table(data))
    
    # With options
    print(create_table(data, style="unicode", has_headers=True, align="auto"))

Usage as CLI:
    python -m src.utils.text_table input.csv --style mysql --headers
    cat data.csv | python -m src.utils.text_table --style gfm --headers
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from io import StringIO
from typing import List, Optional, Sequence, Union


class TableStyle(Enum):
    """Available table rendering styles."""
    MYSQL = "mysql"
    SEPARATED = "separated"
    COMPACT = "compact"
    ROUNDED = "rounded"
    GIRDER = "girder"
    BUBBLES = "bubbles"
    DOTS = "dots"
    GFM = "gfm"  # GitHub Flavored Markdown
    REDDIT = "reddit"
    RST_GRID = "rst_grid"  # reStructuredText Grid
    RST_SIMPLE = "rst_simple"  # reStructuredText Simple
    JIRA = "jira"
    MEDIAWIKI = "mediawiki"
    UNICODE = "unicode"
    UNICODE_SINGLE = "unicode_single"
    HTML = "html"
    PLAIN = "plain"


class CommentStyle(Enum):
    """Comment wrapper styles for different programming languages."""
    NONE = "none"
    DOUBLE_SLASH = "double_slash"  # C++/C#/Java/JavaScript/Rust/Swift
    HASH = "hash"  # Python/Perl/Ruby/Shell
    DOUBLE_DASH = "double_dash"  # SQL/Haskell/Lua
    DOCBLOCK = "docblock"  # PHPDoc/JSDoc/Javadoc
    PERCENT = "percent"  # MATLAB/LaTeX
    SINGLE_SPACE = "single_space"  # MediaWiki
    QUAD_SPACE = "quad_space"  # Reddit
    SINGLE_QUOTE = "single_quote"  # VBA
    REM = "rem"  # BASIC/DOS
    C = "c"  # Fortran IV
    EXCLAMATION = "exclamation"  # Fortran 90
    SLASH_STAR = "slash_star"  # CSS
    XML = "xml"  # XML/HTML comments
    PIPE = "pipe"


class Alignment(Enum):
    """Text alignment options."""
    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    AUTO = "auto"  # Numbers right, text left


@dataclass
class StyleConfig:
    """Configuration for a table style's border characters."""
    # Corner characters
    corner_tl: str = "+"  # Top-left
    corner_tm: str = "+"  # Top-middle
    corner_tr: str = "+"  # Top-right
    corner_ml: str = "+"  # Middle-left
    corner_mm: str = "+"  # Middle-middle
    corner_mr: str = "+"  # Middle-right
    corner_bl: str = "+"  # Bottom-left
    corner_bm: str = "+"  # Bottom-middle
    corner_br: str = "+"  # Bottom-right
    
    # Line characters
    header_vertical: str = "|"
    header_horizontal: str = "-"
    separator_vertical: str = "|"
    separator_horizontal: str = "-"
    
    # Display options
    has_top_line: bool = True
    has_bottom_line: bool = True
    has_left_side: bool = True
    has_right_side: bool = True
    has_header_separator: bool = True
    has_line_separators: bool = False
    top_line_uses_body_separators: bool = False


@dataclass
class CommentConfig:
    """Configuration for comment wrappers."""
    prefix: str = ""
    suffix: str = ""
    before: str = ""
    after: str = ""


def get_style_config(style: Union[TableStyle, str]) -> StyleConfig:
    """Get the border configuration for a table style."""
    if isinstance(style, str):
        style = TableStyle(style.lower())
    
    configs = {
        TableStyle.MYSQL: StyleConfig(
            corner_tl="+", corner_tm="+", corner_tr="+",
            corner_ml="+", corner_mm="+", corner_mr="+",
            corner_bl="+", corner_bm="+", corner_br="+",
            header_vertical="|", header_horizontal="-",
            separator_vertical="|", separator_horizontal="-",
        ),
        TableStyle.SEPARATED: StyleConfig(
            corner_tl="+", corner_tm="+", corner_tr="+",
            corner_ml="+", corner_mm="+", corner_mr="+",
            corner_bl="+", corner_bm="+", corner_br="+",
            header_vertical="|", header_horizontal="=",
            separator_vertical="|", separator_horizontal="-",
            has_line_separators=True,
        ),
        TableStyle.COMPACT: StyleConfig(
            corner_ml=" ", corner_mm=" ", corner_mr=" ",
            header_vertical=" ", header_horizontal="-",
            separator_vertical=" ", separator_horizontal="-",
            has_top_line=False, has_bottom_line=False,
        ),
        TableStyle.ROUNDED: StyleConfig(
            corner_tl=".", corner_tm=".", corner_tr=".",
            corner_ml=":", corner_mm="+", corner_mr=":",
            corner_bl="'", corner_bm="'", corner_br="'",
            header_vertical="|", header_horizontal="-",
            separator_vertical="|", separator_horizontal="-",
            has_line_separators=True,
        ),
        TableStyle.GIRDER: StyleConfig(
            corner_tl="//", corner_tm="[]", corner_tr="\\\\",
            corner_ml="|]", corner_mm="[]", corner_mr="[|",
            corner_bl="\\\\", corner_bm="[]", corner_br="//",
            header_vertical="||", header_horizontal="=",
            separator_vertical="||", separator_horizontal="=",
        ),
        TableStyle.BUBBLES: StyleConfig(
            corner_tl=" o8", corner_tm="(_)", corner_tr="8o ",
            corner_ml="(88", corner_mm="(_)", corner_mr="88)",
            corner_bl=" O8", corner_bm="(_)", corner_br="8O ",
            header_vertical="(_)", header_horizontal="8",
            separator_vertical="(_)", separator_horizontal="o",
        ),
        TableStyle.DOTS: StyleConfig(
            corner_tl=".", corner_tm=".", corner_tr=".",
            corner_ml=":", corner_mm=":", corner_mr=":",
            corner_bl=":", corner_bm=":", corner_br=":",
            header_vertical=":", header_horizontal=".",
            separator_vertical=":", separator_horizontal=".",
        ),
        TableStyle.GFM: StyleConfig(
            corner_tl="|", corner_tm="|", corner_tr="|",
            corner_ml="|", corner_mm="|", corner_mr="|",
            corner_bl="|", corner_bm="|", corner_br="|",
            header_vertical="|", header_horizontal="-",
            separator_vertical="|", separator_horizontal="-",
            has_top_line=False, has_bottom_line=False,
        ),
        TableStyle.REDDIT: StyleConfig(
            corner_tl=" ", corner_tm="|", corner_tr=" ",
            corner_ml=" ", corner_mm="|", corner_mr=" ",
            corner_bl=" ", corner_bm="|", corner_br=" ",
            header_vertical="|", header_horizontal="-",
            separator_vertical="|", separator_horizontal="-",
            has_top_line=False, has_bottom_line=False,
            has_left_side=False, has_right_side=False,
        ),
        TableStyle.RST_GRID: StyleConfig(
            corner_tl="+", corner_tm="+", corner_tr="+",
            corner_ml="+", corner_mm="+", corner_mr="+",
            corner_bl="+", corner_bm="+", corner_br="+",
            header_vertical="|", header_horizontal="=",
            separator_vertical="|", separator_horizontal="-",
            has_top_line=True, top_line_uses_body_separators=True,
        ),
        TableStyle.RST_SIMPLE: StyleConfig(
            corner_tl=" ", corner_tm=" ", corner_tr=" ",
            corner_ml=" ", corner_mm=" ", corner_mr=" ",
            corner_bl=" ", corner_bm=" ", corner_br=" ",
            header_vertical=" ", header_horizontal="=",
            separator_vertical=" ", separator_horizontal="=",
            has_top_line=True, has_bottom_line=True,
        ),
        TableStyle.JIRA: StyleConfig(
            corner_tl="", corner_tm="", corner_tr="",
            corner_ml="", corner_mm="", corner_mr="",
            corner_bl="", corner_bm="", corner_br="",
            header_vertical="||", header_horizontal="",
            separator_vertical="| ", separator_horizontal="",
            has_top_line=False, has_bottom_line=False,
            has_header_separator=False,
        ),
        TableStyle.MEDIAWIKI: StyleConfig(
            corner_tl='{| class="wikitable"', corner_tm="", corner_tr="",
            corner_ml="|-", corner_mm="", corner_mr="",
            corner_bl="", corner_bm="", corner_br="|}",
            header_vertical="\n!", header_horizontal="",
            separator_vertical="\n|", separator_horizontal="",
            has_line_separators=True, has_right_side=False,
        ),
        TableStyle.UNICODE: StyleConfig(
            corner_tl="╔", corner_tm="╦", corner_tr="╗",
            corner_ml="╠", corner_mm="╬", corner_mr="╣",
            corner_bl="╚", corner_bm="╩", corner_br="╝",
            header_vertical="║", header_horizontal="═",
            separator_vertical="║", separator_horizontal="═",
        ),
        TableStyle.UNICODE_SINGLE: StyleConfig(
            corner_tl="┌", corner_tm="┬", corner_tr="┐",
            corner_ml="├", corner_mm="┼", corner_mr="┤",
            corner_bl="└", corner_bm="┴", corner_br="┘",
            header_vertical="│", header_horizontal="─",
            separator_vertical="│", separator_horizontal="─",
        ),
        TableStyle.PLAIN: StyleConfig(
            corner_tl="", corner_tm="", corner_tr="",
            corner_ml="", corner_mm="", corner_mr="",
            corner_bl="", corner_bm="", corner_br="",
            header_vertical="  ", header_horizontal="",
            separator_vertical="  ", separator_horizontal="",
            has_top_line=False, has_bottom_line=False,
            has_header_separator=False,
        ),
    }
    
    return configs.get(style, configs[TableStyle.MYSQL])


def get_comment_config(style: Union[CommentStyle, str]) -> CommentConfig:
    """Get the comment wrapper configuration for a language style."""
    if isinstance(style, str):
        style = CommentStyle(style.lower())
    
    configs = {
        CommentStyle.NONE: CommentConfig(),
        CommentStyle.DOUBLE_SLASH: CommentConfig(prefix="// "),
        CommentStyle.HASH: CommentConfig(prefix="# "),
        CommentStyle.DOUBLE_DASH: CommentConfig(prefix="-- "),
        CommentStyle.DOCBLOCK: CommentConfig(prefix=" * ", before="/**", after=" */"),
        CommentStyle.PERCENT: CommentConfig(prefix="% "),
        CommentStyle.SINGLE_SPACE: CommentConfig(prefix=" "),
        CommentStyle.QUAD_SPACE: CommentConfig(prefix="    "),
        CommentStyle.SINGLE_QUOTE: CommentConfig(prefix="' "),
        CommentStyle.REM: CommentConfig(prefix="REM "),
        CommentStyle.C: CommentConfig(prefix="C "),
        CommentStyle.EXCLAMATION: CommentConfig(prefix="! "),
        CommentStyle.SLASH_STAR: CommentConfig(prefix="/* ", suffix=" */"),
        CommentStyle.XML: CommentConfig(prefix="<!-- ", suffix=" -->"),
        CommentStyle.PIPE: CommentConfig(prefix="|", suffix="|"),
    }
    
    return configs.get(style, CommentConfig())


def _is_number(value: str) -> bool:
    """Check if a string represents a number (for auto-alignment)."""
    # Match integers, decimals, negative numbers, comma-separated numbers
    return bool(re.match(r'^\s*-?[\d,.\s]*\s*$', value)) and any(c.isdigit() for c in value)


def _pad(text: str, width: int, char: str = " ", align: str = "left") -> str:
    """Pad text to a specified width with alignment."""
    additional = width - len(text)
    if additional <= 0:
        return text
    
    if align == "right" or align == "r":
        return char * additional + text
    elif align == "center" or align == "c":
        left_pad = additional // 2
        right_pad = additional - left_pad
        return char * left_pad + text + char * right_pad
    else:  # left
        return text + char * additional


def _get_separator_row(
    col_widths: List[int],
    left: str,
    middle: str,
    right: str,
    horizontal: str,
    prefix: str = "",
    suffix: str = ""
) -> str:
    """Generate a separator row (e.g., +---+---+)."""
    if not horizontal:
        return ""
    
    parts = [prefix]
    for i, width in enumerate(col_widths):
        if i == 0:
            parts.append(left + horizontal * (width + 2))
        else:
            parts.append(middle + horizontal * (width + 2))
    parts.append(right + suffix + "\n")
    
    return "".join(parts)


def create_table(
    data: Sequence[Sequence[str]],
    style: Union[TableStyle, str] = TableStyle.MYSQL,
    has_headers: bool = True,
    spreadsheet_style: bool = False,
    align: Union[Alignment, str] = Alignment.AUTO,
    comment_style: Union[CommentStyle, str] = CommentStyle.NONE,
    trim_cells: bool = True,
) -> str:
    """
    Create a formatted text table from tabular data.
    
    Args:
        data: List of rows, where each row is a list of cell values.
              First row is treated as headers if has_headers=True.
        style: Table border style (see TableStyle enum).
        has_headers: Whether first row should be treated as headers.
        spreadsheet_style: Add row numbers and column letters (A, B, C...).
        align: Text alignment - "left", "right", "center", or "auto".
               Auto aligns numbers right and text left.
        comment_style: Wrap output in language-specific comments.
        trim_cells: Strip whitespace from cell values.
    
    Returns:
        Formatted table as a string.
    
    Example:
        >>> data = [["Name", "Age"], ["Alice", "30"], ["Bob", "25"]]
        >>> print(create_table(data, style="mysql", has_headers=True))
        +-------+-----+
        | Name  | Age |
        +-------+-----+
        | Alice |  30 |
        | Bob   |  25 |
        +-------+-----+
    """
    if not data:
        return ""
    
    # Convert to list of lists and handle string conversion
    rows: List[List[str]] = []
    for row in data:
        rows.append([str(cell) if cell is not None else "" for cell in row])
    
    # Get configurations
    if isinstance(style, str):
        style = TableStyle(style.lower().replace("-", "_"))
    
    if isinstance(align, str):
        align = Alignment(align.lower())
    
    if isinstance(comment_style, str):
        comment_style = CommentStyle(comment_style.lower())
    
    # Handle HTML separately
    if style == TableStyle.HTML:
        return _create_html_table(rows, has_headers)
    
    style_cfg = get_style_config(style)
    comment_cfg = get_comment_config(comment_style)
    
    # Apply spreadsheet style (add row numbers and column letters)
    if spreadsheet_style:
        has_headers = True
        for i, row in enumerate(rows):
            row.insert(0, str(i + 1))
        # Add column headers
        col_count = max(len(row) for row in rows) if rows else 0
        header_row = [" "] + [chr(65 + min(i, 25)) for i in range(col_count - 1)]
        rows.insert(0, header_row)
    
    # Trim cells if requested
    if trim_cells:
        rows = [[cell.strip() for cell in row] for row in rows]
    
    # Calculate column widths and detect number columns
    col_count = max(len(row) for row in rows) if rows else 0
    col_widths = [0] * col_count
    is_number_col = [True] * col_count
    
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            col_widths[j] = max(col_widths[j], len(cell))
            
            # Check if column is numeric (skip header row)
            if align == Alignment.AUTO:
                if has_headers and i == 0 and not spreadsheet_style:
                    pass  # Headers can be text
                elif is_number_col[j] and not _is_number(cell):
                    is_number_col[j] = False
    
    # Pad rows to have consistent column count
    for row in rows:
        while len(row) < col_count:
            row.append("")
    
    # Build output
    output_lines: List[str] = []
    
    # Comment wrapper - before
    if comment_cfg.before:
        output_lines.append(comment_cfg.before + "\n")
    
    # Top line
    if style_cfg.has_top_line:
        if style_cfg.top_line_uses_body_separators or not has_headers:
            horiz = style_cfg.separator_horizontal
        else:
            horiz = style_cfg.header_horizontal
        
        sep = _get_separator_row(
            col_widths,
            style_cfg.corner_tl, style_cfg.corner_tm, style_cfg.corner_tr,
            horiz, comment_cfg.prefix, comment_cfg.suffix
        )
        if sep:
            output_lines.append(sep)
    
    # Data rows
    for i, row in enumerate(rows):
        # Header separator row
        if has_headers and style_cfg.has_header_separator and i == 1:
            sep = _get_separator_row(
                col_widths,
                style_cfg.corner_ml, style_cfg.corner_mm, style_cfg.corner_mr,
                style_cfg.header_horizontal, comment_cfg.prefix, comment_cfg.suffix
            )
            if sep:
                output_lines.append(sep)
        # Line separators between data rows
        elif style_cfg.has_line_separators and i > 0:
            if (not has_headers and i >= 1) or (has_headers and i > 1):
                sep = _get_separator_row(
                    col_widths,
                    style_cfg.corner_ml, style_cfg.corner_mm, style_cfg.corner_mr,
                    style_cfg.separator_horizontal, comment_cfg.prefix, comment_cfg.suffix
                )
                if sep:
                    output_lines.append(sep)
        
        # Data row
        line_parts = [comment_cfg.prefix]
        
        for j, cell in enumerate(row):
            # Determine alignment for this cell
            if align == Alignment.AUTO:
                if has_headers and i == 0:
                    cell_align = "center"
                elif is_number_col[j]:
                    cell_align = "right"
                else:
                    cell_align = "left"
            else:
                cell_align = align.value
            
            # Determine vertical bar character
            if has_headers and i == 0:
                vert = style_cfg.header_vertical
            else:
                vert = style_cfg.separator_vertical
            
            # Pad cell content
            padded = _pad(cell, col_widths[j], " ", cell_align)
            
            # Build cell output
            if j == 0 and not style_cfg.has_left_side:
                line_parts.append(f"  {padded} ")
            else:
                line_parts.append(f"{vert} {padded} ")
        
        # Right side
        if style_cfg.has_right_side:
            if has_headers and i == 0:
                line_parts.append(style_cfg.header_vertical)
            else:
                line_parts.append(style_cfg.separator_vertical)
        
        line_parts.append(comment_cfg.suffix + "\n")
        output_lines.append("".join(line_parts))
    
    # Bottom line
    if style_cfg.has_bottom_line:
        sep = _get_separator_row(
            col_widths,
            style_cfg.corner_bl, style_cfg.corner_bm, style_cfg.corner_br,
            style_cfg.separator_horizontal, comment_cfg.prefix, comment_cfg.suffix
        )
        if sep:
            output_lines.append(sep)
    
    # Comment wrapper - after
    if comment_cfg.after:
        output_lines.append(comment_cfg.after + "\n")
    
    return "".join(output_lines)


def _create_html_table(rows: List[List[str]], has_headers: bool) -> str:
    """Generate an HTML table."""
    lines = ['<table border="1" cellpadding="1" cellspacing="1" align="center">']
    
    for i, row in enumerate(rows):
        tag = "th" if (has_headers and i == 0) else "td"
        cells = "".join(f"<{tag}>{cell}</{tag}>" for cell in row)
        lines.append(f"  <tr>{cells}</tr>")
    
    lines.append("</table>")
    return "\n".join(lines)


def from_csv(
    csv_text: str,
    delimiter: str = ",",
    **kwargs
) -> str:
    """
    Create a table from CSV text.
    
    Args:
        csv_text: CSV-formatted string.
        delimiter: CSV delimiter character.
        **kwargs: Additional arguments passed to create_table().
    
    Returns:
        Formatted table string.
    """
    reader = csv.reader(StringIO(csv_text), delimiter=delimiter)
    data = list(reader)
    return create_table(data, **kwargs)


def from_csv_file(
    filepath: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
    **kwargs
) -> str:
    """
    Create a table from a CSV file.
    
    Args:
        filepath: Path to CSV file.
        delimiter: CSV delimiter character.
        encoding: File encoding.
        **kwargs: Additional arguments passed to create_table().
    
    Returns:
        Formatted table string.
    """
    with open(filepath, "r", encoding=encoding) as f:
        reader = csv.reader(f, delimiter=delimiter)
        data = list(reader)
    return create_table(data, **kwargs)


def print_styles_demo():
    """Print a demonstration of all available table styles."""
    demo_data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "Los Angeles"],
    ]
    
    print("=" * 60)
    print("TEXT TABLE STYLES DEMO")
    print("=" * 60)
    
    for style in TableStyle:
        print(f"\n### {style.value.upper()} ###\n")
        print(create_table(demo_data, style=style, has_headers=True))


def main():
    """CLI entry point for text table generation."""
    parser = argparse.ArgumentParser(
        description="Generate formatted text tables from CSV data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read from file
  python -m src.utils.text_table data.csv --style mysql --headers
  
  # Read from stdin
  cat data.csv | python -m src.utils.text_table --style gfm --headers
  
  # Tab-separated input
  python -m src.utils.text_table data.tsv --delimiter $'\\t' --style unicode
  
  # Show all available styles
  python -m src.utils.text_table --demo

Available styles:
  mysql, separated, compact, rounded, girder, bubbles, dots,
  gfm (GitHub), reddit, rst_grid, rst_simple, jira, mediawiki,
  unicode, unicode_single, html, plain

Comment styles:
  none, double_slash (//), hash (#), double_dash (--),
  docblock (/**), percent (%), slash_star (/* */), xml (<!-- -->)
"""
    )
    
    parser.add_argument(
        "input",
        nargs="?",
        help="Input CSV file (reads from stdin if not provided)"
    )
    parser.add_argument(
        "-s", "--style",
        default="mysql",
        help="Table style (default: mysql)"
    )
    parser.add_argument(
        "-H", "--headers",
        action="store_true",
        help="First row contains headers"
    )
    parser.add_argument(
        "-d", "--delimiter",
        default=",",
        help="CSV delimiter (default: comma)"
    )
    parser.add_argument(
        "-a", "--align",
        choices=["left", "right", "center", "auto"],
        default="auto",
        help="Text alignment (default: auto)"
    )
    parser.add_argument(
        "-c", "--comment",
        default="none",
        help="Comment wrapper style (default: none)"
    )
    parser.add_argument(
        "--spreadsheet",
        action="store_true",
        help="Add row numbers and column letters"
    )
    parser.add_argument(
        "--no-trim",
        action="store_true",
        help="Don't trim whitespace from cells"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Show demonstration of all styles"
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="File encoding (default: utf-8)"
    )
    
    args = parser.parse_args()
    
    if args.demo:
        print_styles_demo()
        return
    
    # Read input
    if args.input:
        with open(args.input, "r", encoding=args.encoding) as f:
            csv_text = f.read()
    else:
        if sys.stdin.isatty():
            print("Reading from stdin (Ctrl+D to finish)...", file=sys.stderr)
        csv_text = sys.stdin.read()
    
    if not csv_text.strip():
        print("Error: No input data provided", file=sys.stderr)
        sys.exit(1)
    
    # Parse CSV
    reader = csv.reader(StringIO(csv_text), delimiter=args.delimiter)
    data = list(reader)
    
    # Generate table
    try:
        result = create_table(
            data,
            style=args.style,
            has_headers=args.headers,
            spreadsheet_style=args.spreadsheet,
            align=args.align,
            comment_style=args.comment,
            trim_cells=not args.no_trim,
        )
        print(result, end="")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
