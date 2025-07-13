import pathlib

def test_ui_build_asset_exists():
    assert (pathlib.Path("frontend/dist/index.html")).exists()
