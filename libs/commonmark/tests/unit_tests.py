from __future__ import unicode_literals

import unittest

try:
    from hypothesis import given, example
except ImportError:
    # Mock out hypothesis stuff for python 2.6
    def given(a):
        def func(b):
            return
        return func

    example = given

try:
    from hypothesis.strategies import text
except ImportError:
    def text():
        pass


import commonmark
from commonmark.blocks import Parser
from commonmark.render.html import HtmlRenderer
from commonmark.inlines import InlineParser
from commonmark.node import NodeWalker, Node


class TestCommonmark(unittest.TestCase):
    def test_output(self):
        s = commonmark.commonmark('*hello!*')
        self.assertEqual(s, '<p><em>hello!</em></p>\n')

    def test_unicode(self):
        s = commonmark.commonmark('<div>\u2020</div>\n')
        self.assertEqual(s, '<div>\u2020</div>\n',
                         'Unicode works in an HTML block.')
        commonmark.commonmark('* unicode: \u2020')
        commonmark.commonmark('# unicode: \u2020')
        commonmark.commonmark('```\n# unicode: \u2020\n```')

    def test_null_string_bug(self):
        s = commonmark.commonmark('>     sometext\n>\n\n')
        self.assertEqual(
            s,
            '<blockquote>\n<pre><code>sometext\n</code></pre>'
            '\n</blockquote>\n')

    def test_normalize_contracts_text_nodes(self):
        md = '_a'
        ast = Parser().parse(md)

        def assert_text_literals(text_literals):
            walker = ast.walker()
            document, _ = walker.next()
            self.assertEqual(document.t, 'document')
            paragraph, _ = walker.next()
            self.assertEqual(paragraph.t, 'paragraph')
            for literal in text_literals:
                text, _ = walker.next()
                self.assertEqual(text.t, 'text')
                self.assertEqual(text.literal, literal)
            paragraph, _ = walker.next()
            self.assertEqual(paragraph.t, 'paragraph')

        assert_text_literals(['_', 'a'])
        ast.normalize()
        # assert text nodes are contracted
        assert_text_literals(['_a'])
        ast.normalize()
        # assert normalize() doesn't alter a normalized ast
        assert_text_literals(['_a'])

    def test_dumpAST_orderedlist(self):
        md = '1.'
        ast = Parser().parse(md)
        commonmark.dumpAST(ast)

    @given(text())
    def test_random_text(self, s):
        commonmark.commonmark(s)

    def test_smart_dashes(self):
        md = 'a - b -- c --- d ---- e ----- f'
        EM = '\u2014'
        EN = '\u2013'
        expected_html = (
            '<p>'
            + 'a - '
            + 'b ' + EN + ' '
            + 'c ' + EM + ' '
            + 'd ' + EN + EN + ' '
            + 'e ' + EM + EN + ' '
            + 'f</p>\n')
        parser = commonmark.Parser(options=dict(smart=True))
        ast = parser.parse(md)
        renderer = commonmark.HtmlRenderer()
        html = renderer.render(ast)
        self.assertEqual(html, expected_html)

    def test_regex_vulnerability_link_label(self):
        i = 200
        while i <= 2000:
            s = commonmark.commonmark('[' + ('\\' * i) + '\n')
            self.assertEqual(s, '<p>' + '[' + ('\\' * (i // 2)) + '</p>\n',
                             '[\\\\... %d deep' % (i,))
            i *= 10

    def test_regex_vulnerability_link_destination(self):
        i = 200
        while i <= 2000:
            s = commonmark.commonmark(('[](' * i) + '\n')
            self.assertEqual(s, '<p>' + ('[](' * i) + '</p>\n',
                             '[]( %d deep' % (i,))
            i *= 10


class TestHtmlRenderer(unittest.TestCase):
    def test_init(self):
        HtmlRenderer()


class TestInlineParser(unittest.TestCase):
    def test_init(self):
        InlineParser()


class TestNode(unittest.TestCase):
    def test_doc_node(self):
        Node('document', [[1, 1], [0, 0]])


class TestNodeWalker(unittest.TestCase):
    def test_node_walker(self):
        node = Node('document', [[1, 1], [0, 0]])
        NodeWalker(node)

    def test_node_walker_iter(self):
        node = Node('document', [[1, 1], [0, 0]])
        for subnode, entered in node.walker():
            pass


class TestParser(unittest.TestCase):
    def setUp(self):
        self.parser = Parser()

    @given(text())
    @example('')
    @example('* unicode: \u2020')
    def test_text(self, s):
        self.parser.parse(s)


if __name__ == '__main__':
    unittest.main()
