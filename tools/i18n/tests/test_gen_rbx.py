import os, subprocess, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import gen_rbx as g

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
FONTS = os.path.join(REPO, 'data', 'fonts')
GALMURI = os.path.join(REPO, '200d-ko', 'fonts', 'Galmuri11.ttf')
HDR = 'id,file,line,field,english,translation,status,note\n'

class T(unittest.TestCase):
    def test_needed_chars_reads_translation_column(self):
        rbf = g.RBF(os.path.join(FONTS, 'term12.rbf'))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'xx.csv')
            open(p, 'w', encoding='utf-8').write(HDR + '1,a.c,1,name,ON,켬 A,translated,\n')
            self.assertEqual(g.needed_chars(p, rbf), [ord('켬')])   # 'A', ' '는 RBF에 있음

    def test_missing_in_ttf(self):
        spec = (GALMURI, 0)
        self.assertEqual(g.missing_in_ttf(spec, [ord('가')]), [])
        self.assertEqual(g.missing_in_ttf(spec, [0x0E01]), [0x0E01])  # ก (태국 문자): Galmuri11엔 없음

    def test_cli_fails_on_missing_glyph(self):
        with tempfile.TemporaryDirectory() as d:
            csvd = os.path.join(d, 'lang'); os.makedirs(csvd)
            open(os.path.join(csvd, 'xx.csv'), 'w', encoding='utf-8').write(
                HDR + '1,a.c,1,name,ON,ก,translated,\n')
            r = subprocess.run([sys.executable, g.__file__, '--lang', 'xx', '--csv-dir', csvd,
                                '--out-dir', d, '--ttf', GALMURI, '--names', 'term12'],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("U+0E01", r.stderr)

    def test_cli_writes_rbx_with_magic(self):
        with tempfile.TemporaryDirectory() as d:
            csvd = os.path.join(d, 'lang'); os.makedirs(csvd)
            open(os.path.join(csvd, 'xx.csv'), 'w', encoding='utf-8').write(
                HDR + '1,a.c,1,name,ON,켬,translated,\n')
            subprocess.run([sys.executable, g.__file__, '--lang', 'xx', '--csv-dir', csvd,
                            '--out-dir', d, '--ttf', GALMURI, '--names', 'term12'], check=True)
            data = open(os.path.join(d, 'xx', 'term12.rbx'), 'rb').read()
            self.assertEqual(data[:4], b'RBX1')
            self.assertEqual(data[4] | data[5] << 8, 1)              # 글자 1개

    def test_ko_term12_matches_repo_file(self):
        # LANG_FONTS['ko']['sizes'] must pin term12 to 12px (fit() alone picks 63px for Galmuri11)
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, g.__file__, '--lang', 'ko', '--names', 'term12',
                            '--out-dir', d], check=True, capture_output=True)
            with open(os.path.join(d, 'ko', 'term12.rbx'), 'rb') as f:
                got = f.read()
        with open(os.path.join(FONTS, 'ko', 'term12.rbx'), 'rb') as f:
            self.assertEqual(got, f.read())

if __name__ == '__main__':
    unittest.main()
