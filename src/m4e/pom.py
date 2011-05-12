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
Tools to work with POMs

Created on Apr 7, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import os.path
from lxml import etree, objectify

POM_NS = 'http://maven.apache.org/POM/4.0.0'
POM_NS_PREFIX = '{%s}' % POM_NS
NAMESPACES = {
    'pom': POM_NS,
}

def xmlPath(element):
    path = []
    
    while True:
        parent = element.getparent()
        name = element.tag
        if name.startswith(POM_NS_PREFIX):
            name = name[len(POM_NS_PREFIX):]
        
        if parent is None:
            path.insert(0, '/%s' % name)
            break
        
        expr = etree.ETXPath(element.tag)
        children = expr(parent)
        #print 'xmlPath',element.tag,children
        index = children.index(element)
        
        if len(children) == 1:
            item = '/%s' % name
        else:
            item = '/%s[%d]' % (name, index)
        
        path.insert(0, item)
        
        element = parent
    
    return ''.join(path)

#objectify.Element.__repr__ = lambda self: xmlPath(self)

def removeElement(element):
    parent = element.getparent()
    
    previous = element.getprevious()
    if previous is not None:
        previous.tail = element.tail
    
    parent.remove(element)

def createElementAfter(previous, tag):
    parent = previous.getparent()
    index = parent.index(previous) + 1
    
    element = etree.Element('%s%s' % (POM_NS_PREFIX, tag))
    element.tail = previous.tail
    previous.tail = parent.text
    parent.insert(index, element)

def addFields(cls, *fields):
    for field in fields:
        def getter(self, field=field):
            return text(self._pomElement, field)
        
        def setter(self, value, field=field):
            elem = getattr(self._pomElement, field)
            elem._setText(value)
        
        setattr(cls, 'get_%s' + field, getter)
        setattr(cls, 'set_%s' + field, setter)
        setattr(cls, field, property(getter,setter))

def text(elem, child=None):
    if elem is None:
        return None
    
    if child:
        elem = getattr(elem, child)
    
    return None if elem is None else elem.text

class Dependency(object):
    def __init__(self, pomElement):
        self._pomElement = pomElement
    
    def __repr__(self):
        return '%s:%s:%s' % (self.groupId, self.artifactId, self.version)
    
    def key(self):
        return '%s:%s:%s' % (self.groupId, self.artifactId, self.version)
    
    def __eq__(self, other):
        return ((self.groupId, self.artifactId, self.version) ==
                (other.groupId, other.artifactId, other.version))
    
    def remove(self):
        removeElement(self._pomElement)
    
    def get_optional(self):
        elem = getattr(self._pomElement, 'optional')
        if elem is None:
            return False
        
        return elem.text == 'true'

    def set_optional(self, value):
        elem = self._pomElement.optional
        if value:
            if elem is None:
                previous = self._pomElement.version
                createElementAfter(previous, 'optional')
            
            self._pomElement.optional.text = 'true'
        else:
            if elem is not None:
                removeElement(elem)
        
    optional = property(get_optional, set_optional)

    def get_scope(self):
        return text(self._pomElement, 'scope')

    def set_scope(self, value):
        elem = self._pomElement.scope
        if value:
            if elem is None:
                previous = self._pomElement.version
                createElementAfter(previous, 'scope')
            
            self._pomElement.scope.text = value
        else:
            if elem is not None:
                removeElement(elem)
        
    scope = property(get_scope, set_scope)

addFields(Dependency, 'groupId', 'artifactId', 'version')

class Profile(object):
    def __init__(self, pomElement):
        self._pomElement = pomElement
    
    def __repr__(self):
        return 'profile<%s>' % (self.id,)
    
    def key(self):
        return self.id
    
    def __eq__(self, other):
        return self.id == other.id
    
    def activeByDefault(self, bool):
        activation = getOrCreate(self._pomElement, 'activation')
        activeByDefault = getOrCreate(activation, 'activeByDefault')
        activeByDefault._setText( 'true' if bool else 'false' )

    def dependencies(self):
        '''Get a list of dependencies of this POM'''
        deps = self._pomElement.dependencies
        
        result = getattr(deps, 'dependency')
        if result is None:
            return []
        
        return [Dependency(d) for d in result]

    def addDependency(self, d):
        if isinstance(d, Dependency):
            d = d._pomElement
        
        objectify.deannotate(d)
        etree.cleanup_namespaces(d)

        self._pomElement.dependencies.append(d)

