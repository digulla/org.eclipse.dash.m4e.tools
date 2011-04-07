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
Test cases for m4e-apply-patches

Created on Apr 7, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import unittest
import types
from nose.tools import eq_
import sys
import codecs
import difflib
import StringIO

sys.path.append('../src')

from m4e.pom import Pom
from m4e.patches import RemoveNonOptional, PatchLoader, PatchTool, dependencyFromString, ReplaceDependency, DependencyPatcher

def test_PomReader():
    reader = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    eq_(types.StringType, type(reader.xml.getroot().tag))
    eq_('{http://maven.apache.org/POM/4.0.0}project', reader.xml.getroot().tag)
    eq_([], reader.xml.getroot().xpath('version'))
    
    eq_('/project', repr(reader.project))
    eq_('/project/version', repr(reader.project.version))
    eq_('2.6.2', reader.project.version.xml_element.text)
    
def test_dependencies():
    pom = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    eq_('/project/dependencies', repr(pom.project.dependencies))
    eq_('[org.eclipse.core:org.eclipse.core.runtime:[3.2.0,4.0.0), org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0), com.ibm.icu:com.ibm.icu:[4.2.1,5.0.0)]', repr(pom.dependencies()))

def readFile(fileName, encoding='UTF-8'):
    with codecs.open(fileName, 'r', encoding) as fh:
        return fh.readlines()

def compareFiles(expected, actual):
    expectedData = readFile(expected)
    actualData = readFile(actual)
    
    diff = difflib.unified_diff(expectedData, actualData, expected, actual, n=3)
    
    diff = ''.join(diff)
    print diff
    eq_("",diff)

def toLines(s):
    return ['%s\n' % line for line in s.split('\n')]

def compareStrings(expectedData, actualData):
    
    expectedData = toLines(expectedData)
    actualData = toLines(actualData)
    
    diff = difflib.unified_diff(expectedData, actualData, 'expected', 'actual', n=3)
    
    diff = ''.join(diff)
    print diff
    eq_("",diff)

def test_removeNonOptional():
    pom = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    tool = RemoveNonOptional()
    tool.run(pom)
    
    expected = 'withoutNonOptional.pom'
    tmp = '../tmp/%s' % expected
    pom.save(tmp)

    pos = repr(pom).find('<optional>false</optional>')
    eq_(-1, pos, 'POM still contains non-optional elements')
    
    compareFiles(expected, tmp)

def test_loadPatches():
    tool = PatchLoader('../patches')
    tool.run()
    
    eq_('[Patches(../patches/birt-2.6.2.patches)]', repr(tool.patches))

    x = tool.patches[0].patches
    eq_('[DependencyPatcher(1)]', repr(x))
    x = x[0].replacements
    eq_('[ReplaceDependency(org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0) -> rhino:js:1.7R2)]', repr(x))

def test_dependencyFromString():
    d = dependencyFromString('a:b:1.0')
    eq_('a:b:1.0', repr(d))

def test_dependencyFromString_2():
    d = dependencyFromString('a:b:1.0:optional=true')
    eq_('a:b:1.0:optional=True', repr(d))

def test_dependencyFromString_3():
    d = dependencyFromString('a:b:1.0:scope=test')
    eq_('a:b:1.0:scope=test', repr(d))

def test_dependencyFromString_4():
    d = dependencyFromString('a:b:1.0:scope=test:optional=true')
    eq_('a:b:1.0:optional=True:scope=test', repr(d))

def test_ApplyPatches():
    
    loader = PatchLoader('../patches')
    loader.patches.insert(0, RemoveNonOptional())
    loader.run()
    
    eq_('[RemoveNonOptional(), Patches(../patches/birt-2.6.2.patches)]', repr(loader.patches))
    
    pom = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    tool = PatchTool(loader.patches)
    tool.apply(pom)
    
    expected = 'patchedPom.pom'
    tmp = '../tmp/%s' % expected
    pom.save(tmp)

    compareFiles(expected, tmp)

POM_WITH_JAVASCRIPT_DEPENDENCY = '''\
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies>
    <dependency>
      <groupId>org.mozilla.javascript</groupId>
      <artifactId>org.mozilla.javascript</artifactId>
      <version>[1.6.0,2.0.0)</version>
      <optional>false</optional>
    </dependency>
  </dependencies>
</project>
'''

POM_WITH_RHINO_DEPENDENCY = '''\
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies>
    <dependency>
      <groupId>rhino</groupId>
      <artifactId>js</artifactId>
      <version>1.7R2</version>
      <scope>test</scope>
      <optional>false</optional>
    </dependency>
  </dependencies>
</project>
'''

def test_patchScope():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test')
    tool = DependencyPatcher([op])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY
    compareStrings(expected, repr(pom))

def test_patchScope_2():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test:optional=true')
    tool = DependencyPatcher([op])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY.replace('<optional>false</optional>', '<optional>true</optional>')
    compareStrings(expected, repr(pom))

def test_patchScope_3():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test:optional=false')
    tool = DependencyPatcher([op])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY.replace('      <optional>false</optional>\n', '')
    compareStrings(expected, repr(pom))
