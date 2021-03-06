# /*******************************************************************************
# * Copyright (c) 07.04.2011 Aaron Digulla.
# * All rights reserved. This program and the accompanying materials
# * are made available under the terms of the Eclipse Public License v1.0
# * which accompanies this distribution, and is available at
# * http://www.eclipse.org/legal/epl-v10.html
# *
# * Contributors:
# *    Aaron Digulla - initial API and implementation and/or initial documentation
# *******************************************************************************/
'''
Common code for m4e tools

Created on Apr 7, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import logging.handlers
import sys
import os.path

def substringBefore( s, pattern ):
    '''Get the substring before a pattern.
    
    Returns None if the pattern can't be found.'''
    pos = s.find( pattern )
    if pos == -1:
        return None
    
    return s[0:pos]

def userNeedsHelp(argv):
    helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))
    
    return not argv or set(argv) & helpOptions

def configLogger(fileName):
    '''Configure the logger.'''
    #logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    path = os.path.abspath(fileName)
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = []
    
    doRollover = os.path.exists(fileName) and os.stat(fileName).st_size > 0
    
    handler = logging.handlers.RotatingFileHandler(fileName, 
                                                   maxBytes=0, backupCount=5, encoding='UTF-8')
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s'))
    handler.setLevel(logging.DEBUG)
    
    # Create a new log file each time the script is run
    if doRollover:
        handler.doRollover()
    
    root.addHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(fmt='%(message)s'))

    root.addHandler(handler)

def mustBeDirectory(path):
    '''Raise an exception if path is not a directory.'''
    if not os.path.exists(path):
        raise RuntimeError("%s doesn't exist" % path)
    
    if not os.path.isdir(path):
        raise RuntimeError('%s is not a directory' % path)
    
    return os.path.abspath(path)
