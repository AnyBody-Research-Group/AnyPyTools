# -*- coding: utf-8 -*-
"""Lexer for the AnyScript modelling langue."""

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import (ascii, bytes, chr, dict, filter, hex, input,  # noqa
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)


import os

from pygments.lexer import (RegexLexer, include, bygroups,
                            default, words)
from pygments.token import (Text, Comment, Operator, Keyword, Name, String,
                            Number, Punctuation, Generic, Other)


__all__ = ['AnyScriptLexer']

_ROOT = os.path.abspath(os.path.dirname(__file__))


with open(os.path.join(_ROOT, 'classes.txt')) as f:
    ANYCLASSES = f.read().split()
with open(os.path.join(_ROOT, 'functions.txt')) as f:
    ANYFUNCTIONS = f.read().split()
with open(os.path.join(_ROOT, 'globals.txt')) as f:
    ANYGLOBALS = f.read().split()
with open(os.path.join(_ROOT, 'statements.txt')) as f:
    ANYSTATEMENTS = f.read().split()
with open(os.path.join(_ROOT, 'options.txt')) as f:
    ANYOPTIONS = f.read().split()


class AnyScriptLexer(RegexLexer):
    """
    """
    name = 'AnyScript'
    aliases = ['anyscript']
    filenames = ['*.any']

    # The trailing ?, rather than *, avoids a geometric performance drop here.
    #: only one /* */ style comment
    _ws1 = r'\s*(?:/[*].*?[*]/\s*)?'

    tokens = {
        'whitespace': [
            # # preprocessor directives: without whitespace
            # ('^#if\s+0', Comment.Preproc, 'if0'),
            # ('^#', Comment.Preproc, 'macro'),
            # # or with whitespace
            # ('^(' + _ws1 + r')(#if\s+0)',
            # bygroups(using(this), Comment.Preproc), 'if0'),
            # ('^(' + _ws1 + ')(#)',
            # bygroups(using(this), Comment.Preproc), 'macro'),
            (r'\n', Text),
            (r'\s+', Text),
            (r'\\\n', Text),  # line continuation
            (r'//(\n|(.|\n)*?[^\\]\n)', Comment.Single),
            (r'/(\\\n)?[*](.|\n)*?[*](\\\n)?/', Comment.Multiline),
        ],

        'statements': [
            # For AnyDoc highlighting
            (r'(§)(/[*])(§)((.|\n)*?)(§)([*]/)(§)',
             bygroups(Generic.Deleted, Generic.Error, Generic.Deleted, Comment.Multiline, Comment.Multiline, Generic.Deleted, Generic.Error, Generic.Deleted)),
            (r'(§)(//)(§)', bygroups(Generic.Deleted, Generic.Error,
                                     Generic.Deleted), 'multiline-directive'),
            (r'§', Generic.Deleted, 'new-codes'),
            ####################
            (words(('#if', '#ifdef', '#ifndef', '#undef', '#endif', '#include', '#import',
                    '#else', '#elif', '#classtemplate', '#define', '#path', '#var')), Comment.Preproc),
            (r'[L@]?"', String, 'string'),
            (r'(\d+\.\d*|\.\d+|\d+)[eE][+-]?\d+[lL]?', Number.Float),
            (r'(\d+\.\d*|\.\d+|\d+[fF])[fF]?', Number.Float),
            (r'\d+[Ll]?', Number.Integer),
            (r"['&*+=|?:<>/-]", Operator),
            # TODO: "correctly" parse complex code attributes
            (r'[()\[\],.]', Punctuation),
            # Globals
            (words(ANYGLOBALS,
                   suffix=r'\b'), Keyword),
            # BM_Statements
            (words(ANYSTATEMENTS,
                   suffix=r'\b'), Other.Statements),
            # BM_Options
            (words(ANYOPTIONS,
                   suffix=r'\b'), Other.Options),
            # Functions
            (words(ANYFUNCTIONS, suffix=r'\b'), Name.Builtin),
            # (r'(\.)([a-zA-Z_]\w*)',
            # bygroups(Operator, Name.Attribute)),
            # void is an actual keyword, others are in glib-2.0.vapi
            (words(ANYCLASSES,
                   suffix=r'\b'), Keyword),
            (r'[a-zA-Z_]\w*', Name),
        ],
        'root': [
            include('whitespace'),
            default('statement'),
        ],
        'statement': [
            include('whitespace'),
            include('statements'),
            ('[{}]', Punctuation),
            (';', Punctuation, '#pop'),
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})',
             String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ],
        'multiline-directive': [
            (r'(.*?)(§)', bygroups(Comment.Single, Generic.Deleted), 'new-codes'),
            (r'.*?\n', Comment.Single, '#pop')
        ],
        'new-codes': [
            (r'[^§]+', Generic.Error),
            (r'§', Generic.Deleted, '#pop'),
            (r'[§]', Generic.Error)
        ]
        # 'macro': [
        # (r'[^/\n]+', Comment.Preproc),
        # (r'/[*](.|\n)*?[*]/', Comment.Multiline),
        # (r'//.*?\n', Comment.Single, '#pop'),
        # (r'/', Comment.Preproc),
        # (r'(?<=\\)\n', Comment.Preproc),
        # (r'\n', Comment.Preproc, '#pop'),
        # ],
        # 'if0': [
        # (r'^\s*#if(?:def).*?(?<!\\)\n', Comment.Preproc, '#push'),
        # (r'^\s*#el(?:se|if).*\n', Comment.Preproc, '#pop'),
        # (r'^\s*#endif.*?(?<!\\)\n', Comment.Preproc, '#pop'),
        # (r'.*?\n', Comment),
        # ]
    }
