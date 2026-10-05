#!/usr/bin/env python3
"""Merge tools/i18n/template.csv (fresh extract) into tools/i18n/lang/<lang>.csv.

Rows follow the template (order, id, file, line). Translations are carried
over row by row where possible (same id, then same file/field/english in
occurrence order), otherwise by english text. New strings get status=new and
an empty translation. Translations whose English text no longer exists are
dropped and reported on stderr.
"""
import argparse, csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ['id', 'file', 'line', 'field', 'english', 'translation', 'status', 'note']


def _carry(r, old):
    r['translation'], r['status'], r['note'] = old['translation'], old['status'], old['note']


def merge(template_rows, lang_rows):
    """Carry translations into template rows (each template row gets one).

    1. Same id AND same english: that lang row (guards against shifted lines).
    2. Same (file, field, english): the k-th unmatched template row takes the
       k-th unused lang row of that key, so per-row alternates survive drift.
       Rows consumed by tiers 1-2 are used once.
    3. Same english anywhere, like gen_strings: first non-empty translation
       that differs from english, else the first non-empty (identity) one.
    """
    cands = [r for r in lang_rows if r['translation']]
    by_id, by_key, by_en, identity = {}, {}, {}, {}
    for i, r in enumerate(cands):
        by_id.setdefault((r['id'], r['english']), []).append(i)
        by_key.setdefault((r['file'], r['field'], r['english']), []).append(i)
        if r['translation'] != r['english']:
            by_en.setdefault(r['english'], r)
        else:
            identity.setdefault(r['english'], r)

    used = set()

    def take(lst):
        for i in lst:
            if i not in used:
                used.add(i)
                return cands[i]
        return None

    out = [dict(t) for t in template_rows]
    matched = [None] * len(out)
    for k, r in enumerate(out):
        matched[k] = take(by_id.get((r['id'], r['english']), ()))
    for k, r in enumerate(out):
        if matched[k] is None:
            matched[k] = take(by_key.get((r['file'], r['field'], r['english']), ()))
    for k, r in enumerate(out):
        old = matched[k] or by_en.get(r['english']) or identity.get(r['english'])
        if old:
            _carry(r, old)
        else:
            r['translation'], r['status'], r['note'] = '', 'new', ''

    lost = lost_rows(out, lang_rows)
    stats = {'kept': sum(1 for r in out if r['status'] != 'new'),
             'new': sum(1 for r in out if r['status'] == 'new'),
             'dropped': len(lost)}
    return out, stats


def lost_rows(out_rows, lang_rows):
    """Lang rows whose (english, translation) pair appears in no output row."""
    carried = {(r['english'], r['translation']) for r in out_rows}
    return [r for r in lang_rows
            if r['translation'] and (r['english'], r['translation']) not in carried]


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lang', required=True)
    ap.add_argument('--template', default=os.path.join(HERE, 'template.csv'))
    ap.add_argument('--lang-dir', default=os.path.join(HERE, 'lang'))
    a = ap.parse_args()
    path = os.path.join(a.lang_dir, a.lang + '.csv')
    old = read_csv(path)
    tmpl = read_csv(a.template)
    if not tmpl:
        print('merge_lang: template has no rows (missing or empty): %s' % a.template, file=sys.stderr)
        sys.exit(1)
    out, stats = merge(tmpl, old)
    lost = lost_rows(out, old)
    for r in lost[:20]:
        print('merge_lang: lost %r -> %r (old id %s)' % (r['english'], r['translation'], r['id']), file=sys.stderr)
    if len(lost) > 20:
        print('merge_lang: ... and %d more lost' % (len(lost) - 20), file=sys.stderr)
    tmp = path + '.tmp'
    with open(tmp, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, path)
    print('merge_lang: %s kept=%d new=%d dropped=%d' % (a.lang, stats['kept'], stats['new'], stats['dropped']))


if __name__ == '__main__':
    main()
