"""Stdlib regression tests; AST extraction avoids terminal import side effects."""
import ast
import difflib
import io
import itertools
import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

REPO = Path(__file__).resolve().parents[1]
MAIN = 'working-tree'

def blob(ref, path='demo.py'):
    return (REPO / path).read_text(encoding='utf-8')

def extracted(ref, names, namespace=None):
    tree = ast.parse(blob(ref))
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names), 'Harness extraction missing requested function'
    ns = {'difflib': difflib}
    ns.update(namespace or {})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), ref + ':extracted', 'exec'), ns)
    return ns

class Algorithms(unittest.TestCase):
    def setUp(self):
        self.versions = [(r, extracted(r, ['lev_dist', 'lev_full', 'sm_full', 'hybrid'])) for r in [MAIN]]

    def test_literal_distances_and_actual_dict_contract(self):
        cases = [('', '', 0), ('', 'abc', 3), ('abc', '', 3), ('kitten', 'sitting', 3),
                 ('ab', 'ac', 1), ('Лев', 'Лев', 0), ('abcdef', 'fedcba', 6)]
        for ref, ns in self.versions:
            for a, b, expected in cases:
                with self.subTest(ref=ref, a=a, b=b):
                    self.assertEqual(ns['lev_dist'](a, b), expected)
                    full = ns['lev_full'](a, b)
                    self.assertEqual(set(full), {'dist', 'ratio', 'matrix', 'ops', 'path'})
                    self.assertEqual(full['dist'], expected)
                    self.assertAlmostEqual(full['ratio'], 1 - expected / max(len(a), len(b), 1))
                    self.assertEqual(full['path'][0], (0, 0))
                    self.assertEqual(full['path'][-1], (len(a), len(b)))
                    cost = 0
                    for previous, current in zip(full['path'], full['path'][1:]):
                        i, j = current
                        op = full['ops'][i][j]
                        di, dj = i - previous[0], j - previous[1]
                        self.assertEqual((di, dj), {'M': (1, 1), 'S': (1, 1), 'D': (1, 0), 'I': (0, 1)}[op])
                        cost += op != 'M'
                    self.assertEqual(cost, expected)

    def test_literal_matrix_and_path(self):
        for ref, ns in self.versions:
            with self.subTest(ref=ref):
                r = ns['lev_full']('ab', 'ac')
                self.assertEqual(r['matrix'], [[0, 1, 2], [1, 0, 1], [2, 1, 1]])
                self.assertEqual(r['path'], [(0, 0), (1, 1), (2, 2)])

    def test_sm_empty_and_literal_kitten_blocks(self):
        for ref, ns in self.versions:
            with self.subTest(ref=ref):
                empty = ns['sm_full']('', '')
                self.assertEqual(set(empty), {'ratio', 'blocks', 'opcodes', 'steps'})
                self.assertEqual(empty, {'ratio': 1.0, 'blocks': [difflib.Match(0, 0, 0)],
                                        'opcodes': [], 'steps': [{'region': (0, 0, 0, 0), 'match': None}]})
                r = ns['sm_full']('kitten', 'sitting')
                self.assertAlmostEqual(r['ratio'], 8 / 13)
                self.assertEqual(r['blocks'], [difflib.Match(1, 1, 3), difflib.Match(5, 5, 1), difflib.Match(6, 7, 0)])
                self.assertEqual(r['opcodes'], [('replace', 0, 1, 0, 1), ('equal', 1, 4, 1, 4),
                                             ('replace', 4, 5, 4, 5), ('equal', 5, 6, 5, 6), ('insert', 6, 6, 6, 7)])

    def test_hybrid_literal_weights(self):
        for ref, ns in self.versions:
            for weight in [0, .5, 1]:
                with self.subTest(ref=ref, weight=weight):
                    self.assertAlmostEqual(ns['hybrid']('kitten', 'sitting', weight), weight * (4 / 7) + (1 - weight) * (8 / 13))

    def test_worked_pairs_blocks_distances_ratios_and_company_weight_sweep(self):
        ns = self.versions[0][1]
        cases = [
            ('Acme Corp.', 'ACME Corporation', 10, 6 / 13,
             [(0, 0, 1), (4, 4, 5), (10, 16, 0)]),
            ('abcdef', 'fedcba', 6, 1 / 6, [(0, 5, 1), (6, 6, 0)]),
            ('Saturday', 'Sunday', 3, 5 / 7,
             [(0, 0, 1), (3, 1, 1), (5, 3, 3), (8, 6, 0)]),
        ]
        for a, b, distance, ratio, blocks in cases:
            with self.subTest(a=a, b=b):
                result = ns['sm_full'](a, b)
                self.assertEqual(ns['lev_dist'](a, b), distance)
                self.assertAlmostEqual(result['ratio'], ratio)
                self.assertEqual(result['blocks'], [difflib.Match(*block) for block in blocks])
        self.assertEqual(
            [round(100 * ns['hybrid']('Acme Corp.', 'ACME Corporation', n / 10), 1)
             for n in range(11)],
            [46.2, 45.3, 44.4, 43.6, 42.7, 41.8, 41.0, 40.1, 39.2, 38.4, 37.5],
        )

    def test_exhaustive_small_inputs_distance_contract(self):
        words = [''] + [''.join(p) for n in range(1, 4) for p in itertools.product('ab', repeat=n)]
        ns = self.versions[0][1]
        for a, b in itertools.product(words, repeat=2):
            full = ns['lev_full'](a, b)
            self.assertEqual(ns['lev_dist'](a, b), full['dist'])
            self.assertEqual(ns['lev_dist'](a, b), ns['lev_dist'](b, a))
            self.assertLessEqual(abs(len(a) - len(b)), full['dist'])
            self.assertLessEqual(full['dist'], max(len(a), len(b)))

