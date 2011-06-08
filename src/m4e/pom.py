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
import StringIO
from lxml import etree, objectify

POM_NS = 'http://maven.apache.org/POM/4.0.0'
POM_NS_PREFIX = '{%s}' % POM_NS
NAMESPACES = {
    'pom': POM_NS,
}

def xmlPath(element):
    '''Return a simple, unambiguous path for an XML element'''
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
    '''Remove an element from a document keeping the formatting intact'''
    parent = element.getparent()
    
    previous = element.getprevious()
    if previous is not None:
        previous.tail = element.tail
    
    parent.remove(element)

def createElementAfter(parent, previousName, tag):
    '''Add an element after a sibling or append it if the sibling doesn't exist'''
    if previousName is None:
        return etree.SubElement(parent, '%s%s' % (POM_NS_PREFIX, tag))
    
    previous = getattr(parent, previousName, None)
    if previous is None:
        index = len(parent)
        previous = parent[index-1]
    else:
        index = parent.index(previous) + 1
    
    element = etree.Element('%s%s' % (POM_NS_PREFIX, tag))
    element.tail = previous.tail
    previous.tail = parent.text
    parent.insert(index, element)

def addFields(cls, *fields):
    '''Add property access for text elements in a DOM to a class'''
    for field in fields:
        def getter(self, field=field):
            return text(self.xml(), field)
        
        def setter(self, value, field=field):
            elem = getattr(self.xml(), field)
            elem._setText(value)
        
        setattr(cls, 'get_%s' + field, getter)
        setattr(cls, 'set_%s' + field, setter)
        setattr(cls, field, property(getter,setter))

def text(elem, child=None):
    '''Get the text of an XML element or None if the element or the child doesn't exist'''
    if elem is None:
        return None
    
    if child:
        elem = getattr(elem, child, None)
    
    return None if elem is None else elem.text

def setOptionalText(parent, elemName, value, previousName=None):
    '''Create a text element if it doesn't exist, 
    change the text of an existing text element or
    delete a text element (if value is None).
    
    If the text element needs to be created, it will be inserted
    after the sibling previousName'''
    child = getattr(parent, elemName, None)
    if value:
        if child is None:
            child = createElementAfter(parent, previousName, elemName)
        
        if child is None:
            raise RuntimeError("Can't create child %s of %s" % (elemName, xmlPath(parent)))
        
        child._setText(unicode(value))
    else:
        if child is not None:
            removeElement(child)

class Dependency(object):
    '''This class maps the standard fields of a Maven 2 dependency between Python and XML'''
    def __init__(self, pomElement):
        self._pomElement = pomElement
    
    def __repr__(self):
        return '%s:%s:%s' % (self.groupId, self.artifactId, self.version)
    
    def key(self):
        return '%s:%s:%s' % (self.groupId, self.artifactId, self.version)
    
    def __eq__(self, other):
        return ((self.groupId, self.artifactId, self.version) ==
                (other.groupId, other.artifactId, other.version))
    
    def xml(self):
        return self._pomElement
    
    def remove(self):
        removeElement(self._pomElement)
    
    def get_optional(self):
        return text(self._pomElement, 'optional') == 'true'

    def set_optional(self, value):
        value = 'true' if value else None
        setOptionalText(self._pomElement, 'optional', value, 'version')
        
    optional = property(get_optional, set_optional)

    def get_scope(self):
        return text(self._pomElement, 'scope')

    def set_scope(self, value):
        setOptionalText(self._pomElement, 'scope', value, 'version')
        
    scope = property(get_scope, set_scope)

# Add the standard cases
addFields(Dependency, 'groupId', 'artifactId', 'version')

