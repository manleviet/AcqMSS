"""Render a table Grid to booktabs LaTeX (complete float) + a Markdown pipe table (v3).

v3 house style: ``\\begin{table}[t]\\centering\\small`` ... booktabs rules only (no
``\\hline``/vertical rules), row terminator ``\\tabularnewline``, ``\\caption`` + ``\\label``
AFTER the tabular, super-columns via ``\\multicolumn`` + ``\\cmidrule(lr)``, ``\\multirow``
tier bands (supplied by the builder as leading cells), ``$x^{\\dagger}$`` non-converged
markers, ``{,}`` thousands inside math. No new packages, no ``\\resizebox``/``siunitx``.
"""
from __future__ import annotations

import re
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


# The TeX specials that must be escaped in a free-text cell (e.g. a convergence reason).
_TEX_ESC = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "$": r"\$",
            "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def _escape_tex(s: str) -> str:
    return "".join(_TEX_ESC.get(ch, ch) for ch in s)


def _int_frac(t: str):
    """(int_part, frac_or_'') if ``t`` is a plain non-negative number, else None."""
    if t.replace(".", "", 1).isdigit():
        i, _, f = t.partition(".")
        return i, f
    return None


def _latex_cell(c: Cell) -> str:
    t = c.text
    if c.raw:                                           # already-rendered LaTeX (compact P/R/F1)
        return t
    if t == MISSING:
        return "--"
    parts = _int_frac(t)
    if parts and len(parts[0]) >= 4:                    # numeric >=1000 -> math + {,} grouping
        body = "{,}".join(_group3(parts[0])) + (f".{parts[1]}" if parts[1] else "")
        inner = f"\\mathbf{{{body}}}" if c.bold else body   # bold IN math (\\textbf won't bold math)
        return f"${inner}^{{\\dagger}}$" if c.dagger else f"${inner}$"
    if c.dagger:                                        # daggered numeric -> math (bold via \\mathbf)
        inner = f"\\mathbf{{{t}}}" if c.bold else t
        return f"${inner}^{{\\dagger}}$"
    if any(ch.isalpha() for ch in t):                   # free-text label -> escape TeX specials
        t = _escape_tex(t)
    return f"\\textbf{{{t}}}" if c.bold else t


_STRIP_ZERO = re.compile(r"(?<![\d.])0\.")


def strip_zero(c: Cell) -> Cell:
    """One rate rendered without its leading zero (``0.80`` -> ``.80``), bold/dagger preserved.

    Used where a table is all rates and the leading zeros are pure noise (app-sampling); ``1.00``
    is untouched, so the reader can still tell a ceiling from a near-ceiling at a glance.
    """
    return Cell(_STRIP_ZERO.sub(".", _latex_cell(c)), False, False, True)


def prf_compact(cells: List[Cell]) -> Cell:
    """Fold P, R, F1 into ONE ``.p/.r/.f1`` cell, each sub-value keeping its own bold/dagger.

    The paper's space-saving rendering: three rates joined by ``/`` with the leading zero of a
    sub-1 value dropped (``0.85`` -> ``.85``), while ``1.00`` keeps its digit. Each sub-value is
    rendered by ``_latex_cell`` FIRST, so bolding a winner (``\\textbf{.85}``) and the
    non-converged dagger (``$.03^{\\dagger}$``) survive the fold untouched.
    """
    return Cell("/".join(_STRIP_ZERO.sub(".", _latex_cell(c)) for c in cells), False, False, True)


def _md_cell(c: Cell) -> str:
    t = c.text
    if c.raw:
        return _md_raw(t)
    if t != MISSING:
        parts = _int_frac(t)
        if parts and len(parts[0]) >= 4:
            t = ",".join(_group3(parts[0])) + (f".{parts[1]}" if parts[1] else "")
        if c.dagger:
            t = f"{t}†"
    return f"**{t}**" if c.bold else t


def latex(grid: Grid) -> str:
    env = "table*" if grid.full_width else "table"
    out = [f"\\begin{{{env}}}[t]", "\\centering", "\\small"]
    if grid.tabcolsep:
        out.append(f"\\setlength{{\\tabcolsep}}{{{grid.tabcolsep}}}")
    out += [f"\\begin{{tabular}}{{{grid.colspec}}}", "\\toprule"]
    if grid.supercols:
        # An entry with an EMPTY name is a spacer: it emits `span` blank cells and no cmidrule, so a
        # banner row can skip columns (app-sampling groups only 2 of its 11 data columns, then 4).
        # The blanks must be emitted — a short header row silently shifts every later \multicolumn
        # left of the \cmidrule that is supposed to underline it.
        head = [""] * grid.n_leading
        for name, span in grid.supercols:
            head += [""] * span if not name else [f"\\multicolumn{{{span}}}{{c}}{{{name}}}"]
        out.append(" & ".join(head) + " \\tabularnewline")
        col = grid.n_leading + 1
        rules = []
        for name, span in grid.supercols:
            if name:
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
    text = re.sub(r"\\multirow\{[^}]*\}\{[^}]*\}\{(.*)\}", r"\1", text)   # greedy: KB label has nested braces
    text = re.sub(r"\\textsc\{([^}]*)\}", r"\1", text)
    return text.replace("\\", "").strip() or " "


def _md_raw(text: str) -> str:
    """Markdown for an ALREADY-typeset cell (the compact P/R/F1 and stripped-zero rates).

    Kept separate from ``_demacro``: this one drops ``$`` and turns ``\\textbf`` into ``**``, which
    is right for a data cell but wrong for a row label, where ``$KB_{1}$`` must survive intact.
    """
    text = re.sub(r"\\(?:textbf|mathbf)\{([^}]*)\}", r"**\1**", text)
    return text.replace("^{\\dagger}", "†").replace("$", "").replace("\\", "")


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