class Terminal(unittest.TestCase):
    def test_rkey_normal_arrow_ctrl_c_read_error_and_setraw_error_restore(self):
        cases = [('enter', ['\r'], 'ENTER', None), ('arrow', ['\x1b', '[', 'A'], 'UP', None),
                 ('char', ['x'], 'x', None), ('ctrl-c', ['\x03'], None, KeyboardInterrupt),
                 ('read-error', [OSError('read failed')], None, OSError),
                 ('setraw-error', ['x'], None, OSError)]
        for ref in [MAIN]:
            for name, reads, value, error in cases:
                with self.subTest(ref=ref, scenario=name):
                    stdin = Mock()
                    stdin.fileno.return_value = 7
                    stdin.read.side_effect = reads
                    old = object()
                    termios = types.SimpleNamespace(tcgetattr=Mock(return_value=old), tcsetattr=Mock(), TCSADRAIN=123)
                    tty = types.SimpleNamespace(setraw=Mock(side_effect=OSError('raw failed') if name == 'setraw-error' else None))
                    ns = extracted(ref, ['rkey'], {'sys': types.SimpleNamespace(stdin=stdin), 'termios': termios, 'tty': tty})
                    if error:
                        with self.assertRaises(error): ns['rkey']()
                    else:
                        self.assertEqual(ns['rkey'](), value)
                    termios.tcsetattr.assert_called_once_with(7, 123, old)

    def test_main_non_tty_never_enables_alternate_screen(self):
        for ref in [MAIN]:
            writes = Mock()
            fake_sys = types.SimpleNamespace(stdout=types.SimpleNamespace(isatty=lambda: False), stderr=io.StringIO(), exit=Mock(side_effect=SystemExit(1)))
            ns = extracted(ref, ['main'], {'sys': fake_sys, 'W': writes})
            with self.assertRaises(SystemExit) as error: ns['main']()
            self.assertEqual(error.exception.code, 1)
            writes.assert_not_called()

    def test_main_finally_normal_error_and_ctrl_c(self):
        for ref in [MAIN]:
            for phase, failure in [('splash', None), ('splash', ValueError('demo failed')),
                                   ('splash', KeyboardInterrupt()), ('menu', ValueError('demo failed')),
                                   ('menu', KeyboardInterrupt())]:
                with self.subTest(ref=ref, phase=phase, failure=type(failure).__name__):
                    writes = []
                    splash = Mock(side_effect=failure if phase == 'splash' else None)
                    menu = Mock(side_effect=failure if phase == 'menu' else None)
                    ns = extracted(ref, ['main'], {'sys': types.SimpleNamespace(stdout=types.SimpleNamespace(isatty=lambda: True)),
                        '_rsz': Mock(), 'TW': 80, 'W': writes.append, 'AON': 'AON', 'HIDE': 'HIDE',
                        'SHOW': 'SHOW', 'AOFF': 'AOFF', 'splash': splash, 'menu': menu})
                    if isinstance(failure, ValueError):
                        with self.assertRaises(ValueError): ns['main']()
                    else: ns['main']()
                    self.assertEqual(writes, ['AONHIDE', 'SHOWAOFF'])

class Documentation(unittest.TestCase):
    def vlookup(self, query, catalog, threshold):
        markdown = blob(MAIN, 'README.md')
        blocks = re.findall(r'```python\n(.*?)```', markdown, re.S)
        block, = [b for b in blocks if 'def hybrid_vlookup(' in b]
        ns = extracted(MAIN, ['lev_dist'])
        ns['levenshtein_distance'] = ns['lev_dist']
        exec(compile(ast.parse(block), 'README.md:hybrid_vlookup', 'exec'), ns)
        return ns['hybrid_vlookup'](query, catalog, threshold=threshold)

    def test_hybrid_vlookup_low_score_returns_flat_no_match(self):
        self.assertEqual(self.vlookup('a', ['ab'], .9), (None, 0))

    def test_hybrid_vlookup_high_score_returns_match_and_scalar_score(self):
        self.assertEqual(self.vlookup('abc', ['abc'], .9), ('abc', 1.0))

    def test_hybrid_vlookup_empty_catalog_returns_flat_no_match(self):
        self.assertEqual(self.vlookup('a', [], .9), (None, 0))

if __name__ == '__main__':
    unittest.main()
