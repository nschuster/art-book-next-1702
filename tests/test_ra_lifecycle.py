"""Progress must never silently belong to a previous account/game mapping."""
import unittest
import test_ra_sync as fixture

class LifecycleTests(unittest.TestCase):
    setUp=fixture.SyncTests.setUp
    tearDown=fixture.SyncTests.tearDown
    save=fixture.SyncTests.save
    run_sync=fixture.SyncTests.run_sync
    output=fixture.SyncTests.output

    def test_account_change_offline_removes_previous_accounts_display(self):
        self.assertEqual(self.run_sync().returncode,0)
        self.cfg['username']='other-user';self.save();self.status=503
        self.assertEqual(self.run_sync('--force').returncode,1)
        self.assertFalse(self.output().exists())

    def test_removed_mapping_prunes_owned_extra_only(self):
        self.assertEqual(self.run_sync().returncode,0)
        unrelated=self.output().parent/'unrelated.xml';unrelated.write_text('user file')
        self.maps=[];self.save()
        self.assertEqual(self.run_sync().returncode,0)
        self.assertFalse(self.output().exists())
        self.assertEqual(unrelated.read_text(),'user file')

    def test_remapping_offline_removes_previous_game_display(self):
        self.assertEqual(self.run_sync().returncode,0)
        self.maps[0]['game_id']=2;self.save();self.status=503
        self.assertEqual(self.run_sync('--force').returncode,1)
        self.assertFalse(self.output().exists())

    def test_targeted_refresh_does_not_prune_other_games(self):
        self.maps.append({'system':'snes','rom':'Other.sfc','game_id':1});self.save()
        self.assertEqual(self.run_sync().returncode,0)
        other=self.output().parent/'Other.xml';original=other.read_bytes()
        self.assertEqual(self.run_sync('--system','snes','--rom','./A & B.sfc','--force').returncode,0)
        self.assertEqual(other.read_bytes(),original)

if __name__=='__main__':unittest.main()
