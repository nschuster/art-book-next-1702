"""Private first-run setup should not need hand-edited JSON."""
import subprocess
import tempfile
from pathlib import Path
import unittest
import json
import importlib.util
from test_metadata import ROOT

class SetupTests(unittest.TestCase):
    def test_setup_autodiscovers_systems_and_keeps_existing_config(self):
        path=ROOT/'scripts/retroachievements/configure.py'
        self.assertTrue(path.exists(), 'Interactive setup is missing')
        spec=importlib.util.spec_from_file_location('ra_configure',path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'roms/snes').mkdir(parents=True)
            (root/'roms/snes/gamelist.xml').write_text('<gameList/>')
            cfg=mod.configure(root,'sample-user','fixture-secret','hardcore')
            data=json.loads(cfg.read_text())
            self.assertEqual(data['systems'],['snes'])
            self.assertEqual(data['mode'],'hardcore')
            self.assertEqual(data['template'],{})
            from test_ra_bar import helper
            sample=dict(ID=1,NumAchievements=40,NumAwardedToUser=18,NumAwardedToUserHardcore=12)
            self.assertEqual(helper.render(sample,data,root),helper.render(sample,{'mode':'hardcore'},root))
            self.assertEqual(cfg.stat().st_mode & 0o777,0o600)
            original=cfg.read_bytes()
            with self.assertRaises(FileExistsError):mod.configure(root,'other','new-key','softcore')
            self.assertEqual(cfg.read_bytes(),original)

if __name__=='__main__':unittest.main()
