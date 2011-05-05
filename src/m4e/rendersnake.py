# /*******************************************************************************
# * Copyright (c) 05.05.2011 Aaron Digulla.
# * All rights reserved. This program and the accompanying materials
# * are made available under the terms of the Eclipse Public License v1.0
# * which accompanies this distribution, and is available at
# * http://www.eclipse.org/legal/epl-v10.html
# *
# * Contributors:
# *    Aaron Digulla - initial API and implementation and/or initial documentation
# *******************************************************************************/
'''
HTML renderer like renderSnake (http://code.google.com/p/rendersnake/)

Created on May 5, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import cgi

__all__ = [ 'HtmlCanvas', 'A' ]

class HtmlCanvas(object):
    def __init__(self, out):
        self.out = out
        self.stack = []
    
    def write(self, text, escapeNeeded=True):
        if escapeNeeded:
            text = self.escape(text)
        
        self.out.write(text)
        
        return self
    
    def escape(self, text):
        return cgi.escape(text)
    
    def html_begin(self, tag, attrs=None):
        self.out.write('<')
        self.out.write(tag)
        
        if attrs:
            attrs.write(self.out)
            
        self.out.write('>')
        
        self.stack.append('</%s>' % tag)
        
        return self
    
    def html_end(self, tag):
        s = '</%s>' % tag
        expected = self.stack.pop()
        if s != expected:
            raise RuntimeError('Tried to close %s but %s was open' % (expected, s))
        self.out.write(s)
        
        return self

def defineTags(*names):
    for name in names:
        def f(self, attrs=None, name=name):
            return self.html_begin(name, attrs)
        
        setattr(HtmlCanvas, name, f)

        def f(self, attrs=None, name=name):
            return self.html_end(name)
        
        name2 = '_%s' % name
        setattr(HtmlCanvas, name2, f)

defineTags('a', 'br', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'html', 'head', 'title', 'body', 'span', 'ul', 'li', 'ol', 'style')

class HtmlAttrs(object):
    def __init__(self):
        self.attrs = []
    
    def add_attr(self, name, value):
        self.attrs.append('%s="%s"' % (name, cgi.escape(value, True)))
        return self
    
    def write(self, out):
        for attr in self.attrs:
            out.write(' ')
            out.write(attr)

def defineAttrs(*names):
    for name in names:
        attrName = name
        if attrName.endswith('_'):
            attrName = attrName[:-1]
        
        def f(self, value, name=attrName):
            return self.add_attr(name, value)
        
        setattr(HtmlAttrs, name, f)

def A():
    return HtmlAttrs()

defineAttrs('class_', 'id', 'style', 'href', 'type', 'onclick', 'name')

if __name__ == '__main__':
    import sys
    
    html = HtmlCanvas(sys.stdout)
    html.html().head().write('\n') \
    .title().write('Demo')._title().write('\n') \
    ._head().write('\n') \
    .body().write('\n') \
    .div(A().id('xxx').class_('yyy').onclick("a='x'; b=\"b\"")) \
    .write('<hello&>') \
    ._div() \
    ._body()._html().write('\n')
