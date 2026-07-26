"""Render a table Grid to booktabs LaTeX (complete float) + a Markdown pipe table (v3).

v3 house style: ``\\begin{table}[t]\\centering\\small`` ... booktabs rules only (no
``\\hline``/vertical rules), row terminator ``\\tabularnewline``, ``\\caption`` + ``\\label``
AFTER the tabular, super-columns via ``\\multicolumn`` + ``\\cmidrule(lr)``, ``\\multirow``
tier bands (supplied by the builder as leading cells), ``$x^{\\dagger}$`` non-converged
markers, ``{,}`` thousands inside math. No new packages, no ``\\resizebox``/``siunitx``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .formatting import Cell, MISSING


@dataclass
class BodyRow:
    leading: List[str]              # raw-LaTeX leading cells (row/tier labels, \multirow, ...)
    cells: List[Cell]              # data cells
    rule_before: bool = False       # emit a \midrule before this row (KB-block separator)


@dataclass
class Grid:
    label: str                      # \label sans 'tab:'; also the filename stem
    caption: str
    colspec: str                    # e.g. 'lccccc'
    headers: List[str]              # full header row (leading + data), raw-LaTeX ok
    body: List[BodyRow]
    supercols: Optional[List[Tuple[str, int]]] = None   # (name, span) over the DATA cols
    n_leading: int = 1              # number of leading (non-data) columns
    full_width: bool = False        # -> table*
    tabcolsep: Optional[str] = None # e.g. '4pt' for wide tables


def _group3(digits: str) -> List[str]:
    parts, s = [], digits
    while len(s) > 3:
        parts.insert(0, s[-3:])
        s = s[:-3]
    parts.insert(0, s)
    return parts


def _latex_cell(c: Cell) -> str:
    t = c.text
    if t == MISSING:
        return "--"
    if t.isdigit() and len(t) >= 4:                 # thousands grouping inside math
        t = "$" + "{,}".join(_group3(t)) + "$"
    elif c.dagger:
        t = f"${t}^{{\\dagger}}$"
    elif any(ch.isalpha() for ch in t):             # text label (e.g. a convergence reason)
        t = t.replace("_", "\\_")
    return f"\\textbf{{{t}}}" if c.bold else t


def _md_cell(c: Cell) -> str:
    t = c.text
    if t != MISSING and t.isdigit() and len(t) >= 4:
        t = ",".join(_group3(t))
    elif c.dagger:
        t = f"{t}†"
    return f"**{t}**" if c.bold else t


def latex(grid: Grid) -> str:
    env = "table*" if grid.full_width else "table"
    out = [f"\\begin{{{env}}}[t]", "\\centering", "\\small"]
    if grid.tabcolsep:
        out.append(f"\\setlength{{\\tabcolsep}}{{{grid.tabcolsep}}}")
    out += [f"\\begin{{tabular}}{{{grid.colspec}}}", "\\toprule"]
    if grid.supercols:
        head = [""] * grid.n_leading + [f"\\multicolumn{{{span}}}{{c}}{{{name}}}"
                                        for name, span in grid.supercols]
        out.append(" & ".join(head) + " \\tabularnewline")
        col = grid.n_leading + 1
        rules = []
        for _, span in grid.supercols:
            rules.append(f"\\cmidrule(lr){{{col}-{col + span - 1}}}")
            col += span
        out.append(" ".join(rules))
    out.append(" & ".join(grid.headers) + " \\tabularnewline")
    out.append("\\midrule")
    for row in grid.body:
        if row.rule_before:
            out.append("\\midrule")
        out.append(" & ".join(row.leading + [_latex_cell(c) for c in row.cells]) + " \\tabularnewline")
    out += ["\\bottomrule", "\\end{tabular}", f"\\caption{{{grid.caption}}}",
            f"\\label{{tab:{grid.label}}}", f"\\end{{{env}}}", ""]
    return "\n".join(out)


def _demacro(text: str) -> str:
    """Best-effort strip of LaTeX leading-cell macros for the Markdown reading aid."""
    import re
    text = re.sub(r"\\multirow\{[^}]*\}\{[^}]*\}\{(.*)\}", r"\1", text)   # greedy: KB label has nested braces
    text = re.sub(r"\\textsc\{([^}]*)\}", r"\1", text)
    return text.replace("\\", "").strip() or " "


def markdown(grid: Grid) -> str:
    out = [f"# {grid.label}", "", grid.caption, ""]
    if grid.supercols:
        out.append("groups: " + ", ".join(f"{_demacro(n)} (×{s})" for n, s in grid.supercols))
        out.append("")
    out.append("| " + " | ".join(_demacro(h) for h in grid.headers) + " |")
    out.append("|" + "|".join(["---"] * len(grid.headers)) + "|")
    for row in grid.body:
        cells = [_demacro(x) for x in row.leading] + [_md_cell(c) for c in row.cells]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"
