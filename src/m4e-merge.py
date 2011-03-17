'''
Small tool to merge several Maven 2 repositories

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import os
import sys
import filecmp

VERSION = '0.1 (17.03.2011)'

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

def merge(source, target):
    names = os.listdir(source)
    
    for name in names:
        srcPath = os.path.join(source, name)
        targetPath = os.path.join(target, name)
        
        if os.path.isdir(srcPath):
            if not os.path.isdir(targetPath):
                raise RuntimeError("%s is a directory but %s is a file" % (srcPath, targetPath))
            
            merge(source, target)
        else:
            if os.path.isdir(targetPath):
                raise RuntimeError("%s is a file but %s is a directory" % (srcPath, targetPath))
            
            if os.path.exists(targetPath):
                equal = filecmp.cmp(srcPath, targetPath)
                if not equal:
                    raise RuntimeError("%s exists but it differs from %s" % (targetPath, srcPath))
            else:
                os.link(srcPath, targetPath)

def main(name, argv):
    print('%s %s' % (name, VERSION))
    if not argv or set(argv) & helpOptions:
        print('Usage: %s <archives...> <result>')
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
