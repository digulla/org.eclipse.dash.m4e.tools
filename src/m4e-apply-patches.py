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
import os
import sys
import time
import logging
from m4e.common import configLogger, mustBeDirectory
from m4e.patches import PatchLoader, PatchTool
from m4e.pom import Pom

VERSION = '0.1 (07.04.2011)'

log = logging.getLogger('m4e.apply_patches')

class ApplyPatches(object):
    
    def run(self, patchDir, repoDir):
        log.info('Applying patches from %s to M2 repository in %s' % (patchDir, repoDir))
        
        self.loadPatches(patchDir)
        self.process(repoDir)
        
        log.info('Done.')
    
    def loadPatches(self, path):
        loader = PatchLoader(path)
        loader.addRemoveNonOptional()
        loader.run()
        
        self.patchTool = PatchTool(loader.patches)
    
    def process(self, root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                self.process(path)
            elif path.endswith('.pom'):
                self.applyPatches(path)

    def applyPatches(self, pomFile):
        pom = Pom(pomFile)
        
        before = repr(pom)
        self.patchTool.apply(pom)
        after = repr(pom)
        
        if before == after:
            log.debug('No changes in %s' % pomFile)
            return
        
        log.info('Patching %s' % pomFile)
        pom.save()

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

def main(name, argv):
    if not argv or set(argv) & helpOptions:
        print('%s %s' % (name, VERSION))
        print('Usage: %s <directory-with-patches> <m2repo>')
        print('')
        print('Move the sources of Eclipse plugins to the right place')
        print('so Maven 2 can find them.')
        return

    patchDir = mustBeDirectory(argv[0])
    repoDir = mustBeDirectory(argv[1])

    configLogger(repoDir + ".log")
    log.info('%s %s' % (name, VERSION))

    tool = ApplyPatches()
    tool.run(patchDir, repoDir)

if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log.error('%s' % e)
        raise
