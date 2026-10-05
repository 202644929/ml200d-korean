import os, subprocess, sys, tempfile, textwrap, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import gen_strings as g

HDR = 'id,file,line,field,english,translation,status,note\n'

def write(d, name, body):
    p = os.path.join(d, name)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(HDR + textwrap.dedent(body))
    return p

class T(unittest.TestCase):
    def test_pairs_dedupe_and_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, 'xx.csv', '''\
                1,a.c,1,name,ON,켬,translated,
                2,b.c,2,name,ON,켬,translated,
                3,c.c,3,name,OFF,끔,translated,
                4,d.c,4,name,OFF,꺼짐,translated,
                5,e.c,5,name,Same,Same,translated,
                6,f.c,6,name,Empty,,new,
                ''')
            pairs, conflicts = g.load_pairs(p)
            self.assertEqual(pairs, {'ON': '켬', 'OFF': '끔'})
            self.assertEqual(conflicts, [('OFF', '끔', '꺼짐')])

    def test_escape(self):
        self.assertEqual(g.c_escape('a"b'), 'a\\"b')
        self.assertEqual(g.c_escape('x\\ny'), 'x\\ny')      # 의도한 \n 유지
        self.assertEqual(g.c_escape('c:\\d'), 'c:\\\\d')
        self.assertEqual(g.c_escape('l1\nl2'), 'l1\\nl2')   # 진짜 줄바꿈은 \n으로

    def test_render_sorted_by_utf8_bytes(self):
        src = g.render_c('ko', sorted({'b': 'B', 'a': 'A', 'é': 'E'}.items(), key=lambda kv: kv[0].encode()))
        self.assertLess(src.index('{"a"'), src.index('{"b"'))
        self.assertLess(src.index('{"b"'), src.index('{"é"'))
        self.assertIn('const char* i18n_tr(const char* en)', src)
        self.assertIn('rbf_font_has_ext_glyphs', src)

    def test_en_is_passthrough(self):
        src = g.render_c('en', [])
        self.assertIn('const char* i18n_tr(const char* en)', src)
        self.assertNotIn('i18n_table[]', src)       # 길이 0 배열 금지

    def test_cli_writes_only_when_changed(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, 'xx.csv', '1,a.c,1,name,ON,켬,translated,\n')
            out = os.path.join(d, 'out.c')
            cmd = [sys.executable, g.__file__, '--lang', 'xx', '--csv-dir', d, '--out', out]
            subprocess.run(cmd, check=True)
            os.utime(out, (1, 1))
            subprocess.run(cmd, check=True)
            self.assertEqual(os.stat(out).st_mtime, 1)

    def test_cli_unknown_lang_fails(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, g.__file__, '--lang', 'zz', '--csv-dir', d,
                                '--out', os.path.join(d, 'o.c')], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('zz.csv', r.stderr)

if __name__ == '__main__':
    unittest.main()
