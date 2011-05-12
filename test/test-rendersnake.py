
from m4e.rendersnake import *

import StringIO
from nose.tools import eq_

def test_Render():
    buffer = StringIO.StringIO()
    
    html = HtmlCanvas(buffer)
    
    html.html().head().write('\n') \
    .title().write('Demo')._title().write('\n') \
    ._head().write('\n') \
    .body().write('\n') \
    .div(A().id('xxx').class_('yyy').onclick("a='x'; b=\"b\"")) \
    .write('<hello&>') \
    ._div() \
    ._body()._html().write('\n')

    eq_('<html><head>\n<title>Demo</title>\n</head>\n<body>\n<div id="xxx" class="yyy" onclick="a=\'x\'; b=&quot;b&quot;">&lt;hello&amp;&gt;</div></body></html>\n', buffer.getvalue())