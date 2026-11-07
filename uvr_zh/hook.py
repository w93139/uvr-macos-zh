"""Translate Tk display options without changing UVR's underlying values.

This file is installed as a PyInstaller runtime hook immediately before UVR.
It deliberately leaves entries, combobox values and configuration variables alone.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


class Translator:
    def __init__(self, translations):
        if not isinstance(translations, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and k and v
            for k, v in translations.items()
        ):
            raise ValueError("Translations must be a non-empty-string mapping")
        self.exact = dict(translations)
        folded = {}
        ambiguous = set()
        for key, value in translations.items():
            folded_key = key.casefold()
            if folded_key in folded and folded[folded_key] != value:
                ambiguous.add(folded_key)
            folded[folded_key] = value
        self.folded = {k: v for k, v in folded.items() if k not in ambiguous}

    def __call__(self, value):
        if not isinstance(value, str) or not value.strip():
            return value
        core = value.strip()
        translated = self.exact.get(core, self.folded.get(core.casefold()))
        if translated is None:
            match = re.fullmatch(r"Sample Mode\s*\((\d+(?:\.\d+)?)(s| Seconds)\)", core)
            if match:
                translated = f"试听模式（{match[1]}秒）"
        if translated is None:
            return value
        left = value[: len(value) - len(value.lstrip())]
        right = value[len(value.rstrip()) :]
        return left + translated + right


def install(translations):
    import tkinter as tk
    from tkinter import ttk

    if getattr(tk, "_uvr_zh_installed", False):
        return
    translate = Translator(translations)
    original_options = tk.Misc._options
    original_destroy = tk.Misc.destroy
    original_title = tk.Wm.wm_title
    # No Entry, Spinbox, Scale, Listbox or Combobox: their values are user data.
    display_widgets = (
        tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.Menubutton,
        tk.Message, ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton,
        ttk.Menubutton,
    )

    def release_proxy(widget):
        info = getattr(widget, "_uvr_zh_proxy", None)
        if info is None:
            return
        widget._uvr_zh_proxy = None
        source, command, proxy = info
        try:
            widget.tk.call("trace", "remove", "variable", source, "write", command)
        except tk.TclError:
            pass
        try:
            widget.deletecommand(command)
        except tk.TclError:
            pass
        # Drop our reference only after the source trace is gone.
        del proxy

    def display_variable(widget, variable):
        if not variable:
            release_proxy(widget)
            return variable
        name = str(variable)
        old = getattr(widget, "_uvr_zh_proxy", None)
        if old and name in (old[0], str(old[2])):
            return old[2]
        release_proxy(widget)
        try:
            initial = widget.tk.globalgetvar(name)
        except tk.TclError:
            return variable
        proxy = tk.StringVar(master=widget, value=translate(initial))

        def update(*_):
            try:
                proxy.set(translate(widget.tk.globalgetvar(name)))
            except tk.TclError:
                pass

        command = widget._register(update)
        widget.tk.call("trace", "add", "variable", name, "write", command)
        widget._uvr_zh_proxy = (name, command, proxy)
        return proxy

    def options(widget, cnf, kw=None):
        merged = dict(tk._cnfmerge(cnf) or {})
        if kw:
            merged.update(kw)
        for key in ("text", "label", "title", "message", "detail"):
            if key in merged:
                merged[key] = translate(merged[key])
        if "textvariable" in merged and isinstance(widget, display_widgets):
            merged["textvariable"] = display_variable(widget, merged["textvariable"])
        return original_options(widget, merged)

    def destroy(widget):
        release_proxy(widget)
        return original_destroy(widget)

    def title(widget, string=None):
        return original_title(widget, translate(string) if string is not None else None)

    tk.Misc._options = options
    tk.Misc.destroy = destroy
    tk.Wm.wm_title = title
    tk.Wm.title = title
    # ttk Notebook methods format their options without Misc._options.
    def notebook_method(original):
        def translated(widget, *args, **kwargs):
            if "text" in kwargs:
                kwargs["text"] = translate(kwargs["text"])
            return original(widget, *args, **kwargs)
        return translated

    for name in ("add", "insert", "tab"):
        setattr(ttk.Notebook, name, notebook_method(getattr(ttk.Notebook, name)))
    tk._uvr_zh_installed = True


def activate():
    resources = Path(sys.executable).resolve().parents[1] / "Resources" / "uvr_zh"
    translations = json.loads((resources / "translations.json").read_text(encoding="utf-8"))
    install(translations)


if getattr(sys, "frozen", False):
    activate()
