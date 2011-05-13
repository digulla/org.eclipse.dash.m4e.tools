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

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
"""
import os
import sys
import time
import logging
from m4e.common import configLogger, userNeedsHelp

VERSION = '1.1 (07.04.2011)'

log = logging.getLogger('m4e.attach_sources')

class AttachSources(object):
    def __init__(self):
        self.count = 0
        
    def run(self, root):
        log.info('Attaching sources in %s' % root)
        self.process(root)
        log.info('Found %d source JARs' % self.count)

    def process(self, root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                if path.endswith('.source'):
                    self.processSource(path)
                else:
                    self.process(path)
    
    def processSource(self, srcPath):
        binPath = srcPath[:-7] 
        
        if not os.path.exists(binPath):
            log.warning('Missing %s' % binPath)
            return
        
        versions = os.listdir(srcPath)
        
        canDelete = True
        for version in versions:
            if not self.processSourceVersion(srcPath, binPath, version):
                canDelete = False
        
        if canDelete:
            os.rmdir(srcPath)
    
    def processSourceVersion(self, srcPath, binPath, version):
        srcPath = os.path.join(srcPath, version)
        binPath = os.path.join(binPath, version)
        
        if not os.path.exists(binPath):
            log.warning('Missing %s' % binPath)
            return
        
        sources = os.listdir(srcPath)
        canDelete = True
        for name in sources:
            if name.endswith('.pom'):
                pom = os.path.join(srcPath, name)
                log.debug('Deleting source POM %s' % pom)
                os.remove(pom)
                continue
            
            if name.endswith('.jar'):
                self.moveSource(srcPath, binPath, name)
                continue
            
            log.warning('Unexpected file %s' % os.path.join(srcPath, name))
            canDelete = False
        
        if canDelete:
            log.debug('%s is empty -> deleting' % srcPath)
            os.rmdir(srcPath)
        
        return canDelete
    
    def moveSource(self, srcPath, binPath, name):
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
        log.debug('Moving %s to %s' % (src, target))
        os.rename(src, target)
        
        self.count += 1

def main(name, argv):
    if userNeedsHelp(argv):
        print('%s %s' % (name, VERSION))
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

    configLogger(root + ".log")
    log.info('%s %s' % (name, VERSION))

    tool = AttachSources()
    tool.run(root)

if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log.error('%s' % e)
        raise
