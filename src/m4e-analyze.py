#!/usr/bin/env python
# /*******************************************************************************
# * Copyright (c) 05.05.2011 Aaron Digulla.
# * All rights reserved. This program and the accompanying materials
# * are made available under the terms of the Eclipse Public License v1.0
# * which accompanies this distribution, and is available at
# * http://www.eclipse.org/legal/epl-v10.html
# *
# * Contributors:
# *    Aaron Digulla - initial API and implementation and/or initial documentation
# *******************************************************************************/
"""Tool to check an Maven 2 Repository for problems.

Created on May 5, 2011

@author: Aaron Digulla <digulla@hepe.com>
"""
import os
import sys
import time
import logging
from m4e.common import configLogger, mustBeDirectory, userNeedsHelp
from m4e.patches import PatchLoader, PatchTool
from m4e.pom import Pom
from m4e.rendersnake import *

VERSION = '0.1 (05.05.2011)'

log = logging.getLogger('m4e.analyze')

helpOptions = frozenset(('--help', '-h', '-help', '-?', 'help'))

class Problem(object):
    htmlTitle = 'Generic Problems'
    
    def __init__(self, pom, message):
        self.pom = pom
        self.message = message
    
    def __repr__(self):
        return 'POM %s: %s' % (self.pom.key(), self.message)
    
    def renderOn(self, html):
        html.div( A().class_( 'problem' ) ) \
        .write( 'POM ' ) \
        .span( A().class_( 'pom' ) ).write( self.pom.key() )._span() \
        .write( ' ' ) \
        .span( A().class_( 'message' ) ).write( self.message )._span() \
        ._div()

class ProblemWithDependency(Problem):
    htmlTitle = 'Problems With Dependencies'
    
    def __init__(self, pom, message, dependency):
        Problem.__init__(self, pom, message)
        
        self.dependency = dependency
    
    def __repr__(self):
        d = '' if self.dependency is None else ' (dependency: %s)' % self.dependency
        
        return 'POM %s: %s%s' % (self.pom.key(), self.message, d)
    
    def renderOn(self, html):
        html.div( A().class_( 'problem' ) ) \
        .write( 'POM ' ) \
        .span( A().class_( 'pom' ) ).write( self.pom.key() )._span() \
        .write( ' ' ) \
        .span( A().class_( 'message' ) ).write( self.message )._span()
        
        if self.dependency:
            html.write(' (dependency: ').span(A().class_('dependency')).write('%s' % self.dependency)._span().write(')')
        
        html._div()
    
class ProblemDifferentVersions(Problem):
    htmlTitle = 'Dependencies With Different Versions'
    
    def __init__(self, pom, versionBackRefs):
        Problem.__init__(self, pom, 'This dependency is referenced with different versions')
        
        self.versionBackRefs = versionBackRefs
    
    def __repr__(self):
        versions = list(self.versionBackRefs.keys())
        versions.sort()
                
        message = 'The dependency %s is referenced with %d different versions:\n' % (self.pom.key(),len(versions))
        
        for version in versions:
            message += '    Version "%s" is used in:\n' % version
            
            backRefs = self.versionBackRefs[version]
            backRefs.sort(key=lambda x: x.key())
            
            for pom in backRefs:
                message += '        %s\n' % pom.key()
        
        return message
    
    def renderOn(self, html):
        versions = list(self.versionBackRefs.keys())
        versions.sort()
        
        html.div( A().class_( 'problem' ) ) \
        .write( 'The dependency ' ) \
        .span( A().class_( 'dependency' ) ).write( self.pom.key() )._span() \
        .write( ' is referenced with %d different versions:' % len(versions) )
        
        html.ul()
        
        for version in versions:
            html.li().write( 'Version "' ).span(A().class_('version')).write(version)._span().write('" is used in:' )
            
            backRefs = self.versionBackRefs[version]
            backRefs.sort(key=lambda x: x.key())
            
            html.ul()
            
            for pom in backRefs:
                html.li().span(A().class_('pom')).write( pom.key() )._span()._li()
            
            html._ul()
            
            html._li()
        
        html._ul()
        html._div()

class MissingDependency(Problem):
    htmlTitle = 'Missing Dependencies'
    
    def __init__(self, key, dependencies):
        Problem.__init__(self, dependencies[0], 'Missing dependencies')
        
        self.key = key
        self.dependencies = dependencies
    
    def __repr__(self):
        message = "The dependency %s is used in %d POMs but I can't find it in this M2 repo:\n" % (self.key, len(self.dependencies))
        for d in self.dependencies:
            message += '    %s\n' % d.key()
        
        return message
    
    def renderOn(self, html):
        html.div( A().class_( 'problem' ) ) \
        .write( 'The dependency ' ) \
        .span( A().class_( 'dependency' ) ).write( self.key )._span() \
        .write( " is used in %d POMs but I can't find it in this M2 repo:" % len(self.dependencies) )
        
        html.ul()

        for d in self.dependencies:
            html.li().span(A().class_('pom')).write(d.key())._span()._li()
        
        html._ul()
        html._div()

