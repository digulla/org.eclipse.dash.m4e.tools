#!/usr/bin/env python
# /*******************************************************************************
# * Copyright (c) 17.03.2011 Aaron Digulla.
# * All rights reserved. This program and the accompanying materials
# * are made available under the terms of the Eclipse Public License v1.0
# * which accompanies this distribution, and is available at
# * http://www.eclipse.org/legal/epl-v10.html
# *
# * Contributors:
# *    Aaron Digulla - initial API and implementation and/or initial documentation
# *******************************************************************************/
'''
Small tool to merge several Maven 2 repositories

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import os
import sys
import filecmp
import time

VERSION = '0.5 (19.03.2011)'

def merge(source, target):
    names = os.listdir(source)
    
    if not os.path.exists(target):
        os.makedirs(target)
    
    for name in names:
        srcPath = os.path.join(source, name)
        targetPath = os.path.join(target, name)
        
        if os.path.isdir(srcPath):
            if os.path.exists(targetPath) and not os.path.isdir(targetPath):
                raise RuntimeError("%s is a directory but %s is a file" % (srcPath, targetPath))
            
            merge(srcPath, targetPath)
        else:
            if os.path.isdir(targetPath):
                raise RuntimeError("%s is a file but %s is a directory" % (srcPath, targetPath))
            
            if os.path.exists(targetPath):
                equal = filecmp.cmp(srcPath, targetPath)
                if not equal:
                    log("WARNING %s differs from %s" % (targetPath, srcPath))
                pass
            else:
                os.link(srcPath, targetPath)

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

def main(name, argv):
    if not argv or set(argv) & helpOptions:
        print('%s %s' % (name, VERSION))
        print('Usage: %s <m2repos...> <result>')
        print('')
        print('Merge the files in the various Maven 2 repositories into one repositories')
        print(workDir)
        return

    target = argv[-1]
    if os.path.exists(target):
        raise RuntimeError('Target repository %s already exists. Cowardly refusing to continue.' % target)
    
    if not os.path.exists(target):
        os.makedirs(target)
    
    global logFile
    logFile = open(target + ".log", 'a')
    log('%s %s' % (name, VERSION))
    
    for source in argv[:-1]:
        log('Merging %s' % source)
        merge(source, target)

logFile = None
def log(msg):
    print(msg)
    
    if logFile is not None:
        logFile.write(time.strftime('%Y%m%d-%H%M%S '))
        logFile.write(msg)
        logFile.write('\n')
        logFile.flush()

if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log('%s' % e)
        raise
    finally:
        if logFile is not None:
            logFile.close()
