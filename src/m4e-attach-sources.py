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
"""Maven 2 Eclipse Artifact Source resolver

After importing Eclipse artifacts into an M2 repository with

> mvn eclipse:make-artifacts -DstripQualifier=true -DeclipseDir=.../eclipse

run this script to move all source JARs in the right place for
Maven 2 to pick them up.

@author: Aaron Digulla <digulla@hepe.com>
"""
import os, sys
from shutil import copyfile

VERSION = '0.9 (17.03.2011)'

def process(root):
    for name in os.listdir(root):
        path = os.path.join(root, name)
        
        if os.path.isdir(path):
            if path.endswith('.source'):
                processSource(path)
            else:
                process(path)

def processSource(srcPath):
    binPath = srcPath[:-7] 
    
    if not os.path.exists(binPath):
        print('WARNING: Missing %s' % binPath)
        return
    
    versions = os.listdir(srcPath)
    
    canDelete = True
    for version in versions:
        if not processSourceVersion(srcPath, binPath, version):
            canDelete = False
    
    if canDelete:
        os.rmdir(srcPath)

def processSourceVersion(srcPath, binPath, version):
    srcPath = os.path.join(srcPath, version)
    binPath = os.path.join(binPath, version)
    
    if not os.path.exists(binPath):
        print('WARNING: Missing %s' % binPath)
        return
    
    sources = os.listdir(srcPath)
    canDelete = True
    for name in sources:
        if name.endswith('.pom'):
            os.remove(os.path.join(srcPath, name))
            continue
        
        if name.endswith('.jar'):
            moveSource(srcPath, binPath, name)
            continue
        
        print('WARNING: Unexpected file %s' % os.path.join(srcPath, name))
        canDelete = False
    
    if canDelete:
        os.rmdir(srcPath)
    
    return canDelete

def moveSource(srcPath, binPath, name):
    # name = org.eclipse.core.runtime.source-3.6.0.jar
    pos1 = name.rindex('-')
    pos2 = name.rindex('.')
    
    version = name[pos1+1:pos2]
    baseName = name[:pos1]
    
    if not baseName.endswith('.source'):
        raise RuntimeError('Unexpected file %s' % os.path.join(srcPath, name))
    
    baseName = baseName[:baseName.rindex('.')]
    
    binName = '%s-%s.jar' % (baseName, version)
    target = '%s-%s-sources.jar' % (baseName, version)
    
    binJar = os.path.join(binPath, binName)
    if not os.path.exists(binJar):
        raise RuntimeError('Missing file %s' % os.path.join(binJar))
    
    src = os.path.join(srcPath, name)
    target = os.path.join(binPath, target)
    os.rename(src, target)

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

def main(name, argv):
    print('%s %s' % (name, VERSION))
    if not argv or set(argv) & helpOptions:
        print('Usage: %s <m2repo>')
        print('')
        print('Move the sources of Eclipse plugins to the right place')
        print('so Maven 2 can find them.')
        return

    root = argv[0]
    if not os.path.exists(root):
        raise RuntimeError("%s doesn't exist" % root)
    
    if not os.path.isdir(root):
        raise RuntimeError('%s is not a directory' % root)
    
    process(root)

if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])
