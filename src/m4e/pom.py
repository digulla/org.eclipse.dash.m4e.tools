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

import os
import os.path
import types
from lxml import etree
# TODO Evaluate objectify
#from lxml import objectify

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

class PomElement(object):
    def __init__(self, tree, element):
        self.tree = tree
        self.xml_element = element
    
    def __getattr__(self, name):
        expr = etree.ETXPath('{%s}%s' % (POM_NS, name))
        #print expr
        result = expr(self.xml_element)
        #print '%s[%s] = %s' % (self, name, result)

        # Wrap the XML elements        
        result = [PomElement(self.tree, x) for x in result]
        
        # Special case for single or no children 
        if len(result) == 0:
            result = None
        elif len(result) == 1:
            result = result[0]
        
        return result
    
    def __repr__(self):
        return xmlPath(self.xml_element)

def removeElement(element):
    parent = element.getparent()
    index = parent.index(element)
    
    previous = element.getprevious()
    previous.tail = element.tail
    del parent[index]

def createElementAfter(previous, tag):
    parent = previous.getparent()
    index = parent.index(previous) + 1
    
    element = etree.Element('%s%s' % (POM_NS_PREFIX, tag))
    element.tail = previous.tail
    previous.tail = parent.text
    parent.insert(index, element)

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
    
    def get_groupId(self):
        return text(self._pomElement.groupId)
    
    def set_groupId(self, groupId):
        self._pomElement.groupId.xml_element.text = groupId

    groupId = property(get_groupId, set_groupId)

    def get_artifactId(self):
        return text(self._pomElement.artifactId)
    
    def set_artifactId(self, artifactId):
        self._pomElement.artifactId.xml_element.text = artifactId

    artifactId = property(get_artifactId, set_artifactId)

    def get_version(self):
        return text(self._pomElement.version)
    
    def set_version(self, version):
        self._pomElement.version.xml_element.text = version

    version = property(get_version, set_version)
    
    def get_optional(self):
        elem = self._pomElement.optional
        if elem is None:
            return False
        
        return elem.xml_element.text == 'true'

    def set_optional(self, value):
        elem = self._pomElement.optional
        if value:
            if elem is None:
                previous = self._pomElement.version
                createElementAfter(previous, 'optional')
            
            self._pomElement.optional.xml_element.text = 'true'
        else:
            if elem is not None:
                removeElement(elem.xml_element)
        
    optional = property(get_optional, set_optional)

    def get_scope(self):
        elem = text(self._pomElement.scope)

    def set_scope(self, value):
        elem = self._pomElement.scope
        if value:
            if elem is None:
                previous = self._pomElement.version
                createElementAfter(previous.xml_element, 'scope')
            
            self._pomElement.scope.xml_element.text = value
        else:
            if elem is not None:
                removeElement(elem.xml_element)
        
    scope = property(get_scope, set_scope)

def text(elem):
    return None if elem is None else elem.xml_element.text

class Pom(object):
    def __init__(self, pomFile):
        self.pomFile = pomFile
        
        try:
            parser = etree.XMLParser(resolve_entities=False, recover=True)
            self.xml = etree.parse(self.pomFile, parser=parser)
        except:
            print 'Error parsing %s' % self.pomFile
            raise
        
        self.project = PomElement(self.xml, self.xml.getroot())
    
    def key(self):
        return '%s:%s:%s' % (text(self.project.groupId), text(self.project.artifactId), text(self.project.version))
    
    def artifactIdVersion(self):
        return '%s:%s' % (text(self.project.artifactId), text(self.project.version))
    
    def shortKey(self):
        return '%s:%s' % (text(self.project.groupId), text(self.project.artifactId))
    
    def files(self):
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
        deps = self.project.dependencies
        if deps is None:
            return []
        
        result = deps.dependency
        if result is None:
            return []
        
        if type(result) != types.ListType:
            result = [result]
        
        return [Dependency(d) for d in result]

    def __repr__(self):
        return etree.tostring(self.xml, pretty_print=True)

    def save(self, fileName=None):
        if not fileName:
            fileName = self.pomFile
        
        tmp = '%s.tmp' % fileName
        bak = '%s.bak' % fileName
        
        if os.path.exists(tmp):
            os.remove(tmp)
        
        self.xml.write(tmp, encoding="UTF-8", pretty_print=True)
        
        if os.path.exists(fileName):
            os.rename(fileName, bak)
            
        os.rename(tmp, fileName)
    