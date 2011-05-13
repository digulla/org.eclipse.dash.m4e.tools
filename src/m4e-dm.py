#!/usr/bin/env python
# /*******************************************************************************
# * Copyright (c) 12.05.2011 Aaron Digulla.
# * All rights reserved. This program and the accompanying materials
# * are made available under the terms of the Eclipse Public License v1.0
# * which accompanies this distribution, and is available at
# * http://www.eclipse.org/legal/epl-v10.html
# *
# * Contributors:
# *    Aaron Digulla - initial API and implementation and/or initial documentation
# *******************************************************************************/
"""Tool to create POM files with a dependencyManagement element.

See http://maven.apache.org/guides/introduction/introduction-to-dependency-mechanism.html#Importing_Dependencies
for how to use this POM.

Created on May 12, 2011

@author: Aaron Digulla <digulla@hepe.com>
"""
import os
import sys
import time
import logging
from m4e.common import configLogger, mustBeDirectory, userNeedsHelp
from m4e.pom import Pom, createPom, getOrCreate, setOptionalText, POM_NS_PREFIX
from lxml import etree

VERSION = '0.1 (12.05.2011)'

log = logging.getLogger('m4e.dm')

class DependencyManagementTool(object):
    def __init__(self, repoDir, artifact):
        self.repoDir = repoDir
        self.groupId, self.artifactId, self.version = artifact.split(':')
    
    def run(self):
        self.pom = createPom(self.repoDir, self.groupId, self.artifactId, self.version)
        
        dependencyManagement = getOrCreate(self.pom.project, 'dependencyManagement')
        self.dependencies = getOrCreate(dependencyManagement, 'dependencies')
        
        self.process(self.repoDir)
        
        self.pom.save()
    
    def process(self, root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                self.process(path)
            elif path.endswith('.pom'):
                self.processPom(path)
    
    def processPom(self, path):
        log.debug('Reading %s' % (path,))
        pom = Pom(path)
        
        dep = etree.SubElement(self.dependencies, POM_NS_PREFIX+'dependency')
        
        setOptionalText(dep, 'groupId', pom.project.groupId.text)
        setOptionalText(dep, 'artifactId', pom.project.artifactId.text)
        setOptionalText(dep, 'version', pom.project.version.text)
        

def main(name, argv):
    if userNeedsHelp(argv) or len(argv) != 2:
        print('%s %s' % (name, VERSION))
        print('Usage: %s <m2repo> <groupId:artifactId:version')
        print('')
        print('Create a POM file with the dependencyManagement element')
        print('for all POMs found in the repository.')
        return

    repoDir = mustBeDirectory(argv[0])
    artifact = argv[1]

    configLogger(repoDir + "-dm.log")
    log.info('%s %s' % (name, VERSION))

    tool = DependencyManagementTool(repoDir, artifact)
    tool.run()
    
    log.info('Done.')

if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log.info('arguments: %s' % (sys.argv,))
        log.error('%s' % e)
        raise
