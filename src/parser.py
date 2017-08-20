import sys
import re
import numpy as np
import logging

indent = ['',
          ' ',
          '  ',
          '   ',
          '    ',
          '     ',
          '      ',
          '       ',
          '        ',
          '          ',
          '           ',
          '            ',
          '             ',
          '              ',
          '               ',
          '                ']

class XMLnode(object):
    """This is a minimal class to allow easy creation of an XML tree
    from Python. It can write XML, but cannot read it."""

    __slots__ = ('_name', '_value', '_attribs', '_children', '_childmap')

    def __init__(self, name="--", value = ""):

        """Create a new node. Usually this only needs to be explicitly
        called to create the root element. Method addChild calls this
        constructor to create the new child node."""

        self._name = name

        # convert 'value' to a string if it is not already, and
        # strip leading whitespace
        if not isinstance(value, str):
            self._value = repr(value).lstrip()
        else:
            self._value = value.lstrip()

        self._attribs = {}    # dictionary of attributes
        self._children = []   # list of child nodes
        self._childmap = {}   # dictionary of child nodes


    def name(self):
        """The tag name of the node."""
        return self._name

    def nChildren(self):
        """Number of child elements."""
        return len(self._children)

    def addChild(self, name, value=""):
        """Add a child with tag 'name', and set its value if the value
        parameter is supplied."""

        # create a new node for the child
        c = XMLnode(name = name, value = value)

        # add it to the list of children, and to the dictionary
        # of children
        self._children.append(c)
        self._childmap[name] = c
        return c

    def addComment(self, comment):
        """Add a comment."""
        self.addChild(name = '_comment_', value = comment)

    def value(self):
        """A string containing the element value."""
        return self._value

    def child(self, name=""):
        """The child node with specified name."""
        return self._childmap[name]

    def children(self):
        """ An iterator over the child nodes """
        for c in self._children:
            yield c

    def __getitem__(self, key):
        """Get an attribute using the syntax node[key]"""
        return self._attribs[key]

    def __setitem__(self, key, value):
        """Set a new attribute using the syntax node[key] = value."""
        self._attribs[key] = value

    def __call__(self):
        """Allows getting the value using the syntax 'node()'"""
        return self._value

    def write(self, filename):
        """Write out the XML tree to a file."""
        s = ['<?xml version="1.0"?>\n']
        self._write(s, 0)
        s.append('\n')
        if isinstance(filename, str):
            with open(filename, 'w') as f:
                f.write(''.join(s))
        else:
            filename.write(''.join(s))

    def write_comment(self, s, level):
        s.append('\n'+indent[level]+'<!--')
        value = self._value
        if value:
            if value[0] != ' ':
                value = ' '+value
            if value[-1] != ' ':
                value += ' '
        s.append(value+'-->')

    def write_attribs(self, s):
        for a in self._attribs:
            s.append(' '+a+'="'+self._attribs[a]+'"')

    def write_value(self, s, level):
        indnt = indent[level]
        vv = self._value.lstrip()
        ieol = vv.find('\n')
        if ieol >= 0:
            while True:
                ieol = vv.find('\n')
                if ieol >= 0:
                    s.extend(('\n  ', indnt, vv[:ieol]))
                    vv = vv[ieol+1:].lstrip()
                else:
                    s.extend(('\n  ',indnt,vv))
                    break
        else:
            s.append(self._value)

    def _write(self, s, level = 0):
        """Internal method used to write the XML representation of each node."""
        if not self.name:
            return

        # handle comments
        if self._name == '_comment_':
            self.write_comment(s, level)
            return

        indnt = indent[level]

        # write the opening tag and attributes
        s.extend((indnt, '<', self._name))
        self.write_attribs(s)

        if not self._value and not self._children:
            s.append('/>')
        else:
            s.append('>')
            if self._value:
                self.write_value(s, level)

            for c in self._children:
                s.append('\n')
                c._write(s, level + 2)
            if self._children:
                s.extend(('\n', indnt))
            s.extend(('</', self._name, '>'))


_name = 'noname'

""" This module contains the code required to parse BOLSIG+-compatible files.
To make the code re-usabe in other projects it is independent from the rest of
the BOLOS code.

Most user would only use the method :func:`parse` in this module, which is 
documented below.
    
"""

