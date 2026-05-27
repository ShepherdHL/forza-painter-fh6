from __future__ import annotations

import struct
from dataclasses import FrozenInstanceError

import pytest

from internal_classes import Color, Shape


class TestColor:
    def test_frozen_cannot_modify(self):
        c = Color(1, 2, 3, 4)
        with pytest.raises(FrozenInstanceError):
            c.r = 10

    def test_get_struct(self):
        c = Color(1, 2, 3, 4)
        assert c.get_struct() == struct.pack("BBBB", 1, 2, 3, 4)


class TestShape:
    def test_frozen_cannot_modify(self):
        s = Shape(1, 0, 0, 0, 0, 0, Color(), False)
        with pytest.raises(FrozenInstanceError):
            s.x = 100
