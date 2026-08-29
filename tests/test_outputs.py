from pathlib import Path

import pytest

from jinjer_sans.config import DESKTOP_DIR
from jinjer_sans.qa import check_fonts


@pytest.mark.skipif(not (DESKTOP_DIR / "jinjerSans-VF.ttf").is_file(), reason="font outputs not built")
def test_built_font_contract():
    check_fonts()
