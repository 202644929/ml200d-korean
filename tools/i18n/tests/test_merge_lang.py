import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import merge_lang as m

def row(i, en, tr='', st='new', note='', file='a.c'):
    return {'id': i, 'file': file, 'line': '1', 'field': 'name',
            'english': en, 'translation': tr, 'status': st, 'note': note}

class T(unittest.TestCase):
    def test_merge(self):
        tmpl = [row('a.c:1:name', 'ON'), row('a.c:2:name', 'Brand new')]
        lang = [row('old:9:name', 'ON', '켬', 'translated', 'n1'), row('x:1:name', 'Gone', '없어짐', 'translated')]
        out, stats = m.merge(tmpl, lang)
        self.assertEqual([r['id'] for r in out], ['a.c:1:name', 'a.c:2:name'])  # template 순서·id 따름
        self.assertEqual((out[0]['translation'], out[0]['status'], out[0]['note']), ('켬', 'translated', 'n1'))
        self.assertEqual((out[1]['translation'], out[1]['status']), ('', 'new'))
        self.assertEqual(stats, {'kept': 1, 'new': 1, 'dropped': 1})

    def test_first_nonempty_translation_wins(self):
        lang = [row('1', 'ON', '', 'new'), row('2', 'ON', '켬', 'translated'), row('3', 'ON', '켜짐', 'translated')]
        out, _ = m.merge([row('t', 'ON')], lang)
        self.assertEqual(out[0]['translation'], '켬')

    def test_real_translation_beats_identity(self):
        # different files -> falls to the global-english tier
        lang = [row('id1', 'ON', 'ON', 'translated', file='x.c'), row('id2', 'ON', '켬', 'translated', file='y.c')]
        out, _ = m.merge([row('new', 'ON', file='z.c')], lang)
        self.assertEqual(out[0]['translation'], '켬')

    def test_identity_fallback(self):
        out, _ = m.merge([row('new', 'ON', file='z.c')], [row('id1', 'ON', 'ON', 'translated', file='x.c')])
        self.assertEqual(out[0]['translation'], 'ON')

    def test_id_match_wins(self):
        tmpl = [row('id1', 'OFF'), row('id2', 'OFF')]
        lang = [row('id1', 'OFF', '끔', 'translated'), row('id2', 'OFF', '꺼짐', 'translated')]
        out, _ = m.merge(tmpl, lang)
        self.assertEqual([r['translation'] for r in out], ['끔', '꺼짐'])

    def test_id_with_different_english_is_not_matched(self):
        # line numbers shifted: same id now holds another string
        tmpl = [row('a.c:5:name', 'Other'), row('a.c:9:name', 'Start')]
        lang = [row('a.c:5:name', 'Start', '시작', 'translated')]
        out, _ = m.merge(tmpl, lang)
        self.assertEqual([r['translation'] for r in out], ['', '시작'])

    def test_drift_in_same_file_keeps_alternate(self):
        tmpl = [row('a.c:6:name', 'Waveform', file='a.c')]
        lang = [row('b.c:1:name', 'Waveform', '파형', 'translated', file='b.c'),
                row('a.c:5:name', 'Waveform', '웨이브폼', 'translated', file='a.c')]
        out, stats = m.merge(tmpl, lang)
        self.assertEqual(out[0]['translation'], '웨이브폼')
        self.assertEqual(stats['dropped'], 1)  # '파형' has no row left to live in

    def test_drift_keeps_occurrence_order(self):
        tmpl = [row('a.c:11:name', 'ON'), row('a.c:12:name', 'ON')]
        lang = [row('a.c:5:name', 'ON', 'ON', 'translated'), row('a.c:6:name', 'ON', '켬', 'translated')]
        out, stats = m.merge(tmpl, lang)
        self.assertEqual([r['translation'] for r in out], ['ON', '켬'])
        self.assertEqual(stats['dropped'], 0)

    def test_dropped_counts_truly_lost_translation(self):
        out, stats = m.merge([row('a.c:5:name', 'Other')], [row('a.c:5:name', 'Start', '시작', 'translated')])
        self.assertEqual(out[0]['translation'], '')
        self.assertEqual(stats['dropped'], 1)

    def test_no_false_drop_when_translation_survives(self):
        # old a.c row has no template twin, but the same translation lives on in b.c
        tmpl = [row('b.c:1:name', 'Start', file='b.c')]
        lang = [row('a.c:1:name', 'Start', '시작', 'translated', file='a.c'),
                row('b.c:1:name', 'Start', '시작', 'translated', file='b.c')]
        _, stats = m.merge(tmpl, lang)
        self.assertEqual(stats['dropped'], 0)

class CliEmptyTemplate(unittest.TestCase):
    def test_empty_or_missing_template_aborts_and_keeps_lang(self):
        import subprocess, tempfile
        script = os.path.join(os.path.dirname(__file__), '..', 'merge_lang.py')
        with tempfile.TemporaryDirectory() as d:
            lang_csv = os.path.join(d, 'xx.csv')
            before = ('id,file,line,field,english,translation,status,note\n'
                      'a:1:n,a.c,1,name,ON,켬,translated,\n').encode('utf-8')
            with open(lang_csv, 'wb') as f:
                f.write(before)
            empty = os.path.join(d, 'empty.csv')
            with open(empty, 'w', encoding='utf-8') as f:
                f.write('id,file,line,field,english,translation,status,note\n')
            for tmpl in (empty, os.path.join(d, 'missing.csv')):
                p = subprocess.run([sys.executable, script, '--lang', 'xx', '--lang-dir', d,
                                    '--template', tmpl], capture_output=True, text=True)
                self.assertNotEqual(p.returncode, 0)
                self.assertIn(tmpl, p.stderr)
                with open(lang_csv, 'rb') as f:
                    self.assertEqual(f.read(), before)
                self.assertEqual(sorted(os.listdir(d)), ['empty.csv', 'xx.csv'])

if __name__ == '__main__':
    unittest.main()
