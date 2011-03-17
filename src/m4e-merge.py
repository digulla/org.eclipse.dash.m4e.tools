#!/usr/bin/env python
'''
Small tool to merge several Maven 2 repositories

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import os
import sys
import filecmp

VERSION = '0.1 (17.03.2011)'

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
                    print("WARNING %s differs from %s" % (targetPath, srcPath))
                pass
            else:
                os.link(srcPath, targetPath)

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

def main(name, argv):
    print('%s %s' % (name, VERSION))
    if not argv or set(argv) & helpOptions:
        print('Usage: %s <m2repos...> <result>')
        print('')
        print('Merge the files in the various Maven 2 repositories into one repositories')
        print(workDir)
        return

    target = argv[-1]
    if os.path.exists(target):
        raise RuntimeError('Target repository %s already exists. Cowardly refusing to continue.' % target)
    
    for source in argv[:-1]:
        merge(source, target)
        
if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])
