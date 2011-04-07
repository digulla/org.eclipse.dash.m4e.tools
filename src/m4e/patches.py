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
Helper code to create m4e patches

Created on Apr 7, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import os.path
import logging

log = logging.getLogger("m4e.patches")

class RemoveNonOptional(object):
    def run(self, pom):
        for dependency in pom.dependencies():
            if dependency.optional:
                continue
            
            dependency.optional = None

    def __repr__(self):
        return 'RemoveNonOptional()'

class Patches(object):
    def __init__(self, fileName):
        self.fileName = fileName
        self.patches = []
    
    def __repr__(self):
        return 'Patches(%s)' % self.fileName

    def run(self, pom):
        for patch in self.patches:
            patch.run(pom)

class PatchDependency(object):
    def __init__(self, groupId=None, artifactId=None, version=None, optional=None, scope=None):
        self.groupId = groupId
        self.artifactId = artifactId
        self.version = version
        self.optional = optional
        self.scope = scope

    def __repr__(self):
        s = ''
        if self.optional:
            s += ':optional=%s' % self.optional
        if self.scope:
            s += ':scope=%s' % self.scope
        
        return '%s:%s:%s%s' % (self.groupId, self.artifactId, self.version, s)
    
    def key(self):
        return '%s:%s:%s' % (self.groupId, self.artifactId, self.version)
    
    def __eq__(self, other):
        return ((self.groupId, self.artifactId, self.version) ==
                (other.groupId, other.artifactId, other.version)) 

def dependencyFromString(s):
    parts = s.split(':')
    if len(parts) < 3:
        raise ValueError('Expected at least three colon-separated values: [%s]' % s)

    options = {}
    for part in parts[3:]:
        tmp = part.split('=', 2)
        
        if len(tmp) != 2:
            raise ValueError('Expected at least two equals-separated values in [%s] of [%s]' % (part, s))
        
        options[tmp[0]] = tmp[1]
    
    optional = options.pop('optional', None)
    scope = options.pop('scope', None)
    
    if len(options):
        raise ValueError('Unexpected options %s in [%s]' % (options, s))
    
    if optional is not None:
        optional = 'true' == optional
    
    return PatchDependency(groupId=parts[0], artifactId=parts[1], version=parts[2], optional=optional, scope=scope)

class ReplaceDependency(object):
    def __init__(self, pattern, replacement):
        self.pattern = dependencyFromString(pattern)
        self.replacement = dependencyFromString(replacement)

    def __repr__(self):
        return 'ReplaceDependency(%s -> %s)' % (self.pattern, self.replacement)

class DependencyPatcher(object):
    def __init__(self, replacements):
        self.replacements = replacements
        
        self.depMap = {}
        for r in replacements:
            key = r.pattern.key()
            self.depMap[key] = r

    def run(self, pom):
        for dependency in pom.dependencies():
            key = dependency.key()
            
            r = self.depMap.get(key, None)
            if r is None:
                continue
            
            log.debug('Found %s in %s' % (key, pom.pomFile))
            
            self.replaceDependency(dependency, r.replacement)

    def __repr__(self):
        return 'DependencyPatcher(%d)' % len(self.replacements)
        
    def replaceDependency(self, dependency, replacement):
        dependency.groupId = replacement.groupId
        dependency.artifactId = replacement.artifactId
        dependency.version = replacement.version
        if replacement.optional is not None:
            dependency.optional = replacement.optional
        if replacement.scope is not None:
            dependency.scope = replacement.scope

class PatchLoader(object):
    def __init__(self, path):
        self.path = path
        self.patches = []
    
    def run(self):
        self.process(self.path)
    
    def process(self, root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                self.process(path)
            elif path.endswith('.patches'):
                self.addPatch(path)

    def addPatch(self, fileName):
        
        patch = Patches(fileName)
        self.patches.append(patch)
        
        replacements = []
        
        def replace(*args):
            replacements.append(ReplaceDependency(*args))
        
        globals = dict(
            replace=replace,
        )
        locals = {}
        execfile(fileName, globals, locals)
        
        if replacements:
            patch.patches.append(DependencyPatcher(replacements))
        
class PatchTool(object):
    def __init__(self, patches):
        self.patches = patches
    
    def apply(self, pom):
        for patch in self.patches:
            patch.run(pom)