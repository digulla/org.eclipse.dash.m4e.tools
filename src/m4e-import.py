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
'''
Utility to unpack archives downloaded from eclipse.org
and import the plug-ins into a Maven 2 repository.

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import sys
import os.path
import shutil
import logging
from m4e.common import configLogger, userNeedsHelp

workDir = os.path.abspath('../tmp')

VERSION = '0.9 (07.04.2011)'
MVN_VERSION = '3.0.3'

log = logging.getLogger('m4e.import')

def download(url, path):
    '''Download the resource to a local path'''
    import urllib2
    
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    
    input = urllib2.urlopen(url)
    try: 
        with open(path, 'w') as output:
            while True:
                data = input.read(10240)
                if not data: break
                output.write(data)
    finally:
        input.close()

m3archive = 'apache-maven-%s-bin.tar.gz' % MVN_VERSION
m3home = os.path.join(workDir, 'apache-maven-%s' % MVN_VERSION)
m3exe = os.path.join(m3home, 'bin', 'mvn')

def downloadMaven3():
    '''Download Maven 3 if necessary'''
    path = os.path.join(workDir, m3archive)
    if os.path.exists(path):
        log.debug('Maven 3 was already downloaded at %s' % path)
        return
    
    downloadUrl = 'http://mirror.switch.ch/mirror/apache/dist//maven/binaries/' + m3archive
    
    log.info('Downloading Maven 3...')
    download(downloadUrl, path)
    log.info('OK')

def unpackMaven3():
    '''Unpack the downloaded Maven 3 archive'''
    archivePath = os.path.join(workDir, m3archive)
    unpackedPath = 'apache-maven-%s' % MVN_VERSION
    
    path = os.path.join(workDir, unpackedPath)
    if os.path.exists(path):
        log.debug('Maven 3 was already unpacked at %s' % path)
        return
    
    import tarfile
    
    log.info('Unpacking Maven 3 archive')
    archive = tarfile.open(archivePath, 'r:*')
    archive.extractall(workDir)
    log.info('OK')

def downloadArchive(archive):
    '''Download an archive via HTTP.
    If the value of archive is not a URL, do nothing.
    
    This function returns the name of the downloaded file.
    '''
    if not archive.startswith('http://'):
        log.debug("Archive URL %s seems to be local" % archive)
        return archive
    
    basename = os.path.basename(archive)
    path = os.path.join(workDir, basename)
    
    if os.path.exists(path):
        log.debug('Archive %s has already been downloaded' % path)
        return path
    
    log.info('Downloading %s to %s' % (archive, path))
    download(archive, path)
    log.info('OK')
    
    return path

archiveExtensions=('.tar.gz', '.tar.bz2', '.zip')

def unpackArchive(archive):
    '''Unpack an archive for import'''
    
    # If the archive is already unpacked, use the directory
    if os.path.isdir(archive):
        log.debug('Archive %s is a directory; no need to unpack' % archive)
        return archive
    
    dirName = os.path.basename(archive)
    
    for ext in archiveExtensions:
        if dirName.endswith(ext):
            dirName = dirName[:-len(ext)]
    
    path = os.path.join(workDir, dirName)
    if os.path.exists(path):
        log.debug('Archive %s is already unpacked at %s' % (archive, path))
        return path
    
    log.info('Unpacking %s' % (archive,))
    
    if archive.endswith('.zip'):
        unpackZipArchive(archive, path)
    else:
        import tarfile
        
        archive = tarfile.open(archive, 'r:*')
        archive.extractall(path)
    
    log.info('OK')
    
    return path

def unpackZipArchive(archive, path):
    import zipfile

    archive = zipfile.ZipFile(archive, 'r')
    # For some reason, extractall() doesn't work on maven.eclipse.org
    for info in archive.infolist():
        log.debug('%s %s %s %s' % (info.filename, info.compress_type, info.extract_version, info.file_size))
        if info.filename[0] == '/' or info.filename.startswith('../') or '/../' in info.filename:
            log.warning('Skipped suspicious entry "%s"' % info.filename)
            continue
        
        if info.filename[-1] == '/':
            dest = os.path.join(path, info.filename)
            os.makedirs(dest)
        else:
            archive.extract(info.filename, path)

def locate(root, pattern):
    '''Locate a directory which contains a certain file.'''
    names = os.listdir(root)
    
    if pattern in names:
        return root
    
    for name in names:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            result = locate(path, pattern)
            if result:
                return result
    
    return None


class ImportTool(object):
    def __init__(self, path, logFile):
        self.path = path
        self.logFile = logFile
        
        self.eclipseFolder = locate(self.path, 'plugins')
        if not self.eclipseFolder:
            raise IOError("Can't locate plug-ins in %s" % self.path)
            return
        
        self.tmpHome = self.path + '_home'
        self.m2dir = os.path.join(self.tmpHome, '.m2')
        self.m2repo = os.path.join(self.tmpHome, 'm2repo')
        self.m2settings = os.path.join(self.m2dir, 'settings.xml')

    def run(self):
        log.info('Importing plug-ins from %s into %s' % (self.eclipseFolder, self.m2repo))
    
        self.clean()
        self.writeSettings()
        
        log.info('Analysing Eclipse plugins...')
        self.doImport()

        log.info('OK')
        
    def doImport(self):
        args = self.args()
        env = self.env()
        
        log.debug('Arguments: %s\n' % (args,))
        log.debug('M2_HOME: %s\n' % env['M2_HOME'])
        
        import subprocess

        child = subprocess.Popen(args, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        self.wait(child)
        child.wait()
        
        rc = child.returncode
        if rc != 0:
            log.error("Arguments: %s" % (args,))
            log.error("Log file: %s" % self.logFile )
            raise RuntimeError("Importing the plug-ins from %s failed with RC=%d" % (self.eclipseFolder, rc))
    
    def wait(self, child):
        import re
        partPattern = re.compile(r'[/\\]')
        
        for line in child.stdout:
            log.debug( 'child: %s' % line.rstrip())
            
            if line.startswith('[INFO] Processing '):
                parts = line.split(' ')
                if parts[2] != 'file':
                    #print parts
                    min, max = parts[2], parts[4].strip()
            elif line.startswith('[INFO] Installing ') and line.endswith('.jar\n'):
                parts = line.split(' ')
                path = parts[-1].strip()
                path = path[len(self.m2repo)+1:]
                path = os.path.dirname(path)
                
                version = os.path.basename(path)
                
                path = os.path.dirname(path)
                
                artifactId = os.path.basename(path)
                
                groupId = os.path.dirname(path)
                groupId = partPattern.sub('.', groupId)
                
                msg1 = 'Installing %s of %s ' % (min, max)
                msg2 = '%s:%s:%s' % (groupId, artifactId, version)
                
                if len(msg1) + len(msg2) > 79:
                    rest = 79 - len(msg1)
                    msg2 = msg2[-rest:]
                
                msg = msg1 + msg2 + ' '*80
                msg = msg[:80] + '\r'
                
                sys.stdout.write(msg)
                sys.stdout.flush()
        
        print('')
    
    def writeSettings(self):
        with open(self.m2settings, 'w') as fh:
            fh.write('''\
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                      http://maven.apache.org/xsd/settings-1.0.0.xsd">
  <localRepository>%s</localRepository>
  <interactiveMode/>
  <usePluginRegistry/>
  <offline/>
  <pluginGroups/>
  <servers/>
  <mirrors/>
  <proxies/>
  <profiles>
  </profiles>
  <activeProfiles/>
