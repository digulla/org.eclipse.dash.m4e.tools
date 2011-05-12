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
from lxml import etree, objectify

log = logging.getLogger("m4e.patches")

class PatchInfo(object):
    '''Information about a patch, for example the involved dependencies'''
    pass

class RemoveNonOptional(PatchInfo):
    '''Remove <optional>false</optional> from all POMs'''
    def run(self, pom):
        for dependency in pom.dependencies():
            if dependency.optional:
                continue
            
            dependency.optional = None

    def __repr__(self):
        return 'RemoveNonOptional()'

class PatchSet(object):
    '''A set of patches'''
    def __init__(self, fileName):
        self.fileName = fileName
        self.patches = []
    
    def __repr__(self):
        return 'PatchSet(%s)' % self.fileName

    def run(self, pom):
        for patch in self.patches:
            patch.run(pom)

class PatchDependency(object):
    '''Data container for dependency data (groupId, artifactId, version, scope, ...)'''
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
    '''Create a PatchDependency from a string'''
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

class ReplaceDependency(PatchInfo):
    '''Replace a dependency with another'''
    def __init__(self, pattern, replacement):
        self.pattern = dependencyFromString(pattern)
        self.replacement = dependencyFromString(replacement)

    def __repr__(self):
        return 'ReplaceDependency(%s -> %s)' % (self.pattern, self.replacement)

class DeleteDependency(PatchInfo):
    '''Delete a dependency'''
    def __init__(self, pattern):
        self.pattern = dependencyFromString(pattern)
        
    def __repr__(self):
        return 'DeleteDependency(%s -> %s)' % (self.pattern)

class ProfileTool(object):
    '''Tool to move replaced dependencies to a profile'''
    
    def __init__(self, pom, defaultProfileName, profileName):
        self.pom = pom

        self.defaultProfileName = defaultProfileName
        self.profileName = profileName

        self.defaultProfile = None
        self.profile = None
    
    def replaceDependency(self, dependency, replacement):
        '''Remove the dependency from the original place and more it
        to self.defaultProfile. Add the replacement to self.profile.'''
        dependency.remove()

        if self.defaultProfile is None:
            self.defaultProfile = self.pom.profile(self.defaultProfileName)
            self.defaultProfile.activeByDefault( True )
            
            self.profile = self.pom.profile(self.profileName)
        
        self.defaultProfile.addDependency(dependency)
        
        d = self.createXmlDependency(replacement)
        self.profile.addDependency(d)

    def createXmlDependency(self, template):
        '''Create an XML tree from a PatchDependency'''
        d = objectify.Element('dependency')
        
        for field in ('groupId', 'artifactId', 'version', 'optional', 'scope'):
            value = getattr(template, field)
            if value is None:
                continue
            
            if type(value) == type(True):
                if not value:
                    continue
                
                value = 'true' if value else 'false'
            
            etree.SubElement(d, field)._setText(value)
        
        return d

class DependencyPatcher(object):
    '''Apply dependency patches to a POM'''
    def __init__(self, defaultProfileName, profileName, replacements, deletes):
        self.defaultProfileName = defaultProfileName
        self.profileName = profileName
        self.replacements = replacements
        self.deletes = deletes
        
        self.depMap = {}
        for r in self.replacements:
            key = r.pattern.key()
            self.depMap[key] = r
            
        self.delSet = set()
        for d in self.deletes:
            key = d.pattern.key()
            self.delSet.add(key)

    def run(self, pom):
        tool = ProfileTool(pom, self.defaultProfileName, self.profileName)
        
        for dependency in pom.dependencies():
            key = dependency.key()
            
            if key in self.delSet:
                dependency.remove()
                continue
            
            r = self.depMap.get(key, None)
            if r is None:
                continue
            
            log.debug('Found %s in %s' % (key, pom.pomFile))
            
            tool.replaceDependency(dependency, r.replacement)

    def __repr__(self):
        return 'DependencyPatcher(%d)' % len(self.replacements)
        
class PatchLoader(object):
    '''Load patches from a file'''
    
    def __init__(self, path):
        self.path = path
        self.patches = []
        self.profile = None
        self.defaultProfile = None
    
    def addRemoveNonOptional(self):
        self.patches.append(RemoveNonOptional())
    
    def run(self):
        self.process(self.path)
    
    def process(self, root):
        '''Search a folder for patches'''
        
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                self.process(path)
            elif path.endswith('.patches'):
                self.addPatch(path)

    def addPatch(self, fileName):
        '''Add all patches in a file to the list of patches'''
        
        patch = PatchSet(fileName)
        self.patches.append(patch)
        
        replacements = []
        deletes = []
        
        def replace(*args):
            replacements.append(ReplaceDependency(*args))
        def delete(*args):
            deletes.append(DeleteDependency(*args))
        def profile(name):
            self.profile = name
        def defaultProfile(name):
            self.defaultProfile = name
        
        globals = dict(
            replace=replace,
            delete=delete,
            profile=profile,
            defaultProfile=defaultProfile,
        )
        locals = {}
        execfile(fileName, globals, locals)
        
        if replacements or deletes:
            patch.patches.append(DependencyPatcher(self.defaultProfile, self.profile, replacements, deletes))
        
class PatchTool(object):
    '''Tool to apply a set of patches to a single POM'''
    def __init__(self, patches):
        self.patches = patches
    
    def apply(self, pom):
        for patch in self.patches:
            patch.run(pom)
