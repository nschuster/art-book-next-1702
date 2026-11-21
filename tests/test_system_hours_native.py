"""Actual pinned parser probes, not a Python expression emulator.

Set SYSTEM_HOURS_NATIVE_PROBE to the rebuilt unchanged MathExpr/HtmlColor binary.
The input strings below are explicit source-format fixtures, NOT live library data.
"""
import os
import subprocess
import pytest

PROBE = os.environ.get('SYSTEM_HOURS_NATIVE_PROBE')
pytestmark = pytest.mark.skipif(not PROBE, reason='set SYSTEM_HOURS_NATIVE_PROBE to pinned C++ parser probe')

@pytest.mark.parametrize('binding,expected', [(None,'0h 0m'),('', '0h 0m'),('00:01','00:01'),('00:59','00:59'),('01:00','01:00'),('59:59','59:59'),('01:00:00','01:00:00'),('23:59:59','23:59:59'),('01:00:00:00','01:00:00:00'),('02:03:04:05','02:03:04:05'),('100:01:02:03','100:01:02:03')])
def test_native_old_binding_is_not_hours_conversion(binding, expected):
    substitution = '' if binding is None else '"'+binding+'"'
    expression = f'empty( {substitution} ) ? "0h 0m" : {substitution}'
    assert subprocess.check_output([PROBE, expression], text=True).strip() == expected

@pytest.mark.parametrize('expression', ['substr("02:03:04:05",0,2)', 'split("02:03:04:05",":")', 'replace("02:03:04:05",":"," ")', 'tointeger("02:03:04:05")'])
def test_native_no_substring_split_replace_or_colon_to_integer(expression):
    assert subprocess.check_output([PROBE, expression], text=True).startswith('ERROR: Unknown ')