def parse(fp):
    """ Parses a BOLSIG+ cross-sections file.  

    Parameters
    ----------
    fp : file-like
       A file object pointing to a Bolsig+-compatible cross-sections file.

    Returns
    -------
    processes : list of dictionaries
       A list with all processes, in dictionary form, included in the file.

    Note
    ----
    This function does not return :class:`process.Process` instances so that
    the parser is independent of the rest of the code and can be re-used in
    other projects.  If you want to convert a process in dictionary form `d` to
    a :class:`process.Process` instance, use

    >>> process = process.Process(**d)

    """
    processes = []
    for line in fp:
        try:
            key = line.strip()
            fread = KEYWORDS[key]

            # If the key is not found, we do not reach this line.
            logging.debug("New process of type '%s'" % key)

            d = fread(fp)
            d['kind'] = key
            processes.append(d)
            
        except KeyError:
            pass

    logging.info("Parsing complete. %d processes read." % len(processes))

    return processes


# BOLSIG+'s user guide saye that the separators must consist of at least five dashes
RE_SEP = re.compile("-----+")
def _read_until_sep(fp):
    """ Reads lines from fp until a we find a separator line. """
    lines = []
    for line in fp:
        if RE_SEP.match(line.strip()):
            break
        lines.append(line.strip())

    return lines


def _read_block(fp, has_arg=True):
    """ Reads data of a process, contained in a block. 
    has_arg indicates wether we have to read an argument line"""
    target = fp.next().strip()
    if has_arg:
        arg = fp.next().strip()
    else:
        arg = None

    comment = "\n".join(_read_until_sep(fp))

    logging.debug("Read process '%s'" % target)
    data = np.loadtxt(_read_until_sep(fp)).tolist()

    return target, arg, data

#
# Specialized funcion for each keyword. They all return dictionaries with the
# relevant attibutes.
# 
def _read_momentum(fp):
    """ Reads a MOMENTUM or EFFECTIVE block. """
    target, arg, data = _read_block(fp, has_arg=True)
    mass_ratio = float(arg.split()[0])
    d = dict(target=target,
             mass_ratio=mass_ratio,
             data=data)
    return d

RE_ARROW = re.compile('<?->')    
def _read_excitation(fp):
    """ Reads an EXCITATION or IONIZATION block. """
    target, arg, data = _read_block(fp, has_arg=True)
    lhs, rhs = [s.strip() for s in RE_ARROW.split(target)]

    d = dict(target=lhs,
             product=rhs,
             data=data)

    if '<->' in target.split():
        threshold, weight_ratio = float(arg.split()[0]), float(arg.split()[1])
        d['weight_ratio'] = weight_ratio
    else:
        threshold = float(arg.split()[0])

    d['threshold'] = threshold

    return d


def _read_attachment(fp):
    """ Reads an ATTACHMENT block. """
    target, arg, data = _read_block(fp, has_arg=False)

    d = dict(data=data,
             threshold=0.0)
    lr = [s.strip() for s in RE_ARROW.split(target)]

    if len(lr) == 2:
        d['target'] = lr[0]
        d['product'] = lr[1]
    else:
        d['target'] = target

    return d


KEYWORDS = {"MOMENTUM": _read_momentum, 
            "ELASTIC": _read_momentum, 
            "EFFECTIVE": _read_momentum,
            "EXCITATION": _read_excitation,
            "IONIZATION": _read_excitation,
            "ATTACHMENT": _read_attachment}


def main():
    with open('Cross section.txt') as fp:
        processes = parse(fp)
    x = XMLnode("ctml")
    for i, p in enumerate(processes):
        r = x.addChild('process')
        r['id'] = str(i)
        r['type'] = p['kind']
        r.addChild(name='reactants',value=p['target'])

        if p['kind'].find("EXCITATION") is not -1:
            r.addChild(name='products',value=p['product'])
            r.addChild(name='threshold',value=p['threshold'])
            if 'weight_ratio' in p:
                r['reversible'] = 'yes'
                r.addChild(name='weight_ratio',value=p['weight_ratio'])
        elif p['kind'].find("IONIZATION") is not -1:
            r.addChild(name='products',value=p['product'])
            r.addChild(name='threshold',value=p['threshold'])
        elif p['kind'].find("ATTACHMENT") is not -1:
            r.addChild(name='products',value=p['product'])
            r.addChild(name='threshold',value=p['threshold'])       
        else:
            r.addChild(name='products',value=p['target'])
            r.addChild(name='mass_ratio',value=p['mass_ratio'])
        data = ''
        for j in p['data']:
            data += '%10.6E ' % j[0]
            data += '%10.6E ' % j[1]
            data += '\n'

        r.addChild(name='data',value=data)

    x.write("lxcat.xml")


if __name__ == "__main__":
    main()

