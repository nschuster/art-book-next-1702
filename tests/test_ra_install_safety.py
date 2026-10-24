"""Installer must preflight every output before creating hooks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_metadata import ROOT

class InstallSafetyTests(unittest.TestCase):
    def test_symlink_example_does_not_leave_partial_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            state=root/'system/retroachievements';state.mkdir(parents=True)
            outside=root/'unrelated.json';outside.write_text('untouched')
            (state/'config.example.json').symlink_to(outside)
            p=subprocess.run([sys.executable,str(ROOT/'scripts/retroachievements/install.py'),'--data-root',str(root)],capture_output=True,text=True)
            self.assertNotEqual(p.returncode,0)
            self.assertFalse((root/'system/scripts/ra-progress-sync.sh').exists())
            self.assertFalse((state/'install-manifest.json').exists())
            self.assertEqual(outside.read_text(),'untouched')

if __name__=='__main__':unittest.main()
