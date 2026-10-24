"""Regression for Batocera 42's pinned NanoSVG coordinate conversion.

The native parser treats unitless gradient endpoints as pixels even in
objectBoundingBox space; percentages are needed to span the fill bounds.
See docs/qa/ra-native-svg.md for compiled pinned-rasterizer evidence.
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from test_ra_bar import helper


class NativeSvgTests(unittest.TestCase):
    def test_gradient_spans_fill_in_native_coordinate_units(self):
        for count in (0, 1, 12, 40):
            data = dict(ID=1, NumAchievements=40, NumAwardedToUser=count,
                        NumAwardedToUserHardcore=count)
            _, content = helper.progress_asset(data, {}, Path('/userdata'))
            gradient = ET.fromstring(content).find('{*}defs/{*}linearGradient')
            assert gradient is not None
            self.assertEqual(gradient.get('x1'), '0%')
            self.assertEqual(gradient.get('x2'), '100%')
            self.assertEqual(gradient.get('y1'), '0%')
            self.assertEqual(gradient.get('y2'), '0%')