class Profile(object):
    '''This class offers support for Maven 2 profile elements'''
    def __init__(self, pomElement):
        self._pomElement = pomElement
    
    def __repr__(self):
        return 'profile<%s>' % (self.id,)
    
    def key(self):
        return self.id
    
    def __eq__(self, other):
        return self.id == other.id
    
    def xml(self):
        return self._pomElement
    
    def activeByDefault(self, bool):
        activation = getOrCreate(self._pomElement, 'activation')
        activeByDefault = getOrCreate(activation, 'activeByDefault')
        activeByDefault._setText( 'true' if bool else 'false' )

    def dependencies(self):
        '''Get a list of dependencies of this POM'''
        deps = getattr(self._pomElement, 'dependencies', None)
        if deps is None:
            return []
        
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

def getOrCreate(elem, childName):
    '''Get a child node by name. Create the child node if it doesn't exist.'''
    child = getattr(elem, POM_NS_PREFIX+childName, None)
    
    if child is None:
        #print 'Create child',childName,'in',elem
        #print elem.getchildren()
        child = etree.SubElement(elem, POM_NS_PREFIX+childName)
    return child

class Pom(object):
    '''Helper class to work with POM files'''
    def __init__(self, pomFile=None):
        self.pomFile = pomFile
        
        if self.pomFile:
            self.load()
    
            self.project = self.xml.getroot()
            #print type(self.xml)
            #print dir(self.project)
            #print(isinstance(self.project, objectify.ObjectifiedElement))
            assert self.project.tag == POM_NS_PREFIX+'project', '%s: Expected <project> as root element but was %s' % (self.pomFile, self.project.tag,)
        
            #print self.project.groupId
    
    def createNew(self):
        self.xml = objectify.parse(StringIO.StringIO('''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId/>
  <artifactId/>
  <version/>
</project>
'''))
        self.project = self.xml.getroot()
    
    def load(self):
        try:
            # This is necessary to parse POM files with HTML entities
            parser = objectify.makeparser(resolve_entities=False, recover=True)
            self.xml = objectify.parse(self.pomFile, parser=parser)
        except:
            print 'Error parsing %s' % self.pomFile
            raise
        
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
        
        result = getattr(deps, 'dependency', None)
        if result is None:
            return []
        
        return [Dependency(d) for d in result]

    def profile(self, profileId):
        '''Get a Profile instance by ID'''
        profiles = getOrCreate(self.project, 'profiles')
        
        l = getattr(profiles, 'profile', [])
        for profile in l:
            if profile.id.text == profileId:
                return Profile(profile)
        
        return self.createNewProfile(profiles, profileId)

    def profiles(self):
        profiles = getattr(self.project, 'profiles', None)
        if profiles is None:
            return []
        
        return [Profile(p) for p in profiles]

    def createNewProfile(self, profiles, profileId):
        xml = etree.SubElement(profiles, POM_NS_PREFIX+'profile')
        etree.SubElement(xml, POM_NS_PREFIX+'id')
        
        profile = Profile(xml)
        profile.id = profileId
        #profile.activeByDefault(False)
    
        etree.SubElement(xml, POM_NS_PREFIX+'dependencies')
        
        return profile

    def __repr__(self):
        return etree.tostring(self.xml, pretty_print=True)

    def save(self, fileName=None):
        '''Save this POM to a file
        
        Of the file already exists, a backup is created.'''
        if not fileName:
            fileName = self.pomFile
        
        tmp = '%s.tmp' % fileName
        bak = '%s.bak' % fileName
        
        dir = os.path.dirname(tmp)
        if not os.path.exists(dir):
            os.makedirs(dir)
        
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
    
def createPom(repoDir, groupId, artifactId, version):
    path = os.path.join(*groupId.split('.'))
    path = os.path.join(repoDir, path, artifactId, version)
    
    fileName = '%s-%s.pom' % (artifactId, version)
    path = os.path.join(path, fileName)
    
    pom = Pom()
    pom.createNew()
    pom.pomFile = path
    
    pom.project.groupId._setText(groupId)
    pom.project.artifactId._setText(artifactId)
    pom.project.version._setText(version)
    
    return pom
