"""Run shipped expression through an independently compiled pinned MathExpr probe.
Usage: python tools/check_playtime_parser.py /tmp/playtime-probe/probe
See docs/QA.md. No Python expression emulator; integer math is only the oracle.
"""
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


def check(probe):
    root = Path(__file__).resolve().parents[1]
    node = ET.parse(root/'aspect-ratio-4-3.xml').find(".//text[@name='game-gametime-totalhours']/text")
    expression = node.text
    cases = [0, 59, 60, 3599, 3600, 9300, 86400, 172800, 177300, 3599999]
    for seconds in cases:
        actual = subprocess.check_output([str(probe), expression.replace('{game:gametime}', str(seconds))], text=True).strip()
        expected = f'{seconds//3600}h {(seconds//60)%60}m'
        assert actual == expected, (seconds, actual, expected)
        print(f'{seconds}: {actual} PASS')
    # Explicit accepted precision limitation; not an exactness assertion.
    actual = subprocess.check_output([str(probe), expression.replace('{game:gametime}', '16777259')], text=True).strip()
    assert actual == '4660h 21m', actual
    print('16777259: 4660h 21m (exact: 4660h 20m); accepted float precision limit')


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve())