</settings>
''' % (self.m2repo,)
        );
        
    def clean(self):
        '''Make sure we don't have any leftovers from previous attempts.'''
        if os.path.exists(self.tmpHome):
            log.info('Cleaning up from last run...')
            shutil.rmtree(self.tmpHome)
        
        os.makedirs(self.m2dir)

        if os.path.exists(templateRepo):
            log.info('Copying template...')
            shutil.copytree(templateRepo, self.m2repo)

    def args(self):
        return (
            m3exe,
            'eclipse:make-artifacts',
            '-DstripQualifier=true',
            '-DeclipseDir=%s' % self.eclipseFolder,
            '--settings', self.m2settings,
            '-X',
        )

    def env(self):
        env = dict(os.environ)
        env['M2_HOME'] = m3home
        return env

    
def importIntoTmpRepo(path, logFile):
    tool = ImportTool(path, logFile)
    tool.run()
    return tool

primingArchive=os.path.join(workDir,'..','data','priming.tar.gz')
templateRepo=os.path.join(workDir,'priming_home','m2repo')

def loadNecessaryPlugins(logFile):
    '''We want to avoid downloading the Maven plug-ins all the time.
    
    Therefore, we create a template repository which contains the
    necessary plug-ins, so we can copy them later.
    '''
    if os.path.exists(templateRepo):
        return
    
    log.info('Downloading necessary plug-ins for Maven 3')
    archive = downloadArchive(primingArchive)
    path = unpackArchive(archive)
    importIntoTmpRepo(path, logFile)
    
    eclipseDir = os.path.join(templateRepo, 'org', 'eclipse')
    
    # Save one JAR which the Maven Eclipse Plugin needs
    backupDir = os.path.join(templateRepo, '..', 'backup', 'resources')
    if not os.path.exists(backupDir):
        shutil.copytree(os.path.join(eclipseDir, 'core', 'resources'), backupDir)
    
    # Delete everything
    shutil.rmtree(eclipseDir)
    
    # Restore what we saved above
    shutil.copytree(backupDir, os.path.join(eclipseDir, 'core', 'resources'))
    
    log.info('OK')

