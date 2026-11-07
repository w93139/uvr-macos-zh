import json
from pathlib import Path

import pytest

from uvr_zh.hook import Translator


def catalog():
    return json.loads((Path(__file__).parents[1] / "uvr_zh/translations.json").read_text(encoding="utf-8"))


def test_exact_text_whitespace_and_dynamic_duration():
    translate = Translator({"Select Input": "选择歌曲", "Sample Mode": "试听模式"})
    assert translate("  Select Input\n") == "  选择歌曲\n"
    assert translate("SELECT INPUT") == "选择歌曲"
    assert translate("Sample Mode (15s)") == "试听模式（15秒）"
    for original in ["my Select Input song.wav", "/Users/example/Select Input.wav", "UVR_MDXNET_KARA_2.onnx", 0, None]:
        assert translate(original) == original


def test_ambiguous_case_is_not_guessed():
    translate = Translator({"A": "甲", "a": "乙"})
    assert translate("A") == "甲" and translate("a") == "乙"


def test_catalog_is_valid_and_has_core_ui():
    translate = Translator(catalog())
    for english in ["Select Input", "Select Output", "Start Processing", "Stop", "Settings"]:
        assert translate(english) != english
    assert translate("UVR-MDX-NET-Inst_HQ_3.onnx") == "UVR-MDX-NET-Inst_HQ_3.onnx"


def test_real_tk_display_changes_but_model_path_and_control_values_do_not():
    import tkinter as tk
    from tkinter import ttk
    from uvr_zh.hook import install

    root = tk.Tk()
    root.withdraw()
    try:
        install({"Start Processing": "开始处理", "Stop": "停止", "Select Input": "选择歌曲", "Settings": "设置", "Enabled": "启用"})
        source = tk.StringVar(master=root, value="Start Processing")
        button = ttk.Button(root, textvariable=source)
        shown = str(button.cget("textvariable"))
        assert root.getvar(shown) == "开始处理"
        assert source.get() == "Start Processing"
        source.set("Stop")
        assert root.getvar(shown) == "停止" and source.get() == "Stop"
        # Reconfiguration reuses one trace rather than leaking callbacks.
        for _ in range(4):
            button.configure(textvariable=source)
        assert len(source.trace_info()) == 1
        combo_var = tk.StringVar(master=root, value="UVR_MDXNET_KARA_2.onnx")
        combo = ttk.Combobox(root, textvariable=combo_var, values=("UVR_MDXNET_KARA_2.onnx", "Enabled"))
        assert str(combo.cget("textvariable")) == str(combo_var)
        assert combo.get() == "UVR_MDXNET_KARA_2.onnx"
        assert tuple(combo.cget("values")) == ("UVR_MDXNET_KARA_2.onnx", "Enabled")
        path_var = tk.StringVar(master=root, value="/tmp/Select Input.wav")
        entry = ttk.Entry(root, textvariable=path_var)
        assert entry.get() == path_var.get()
        selected = tk.BooleanVar(master=root, value=False)
        check = ttk.Checkbutton(root, text="Enabled", variable=selected)
        assert check.cget("text") == "启用" and selected.get() is False
        check.invoke()
        assert selected.get() is True
        notebook = ttk.Notebook(root)
        page = ttk.Frame(notebook)
        notebook.add(page, text="Settings")
        assert notebook.tab(page, "text") == "设置"
        menu = tk.Menu(root, tearoff=False)
        calls = []
        menu.add_command(label="Select Input", command=lambda: calls.append("original command"))
        assert menu.entrycget(0, "label") == "选择歌曲"
        menu.invoke(0)
        assert calls == ["original command"]
        button.destroy()
        assert source.trace_info() == []
        source.set("Start Processing")
        assert source.get() == "Start Processing"
    finally:
        root.destroy()
