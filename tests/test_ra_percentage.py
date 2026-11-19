import xml.etree.ElementTree as ET
import pytest
from PIL import ImageFont
from test_ra_bar import helper
from test_metadata import ROOT

@pytest.mark.parametrize('count,total,expected',[(0,0,'0 / 0 · 0%'),(12,40,'12 / 40 · 30%'),(1,3,'1 / 3 · 33%'),(2,3,'2 / 3 · 67%'),(1,8,'1 / 8 · 13%'),(40,40,'40 / 40 · 100%')])
def test_percentage_label(count,total,expected):
    data=dict(ID=1,NumAchievements=total,NumAwardedToUser=count,NumAwardedToUserHardcore=0)
    xml=ET.fromstring(helper.render(data,{'mode':'softcore'},'/userdata'))
    text=xml.find('.//text[@name="ra_progress"]')
    assert text.findtext('text')==expected
    assert text.findtext('size')=='0.34 0.045833333333333'
    hard=ET.fromstring(helper.render(data,{'mode':'hardcore'},'/userdata'))
    assert hard.findtext('.//text[@name="ra_progress"]/text')==f'0 / {total} · 0%'

def test_percentage_text_fits_at_both_sizes():
    for w,h in [(640,480),(320,240)]:
        font=ImageFont.truetype(str(ROOT/'_inc/fonts/Roboto-Bold.ttf'),int(int(h*.027777777777777)*1.31))
        assert font.getlength('9999 / 9999 · 100%') < .34*w
