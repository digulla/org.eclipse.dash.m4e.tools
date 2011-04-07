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
Common code for m4e tools

Created on Apr 7, 2011

@author: Aaron Digulla <digulla@hepe.com>
'''

import logging
import logging.handlers
import sys
import os.path

def configLogger(fileName):
    #logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = []
    
    doRollover = os.path.exists(fileName) and os.stat(fileName).st_size > 0
    
    handler = logging.handlers.RotatingFileHandler(fileName, 
                                                   maxBytes=0, backupCount=5, encoding='UTF-8')
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s %(levelname)s %(name)s %(message)s'))
    handler.setLevel(logging.DEBUG)
    
    # Create a new log file each time the script is run
    if doRollover:
        handler.doRollover()
    
    root.addHandler(handler)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(fmt='%(message)s'))

    root.addHandler(handler)
