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

from m4e.pom import Pom, xmlPath
from m4e.patches import *

def test_PomReader():
    reader = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    eq_(types.StringType, type(reader.xml.getroot().tag))
    eq_('{http://maven.apache.org/POM/4.0.0}project', reader.xml.getroot().tag)
    eq_([], reader.xml.getroot().xpath('version'))
    
    eq_('/project', xmlPath(reader.project))
    eq_('/project/version', xmlPath(reader.project.version))
    eq_('2.6.2', reader.project.version.text)
    
def test_dependencies():
    pom = Pom('org.eclipse.birt.core-2.6.2.pom')
    
    eq_('/project/dependencies', xmlPath(pom.project.dependencies))
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
    
    eq_('[PatchSet(../patches/eclipse-3.6.2.patches), StripQualifiers()]', repr(tool.patches))

    x = tool.patches[0].patches
    eq_('[DependencyPatcher(63)]', repr(x))
    eq_('m4e.maven-central', tool.profile)
    eq_('m4e.orbit', tool.defaultProfile)
    x = x[0].replacements[0]
    eq_('ReplaceDependency(com.jcraft.jsch:com.jcraft.jsch:0.1.41 -> com.jcraft:jsch:0.1.41)', repr(x))

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
    loader.addRemoveNonOptional()
    loader.run()
    
    eq_('[RemoveNonOptional(), PatchSet(../patches/eclipse-3.6.2.patches), StripQualifiers()]', repr(loader.patches))
    
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
  <dependencies/>
  <profiles>
    <profile>
      <id>m4e.orbit</id>
      <activation>
        <activeByDefault>true</activeByDefault>
      </activation>
      <dependencies>
        <dependency>
          <groupId>org.mozilla.javascript</groupId>
          <artifactId>org.mozilla.javascript</artifactId>
          <version>[1.6.0,2.0.0)</version>
          <optional>false</optional>
        </dependency>
      </dependencies>
    </profile>
    <profile>
      <id>m4e.maven-central</id>
      <dependencies>
        <dependency>
          <groupId>rhino</groupId>
          <artifactId>js</artifactId>
          <version>1.7R2</version>
${opt}
        </dependency>
      </dependencies>
    </profile>
  </profiles>
</project>
'''

def test_patchScope():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test')
    tool = DependencyPatcher('m4e.orbit', 'm4e.maven-central', [op], [])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY.replace('${opt}', '          <scope>test</scope>')
    compareStrings(expected, repr(pom))

def test_patchScope_2():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test:optional=true')
    tool = DependencyPatcher('m4e.orbit', 'm4e.maven-central', [op], [])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY.replace('${opt}', '          <optional>true</optional>\n          <scope>test</scope>')
    compareStrings(expected, repr(pom))

def test_patchScope_3():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = ReplaceDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)', 'rhino:js:1.7R2:scope=test:optional=false')
    tool = DependencyPatcher('m4e.orbit', 'm4e.maven-central', [op], [])
    
    tool.run(pom)
    
    expected = POM_WITH_RHINO_DEPENDENCY.replace('${opt}', '          <scope>test</scope>')
    compareStrings(expected, repr(pom))

def test_patchDelete():
    pom = Pom(StringIO.StringIO(POM_WITH_JAVASCRIPT_DEPENDENCY))
    
    op = DeleteDependency('org.mozilla.javascript:org.mozilla.javascript:[1.6.0,2.0.0)')
    tool = DependencyPatcher(None, None, [], [op])
    
    tool.run(pom)

    print repr(pom)    
    compareStrings('''<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <dependencies/>
</project>
''', repr(pom))

def test_noDependencies():
    xml = '<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd"></project>'
    pom = Pom(StringIO.StringIO(xml))
    
    eq_([], pom.dependencies())

def test_stripQualifier():
    pom = Pom('org.eclipse.persistence.moxy-2.1.2.pom')
    
    StripQualifiers().run(pom)
    with open('org.eclipse.persistence.moxy-2.1.2.fixed') as fh:
        expected = fh.read()
    
    compareStrings(expected, repr(pom))

def test_stripQualifier2():
    compareStrings('1', StripQualifiers().stripQualifier('1'))

def test_stripQualifier3():
    compareStrings('1.0', StripQualifiers().stripQualifier('1.0'))

def test_stripQualifier4():
    compareStrings('1.3.2', StripQualifiers().stripQualifier('1.3.2'))

def test_stripQualifier5():
    compareStrings('', StripQualifiers().stripQualifier(''))

def test_stripQualifier6():
    compareStrings('[2.5.0,3.0.0)', StripQualifiers().stripQualifier('[2.5.0.v200906151043,3.0.0)'))

def test_stripQualifier7():
    compareStrings('[0,)', StripQualifiers().stripQualifier('[0,)'))

def test_stripQualifier8():
    compareStrings('[2.6.2,3.0)', StripQualifiers().stripQualifier('[2.6.2,3.0)'))

def test_stripQualifier8():
    compareStrings('[3.6.1,4)', StripQualifiers().stripQualifier('[3.6.1,4)'))
