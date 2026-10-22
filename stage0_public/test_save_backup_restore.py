#!/usr/bin/env python3
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SCRIPT=ROOT/'save_backup_restore.sh';SIGNER='a'*64
ADB_STUB=r'''#!/usr/bin/env bash
set -euo pipefail
if [[ "$1" == "wait-for-device" ]]; then exit 0; fi
if [[ "$1" == "shell" && "$2" == "pm" && "$3" == "path" ]]; then echo 'package:/fake/base.apk'; exit 0; fi
if [[ "$1" == "shell" && "$2" == "getprop" ]]; then echo '14'; exit 0; fi
if [[ "$1" == "shell" && "$2" == "am" && "$3" == "force-stop" ]]; then exit 0; fi
if [[ "$1" == "shell" && "$2" == "run-as" ]]; then shift 3; if [[ "$1" == "test" && "$2" == "-f" ]]; then test -f "$FAKE_PREF"; exit $?; fi; if [[ "$1" == "mkdir" ]]; then mkdir -p "$(dirname "$FAKE_PREF")"; exit 0; fi; if [[ "$1" == "sh" && "$2" == "-c" ]]; then cat > "$FAKE_PREF"; chmod 600 "$FAKE_PREF"; exit 0; fi; fi
if [[ "$1" == "exec-out" && "$2" == "cat" ]]; then cat "$FAKE_APK"; exit 0; fi
if [[ "$1" == "exec-out" && "$2" == "run-as" ]]; then cat "$FAKE_PREF"; exit 0; fi
exit 99
'''
APKSIGNER_STUB=r'''#!/usr/bin/env bash
echo "Signer #1 certificate SHA-256 digest: ${FAKE_SIGNER}"
'''
class T(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();r=Path(self.t.name);self.pref=r/'app/shared_prefs/MonkeyGame.xml';self.pref.parent.mkdir(parents=True);self.original=b'<map><string name=".monkeystate">abc;123</string></map>\n';self.pref.write_bytes(self.original);self.apk=r/'base.apk';self.apk.write_bytes(b'x');self.adb=r/'adb';self.adb.write_text(ADB_STUB);self.adb.chmod(0o755);self.sign=r/'apksigner';self.sign.write_text(APKSIGNER_STUB);self.sign.chmod(0o755);self.env=os.environ.copy();self.env.update({'ADB':str(self.adb),'APKSIGNER':str(self.sign),'FAKE_PREF':str(self.pref),'FAKE_APK':str(self.apk),'FAKE_SIGNER':SIGNER});self.backup=r/'backup'
 def tearDown(self): self.t.cleanup()
 def runx(self,*a,check=True): return subprocess.run([str(SCRIPT),*a],env=self.env,text=True,capture_output=True,check=check)
 def test_roundtrip(self):
  r=self.runx('backup',str(self.backup));self.assertIn('BACKUP_OK',r.stdout);m=json.loads((self.backup/'metadata.json').read_text());self.assertEqual(m['save_sha256'],hashlib.sha256(self.original).hexdigest());self.pref.write_bytes(b'bad');r=self.runx('restore',str(self.backup));self.assertIn('RESTORE_OK',r.stdout);self.assertEqual(self.pref.read_bytes(),self.original)
 def test_signer_mismatch(self):
  self.runx('backup',str(self.backup));p=self.backup/'metadata.json';m=json.loads(p.read_text());m['SIGNER_SHA256']='b'*64;p.write_text(json.dumps(m));r=self.runx('restore',str(self.backup),check=False);self.assertEqual(r.returncode,8);self.assertIn('refusing restore',r.stderr.lower())
if __name__=='__main__':unittest.main()
