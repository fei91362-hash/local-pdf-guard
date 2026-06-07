def test_gui_module_imports():
    import pdf_guard.gui as gui

    assert callable(gui.main)