class Analyzer(object):
    def __init__(self, repoDir):
        self.repoDir = repoDir
        self.pomFiles = []
        self.versions = {}
        self.versionBackRefs = {}
        self.problems = []
        self.pomByKey = {}
        self.dependencies = {}
        
        self.timestamp = time.localtime()
        self.htmlReportPath = repoDir + '-analysis-%s.html' % time.strftime('%Y%m%d-%H%M%S', self.timestamp)

    def run(self):
        log.info('Analyzing %s...' % self.repoDir)
        self.process(self.repoDir)
        
        log.info('Found %d POM files. Looking for problems...' % len(self.pomFiles))
        self.checks()
        
        log.info('Found %d problems. Generating report...' % len(self.problems))
        self.report()
    
    def checks(self):
        self.checkDifferentVersions()
        self.checkMissingDependencies()
    
    def checkDifferentVersions(self):
        '''Check the different versions which are used to locate a dependency.'''
        for key, versionBackRefs in self.versionBackRefs.items():
            if len(versionBackRefs) > 1:
                pom = self.pomByKey[key]
                
                self.newProblem(ProblemDifferentVersions(pom, versionBackRefs))
    
    def checkMissingDependencies(self):
        for key, dependencies in self.dependencies.items():
            pom = self.pomByKey.get(key, None)
            if not pom:
                self.newProblem(MissingDependency(key, dependencies))
    
    def process(self, root):
        for name in os.listdir(root):
            path = os.path.join(root, name)
            
            if os.path.isdir(path):
                self.process(path)
            elif path.endswith('.pom'):
                self.analyzePOM(path)
    
    def analyzePOM(self, pomFile):
        pom = Pom(pomFile)
        self.pomFiles.append( pom )
        log.debug('Analyzing %s %s' % (pomFile, pom.key()))
        
        shortKey = pom.shortKey()
        self.pomByKey[shortKey] = pom
        
        for d in pom.dependencies():
            key = d.groupId + ":" + d.artifactId
            dependencies = self.dependencies.setdefault(key, [])
            dependencies.append( pom )
            
            if not d.version or d.version == '[0,)':
                self.newProblem(ProblemWithDependency(pom, 'Missing version in dependency', d))
            
            versions = self.versions.setdefault(key, set())
            versions.add( d.version )

            versionBackRefs = self.versionBackRefs.setdefault(key, {})
            backRefs = versionBackRefs.setdefault(d.version, [])
            backRefs.append( pom )

    def newProblem(self, problem):
        self.problems.append(problem)

    def report(self):
        print "Found %d POM files" % len(self.pomFiles)
        print "Found %d problems" % len(self.problems)
        
        for p in self.problems:
            print p
        
        self.htmlReport()
    
    def htmlReport(self):
        log.info('Writing HTML report to %s' % self.htmlReportPath)
        with open(self.htmlReportPath, 'w') as out:
            html = HtmlCanvas(out)
            
            ts = time.strftime('%Y.%m.%d %H:%M:%S', self.timestamp)
            title = 'Analysis of %s (%s)' % (self.repoDir, ts)
            html.html().head().title().write( title )._title().write('\n')
            
            self.styles(html)
            
            html._head().write('\n').body().write('\n')
            
            html.h1().write( title )._h1()
            
            html.p().write( "Found %d POM files" % len(self.pomFiles) )._p()
            html.p().write( "Found %d problems" % len(self.problems) )._p()
            
            self.renderProblemsAsHtml(html)
            
            html._body().write('\n')._html().write('\n')

    def renderProblemsAsHtml(self, html):
        
        map = {}
        
        for p in self.problems:
            key = p.htmlTitle
            
            l = map.setdefault(key, [])
            l.append(p)
        
        keys = map.keys()
        keys.sort()
        
        html.h2().write( 'Table of Contents' )._h2()
        
        html.ul()
        index = 1
        for key in keys:
            html.li().a(A().href('#toc%d' % index)).write(key)._a()._li()
            index += 1
        html._ul()
        
        index = 1
        for key in keys:
            l = map[key]
            
            html.h2().a(A().name('toc%d' % index)).write(key)._a()._h2()
            index += 1
            
            for p in l:
                p.renderOn(html)
        

    def styles(self, html):
        html.style( A().type('text/css') ).write('\n')
        
        html.write( '.pom { font-weight: bold; color: #7F0055; font-family: monospace; }\n' )
        html.write( '.dependency { font-weight: bold; color: #55007F; font-family: monospace; }\n' )
        html.write( '.version { font-weight: bold; color: #007F55; font-family: monospace; }\n' )
        
        html._style().write('\n')

def main(name, argv):
    if userNeedsHelp(argv):
        print('%s %s' % (name, VERSION))
        print('Usage: %s <m2repo>')
        print('')
        print('Move the sources of Eclipse plugins to the right place')
        print('so Maven 2 can find them.')
        return

    repoDir = mustBeDirectory(argv[0])

    configLogger(repoDir + "-analyze.log")
    log.info('%s %s' % (name, VERSION))

    tool = Analyzer(repoDir)
    tool.run()
    
    log.info('Done.')

if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log.error('%s' % e)
        raise
