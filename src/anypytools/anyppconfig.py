""" Class for storing and getting define/path statements from a file """

import re
import collections
RE_PATTERN = (r'^(?P<prefix>[^\S\n]*(?P<type>(?:#define|#path))[^\S\n]+)'
              r'(?P<key>{key})(?P<space>[^\S\n]+)'
              r'(?P<value>.+?)'
              r'(?P<postfix>[ \t]*(?:(?://|/\*).*)?)$')

RE_PARSE = re.compile(RE_PATTERN.format(key= r'\w+'), re.M)
PVar = collections.namedtuple('PVar', ['type', 'value'])

class AnyPPConfig(collections.MutableMapping):
    '''
    Implements a dictionary interface to the an underlying python file.
    The defines/path statements of anyscript file can be manipulated by chinging the
    mapping.

    anyconfig = AnyPPConfig('BodyModelConfig.any')
    # Change BM_TRUNK_NECK to off or add it if it doesn't exist
    anyconfig['BM_TRUNK_NECK'] = 'OFF'

    New statements are added as to the buttom of the file.
    All new staments added through the dict interface are treated as
    #define's. To add a #path statements use bm.add

    '''
    def __init__(self, filename, *args, **kwargs):
        self._cached_stamp = 0
        self.filename = filename
        self.update(*args, **kwargs)

    # def _file_changed(self):
    #     stamp = 0
    #     attempts = 10
    #     while attempts < 10:
    #         stamp, old_stamp = os.stat(self.filename).st_mtime, stamp
    #         if stamp == old_stamp:
    #             yield False
    #         else:
    #             yield True
    #     raise IOError('Unable to write to an unchanged file')

    def _read_and_parse(self):
        """
        Reads the AnyScript file and parses the define/path statements to
        a list of (key,value) tuples. Returns the tuples and the filecontent
        """
        with open(self.filename) as f:
            content = f.read()
        mlist = RE_PARSE.findall(content)
        if mlist:
            matches = [(g[2], PVar(g[1], g[4])) for g in mlist]
        else:
            matches = []
        return matches, content

    def _check_key(self, key):
        if key.startswith('#'):
            ktype, key = key.split()
        else:
            ktype, key = None, key
        return ktype, key

    def __setitem__(self, key, value):
        keytype, key = self._check_key(key)
        self._check_value(value)
        matches, content = self._read_and_parse()
        self._check_multiple_entries(key, matches)
        d = dict(matches)
        if key in d:
            if keytype is not None and keytype != d[key].type:
                raise KeyError('The type (define/path) does not match'
                               ' the variable already in the file')
            pattern = RE_PATTERN.format(key=key)
            repl = r'\g<prefix>\g<key>\g<space>{val}\g<postfix>'.format(val=value)
            out, n = re.subn(pattern, repl, content, flags=re.M)
            if n != 1:
                ValueError('Regex errro. Could not update value')
        else:
            if not keytype:
                out = '{}\n#define {} {}'.format(content, key, value)
            else:
                out = '{}\n{} {} {}'.format(content, keytype, key, value)
        with open(self.filename, 'w') as fh:
            fh.write(out)

    def _check_value(self, value):
        """ Check that the values given is valid"""
        if not isinstance(value, str):
            raise ValueError('Values must be Strings')
        if value.startswith('"') or value.endswith('"'):
            if value[0] != value[-1]:
                raise ValueError('Unbalanced quotes')

    def __getitem__(self, key):
        ktype, key = self._check_key(key)
        matches, _ = self._read_and_parse()
        self._check_multiple_entries(key, matches)
        d = dict(matches)
        if key in d and (ktype is None or ktype == d[key].type):
            return d[key].value
        else:
            self._raise_keyerror(ktype, key)

    def _check_multiple_entries(self, key, matches):
        """
        Checks that the key is not define multiple times in the file.
        Raises ValueError otherwise """
        if matches:
            _, key = self._check_key(key)
            keys = list(zip(*matches))[0]
            if keys.count(key) > 1:
                raise ValueError(key + ' name is defined multiple times in the file')


    def _raise_keyerror(self, ktype, key):
        ktype = ktype + ' ' if ktype else ''
        raise KeyError(ktype + key)

    def __delitem__(self, key):
        ktype, key = self._check_key(key)
        matches, content = self._read_and_parse()
        self._check_multiple_entries(key, matches)
        d = dict(matches)
        if key in d and (ktype is None or ktype == d[key].type):
            pattern = RE_PATTERN.format(key=key)
            out, n = re.subn(pattern, "", content, flags=re.M)
            if n != 1:
                ValueError('Regex errro. Could not update value')
        else:
            self._raise_keyerror(ktype, key)
        with open(self.filename, 'w') as fh:
            fh.write(out)

    def __iter__(self):
        stamp = os.stat(self.filename).st_mtime
        matches, _ = self._read_and_parse()
        d = dict(matches)
        for k in d:
            if stamp != os.stat(self.filename).st_mtime:
                raise IOError('AnyScript file changed while iterating over it')
            yield k

    def __len__(self):
        matches, _ = self._read_and_parse()
        return len(matches)

    def __str__(self):
        '''returns simple dict representation of the mapping'''
        matches, _ = self._read_and_parse()
        d = dict(matches)
        return d.__str__()

    def __repr__(self):
        '''echoes class, id, & reproducible representation in the REPL'''
        matches, _ = self._read_and_parse()
        d = dict(matches)
        return 'AnyPPConfig("{}"),{}'.format(self.filename, d.__repr__())

    def get_file_content(self):
        matches, content = self._read_and_parse()
        return content


if __name__ == '__main__':
    bm = AnyPPConfig(filename='BodyModelConfig.any')