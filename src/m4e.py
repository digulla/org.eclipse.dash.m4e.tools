'''
Utility to unpack archives downloaded from eclipse.org
and import the plug-ins into a Maven 2 repository.

Created on Mar 17, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import sys
import os.path

workDir = os.path.abspath('../tmp')

VERSION = '0.1 (17.03.2011)'
MVN_VERSION = '3.0.3'

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
        return
    
    downloadUrl = 'http://mirror.switch.ch/mirror/apache/dist//maven/binaries/' + m3archive
    
    print('Downloading Maven 3...')
    download(downloadUrl, path)
    print('OK')

def unpackMaven3():
    '''Unpack the downloaded Maven 3 archive'''
    archivePath = os.path.join(workDir, m3archive)
    unpackedPath = 'apache-maven-%s' % MVN_VERSION
    
    if os.path.exists(os.path.join(workDir, unpackedPath)):
        return
    
    import tarfile
    
    print('Unpacking Maven 3 archive')
    archive = tarfile.open(archivePath, 'r:*')
    archive.extractall(workDir)
    print('OK')

def downloadArchive(archive):
    '''Download an archive via HTTP.
    If the value of archive is not a URL, do nothing.
    
    This function returns the name of the downloaded file.
    '''
    if not archive.startswith('http://'):
        return archive
    
    basename = os.path.basename(archive)
    path = os.path.join(workDir, basename)
    
    if os.path.exists(path):
        return path
    
    print('Downloading %s to %s' % (archive, path))
    download(archive, path)
    print('OK')
    
    return path

archiveExtensions=('.tar.gz', '.tar.bz2', '.zip')

def unpackArchive(archive):
    '''Unpack an archive for import'''
    dirName = os.path.basename(archive)
    
    for ext in archiveExtensions:
        if dirName.endswith(ext):
            dirName = dirName[:-len(ext)]
    
    path = os.path.join(workDir, dirName)
    if os.path.exists(os.path.join(path)):
        return path
    
    import tarfile
    
    print('Unpacking %s' % (archive,))
    archive = tarfile.open(archive, 'r:*')
    archive.extractall(path)
    print('OK')
    
    return path

def locate(root, pattern):
    '''Locate a directory which contains a certain file.'''
    names = os.listdir(root)
    
    if pattern in names:
        return root
    
    for name in names:
        path = os.path.join(root, name)
        if os.path.isdir(path):
            result = locate(path, pattern)
            if result: return result
    
    return None


class ImportTool(object):
    def __init__(self, path):
        self.path = path
        
        self.eclipseFolder = locate(self.path, 'plugins')
        if not self.eclipseFolder:
            raise IOError("Can't locate plug-ins in %s" % self.path)
            return
        
        self.tmpHome = self.path + '_home'
        self.m2dir = os.path.join(self.tmpHome, '.m2')
        self.m2repo = os.path.join(self.tmpHome, 'm2repo')
        self.m2settings = os.path.join(self.m2dir, 'settings.xml')
        self.logFile = self.path + '.log'

    def run(self):
        self.clean()
        self.writeSettings()
        
        print('Importing plug-ins from %s into %s' % (self.eclipseFolder, self.m2repo))
    
        with open(self.logFile, 'w') as log:
            self.doImport(log)

        print('OK')
        
    def doImport(self, log):
        args = self.args()
        env = self.env()
        
        log.write('Arguments: %s\n' % (args,))
        log.write('M2_HOME: %s\n' % env['M2_HOME'])
        log.write('\n\n\n')
        log.flush()
        
        import subprocess

        child = subprocess.Popen(args, 
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            close_fds=True,
            env=env,
            bufsize=1,
            universal_newlines=True
        )
        self.wait(child, log)
        child.wait()
        
        rc = child.returncode
        if rc != 0:
            print("Arguments: " + args )
            print("Log file: " + self.logFile )
            raise RuntimeError("Importing the plug-ins from %s failed with RC=%d", (self.eclipseFolder, rc))
    
    def wait(self, child, log):
        import re
        partPattern = re.compile(r'/\\')
        
        for line in child.stdout:
            log.write(line)
            
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
                
                msg = 'Installing %s of %s %s:%s:%s' % (min, max, groupId, artifactId, version) + ' '*80
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
        import shutil
        if os.path.exists(self.tmpHome):
            shutil.rmtree(self.tmpHome)
        
        os.makedirs(self.m2dir)

        if os.path.exists(templateRepo):
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

    
def importIntoTmpRepo(path):
    tool = ImportTool(path)
    tool.run()

primingArchive=os.path.join(workDir,'..','data','priming.tar.gz')
templateRepo=os.path.join(workDir,'priming_home','m2repo')

def loadNecessaryPlugins():
    '''We want to avoid downloading the Maven plug-ins all the time.
    
    Therefore, we create a template repository which contains the
    necessary plug-ins, so we can copy them later.
    '''
    if os.path.exists(templateRepo):
        return
    
    print('Downloading necessary plug-ins for Maven 3')
    archive = downloadArchive(primingArchive)
    path = unpackArchive(archive)
    importIntoTmpRepo(path)
    
    import shutil
    shutil.rmtree(os.path.join(templateRepo, 'org', 'eclipse'))
    
    print('OK')

def main(name, argv):
    downloadMaven3()
    unpackMaven3()
    loadNecessaryPlugins()
    
    for archive in argv:
        archive = downloadArchive(archive)
        path = unpackArchive(archive)
        importIntoTmpRepo(path)
    
if __name__ == '__main__':
    main(sys.argv[0], sys.argv[1:])