def deleteCommonFiles(folder, mask):
    #print 'deleteCommonFiles',folder,mask
    names = os.listdir(folder)
    names.sort()
    
    toDelete = set(os.listdir(mask))
    
    isEmpty = True
    
    for name in names:
        if not name in toDelete:
            isEmpty = False
            continue
        
        path = os.path.join(folder, name)
        #print 'Common',path
        if os.path.isdir(path):
            empty = deleteCommonFiles(path, os.path.join(mask, name))
            
            if empty:
                #print 'Deleting empty dir',path
                os.rmdir(path)
            else:
                isEmpty = False
        else:
            #print 'Deleting file',path
            os.remove(path)
    
    return isEmpty

mavenFiles = set(('maven-metadata-local.xml', '_maven.repositories'))

def deleteMavenFiles(folder):
    names = os.listdir(folder)
    
    for name in names:
        path = os.path.join(folder, name)
        
        if os.path.isdir(path):
            deleteMavenFiles(path)
        elif name in mavenFiles:
            os.remove(path)

def main(name, argv):
    logFile = os.path.join(workDir, 'm4e-import.log')
    configLogger(logFile)
    
    log.info('%s %s' % (name, VERSION))
    log.debug('workDir=%s' % os.path.abspath(workDir))
    if userNeedsHelp(argv):
        print('Usage: %s <archives...>')
        print('')
        print('Import the set of archives into Maven 2 repositories in')
        print(workDir)
        return
    
    downloadMaven3()
    unpackMaven3()
    loadNecessaryPlugins(logFile)
    
    for archive in argv:
        archive = downloadArchive(archive)
        path = unpackArchive(archive)
        tool = importIntoTmpRepo(path, logFile)
        
        m2repo = tool.m2repo
        log.info('Deleting non-Eclipse artifacts...')
        deleteCommonFiles(m2repo, templateRepo)
        log.info('OK')
        
        deleteMavenFiles(m2repo)
        
if __name__ == '__main__':
    try:
        main(sys.argv[0], sys.argv[1:])
    except Exception as e:
        log.error('%s' % e)
        raise
        