addFields(Profile, 'id')

def createNewProfile(profiles, profileId):
    xml = etree.SubElement(profiles, 'profile')
    etree.SubElement(xml, 'id')
    
    profile = Profile(xml)
    profile.id = profileId
    profile.activeByDefault(False)

    etree.SubElement(xml, 'dependencies')
    
    return profile

def getOrCreate(elem, childName):
    child = getattr(elem, POM_NS_PREFIX+childName, None)
    if child is None:
        #print 'Create child',childName,'in',elem
        #print elem.getchildren()
        child = etree.SubElement(elem, POM_NS_PREFIX+childName)
    return child

class Pom(object):
    def __init__(self, pomFile):
        self.pomFile = pomFile
        
        try:
            parser = objectify.makeparser(resolve_entities=False, recover=True)
            self.xml = objectify.parse(self.pomFile, parser=parser)
        except:
            print 'Error parsing %s' % self.pomFile
            raise
        
        self.project = self.xml.getroot()
        #print dir(self.project)
        #print(isinstance(self.project, objectify.ObjectifiedElement))
        assert self.project.tag == POM_NS_PREFIX+'project', 'Expected <project> as root element but was %s' % (self.project.tag,)
        
        #print self.project.groupId
    
    def key(self):
        '''groupId:artifactId:version'''
        return '%s:%s:%s' % (text(self.project.groupId), text(self.project.artifactId), text(self.project.version))
    
    def artifactIdVersion(self):
        '''artifactId:version (without groupId)'''
        return '%s:%s' % (text(self.project.artifactId), text(self.project.version))
    
    def shortKey(self):
        '''groupId:artifactId (without version)'''
        return '%s:%s' % (text(self.project.groupId), text(self.project.artifactId))
    
    def files(self):
        '''Get a list of file types that are available for this artifact. This is usually [jar, pom] or [jar, pom, sources].'''
        path = os.path.dirname(self.pomFile)
        l = os.listdir(path)
        
        files = []
        prefix = '%s-%s' % (text(self.project.artifactId), text(self.project.version))
        for item in l:
            if not item.startswith(prefix) or item.endswith('.bak'):
                continue
            
            item = item[len(prefix):]
            if item.startswith('.'):
                item = item[1:]
            if item.startswith('-') and item.endswith('.jar'):
                item = item[1:-4]
            
            files.append(item)
        
        files.sort()
        return files
    
    def dependencies(self):
        '''Get a list of dependencies of this POM'''
        deps = getattr(self.project, 'dependencies', None)
        if deps is None:
            return []
        
        result = getattr(deps, 'dependency')
        if result is None:
            return []
        
        return [Dependency(d) for d in result]

    def profile(self, profileId):
        profiles = getOrCreate(self.project, 'profiles')
        
        l = getattr(profiles, 'profile', [])
        for profile in l:
            if profile.id.text == profileId:
                return Profile(profile)
        
        return createNewProfile(profiles, profileId)

    def __repr__(self):
        return etree.tostring(self.xml, pretty_print=True)

    def save(self, fileName=None):
        '''Save this POM to a file
        
        Of the file already exists, a backup is created.'''
        if not fileName:
            fileName = self.pomFile
        
        tmp = '%s.tmp' % fileName
        bak = '%s.bak' % fileName
        
        if os.path.exists(tmp):
            os.remove(tmp)
        
        objectify.deannotate(self.xml)
        etree.cleanup_namespaces(self.xml)
        
        deps = getattr(self.project, 'dependencies', None)
        if deps is not None and len(deps) == 0:
            self.project.dependencies.remove()
        
        self.xml.write(tmp, encoding="UTF-8", pretty_print=True)
        
        if os.path.exists(fileName):
            os.rename(fileName, bak)
            
        os.rename(tmp, fileName)
    