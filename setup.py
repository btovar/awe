"""
This file is part of AWE
Copyright (C) 2012- University of Notre Dame
This software is distributed under the GNU General Public License.
See the file COPYING for details.
"""


from distutils.core import setup

import os
import glob

def get_executables():
    return glob.glob(os.path.join('scripts', '*'))

datafiles = glob.glob('*.tar.bz2')
datafiles.append('awe-ala.py')

setup( author       = "Badi' Abdul-Wahid",
       author_email = 'abdulwahidc@gmail.com',
       url          = 'https://bitbucket.org/badi/awe',
       name         = 'awe',
       packages     = ['awe'],
       scripts      = get_executables(),
       data_files   = datafiles,
       platforms    = ['Linux', 'Mac OS X'],
       description  = 'Adaptive Weighted Ensemble method using WorkQueue'
       )
