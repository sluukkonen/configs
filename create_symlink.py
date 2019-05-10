#!/usr/bin/env python

import os

home = os.path.abspath(os.environ['HOME'])
path = os.path.abspath(os.path.dirname(__file__))

bin = os.path.join(home, 'bin')
local_bin = os.path.join(path, 'bin')

excludes = ['.gitignore', '.git', '.gitmodules', os.path.basename(__file__), 'bin', 'Brewfile']

def link_directory(srcdir, dstdir):
    for f in os.listdir(srcdir):
        if f not in excludes:
            src = os.path.abspath(os.path.join(srcdir, f))
            dst = os.path.join(dstdir, f)
            try:
                os.symlink(src, dst)
                print "ln -s %s %s" % (src, dst)
            except Exception, msg:
                pass

if not os.path.exists(bin):
    os.mkdir(bin)
    print "mkdir %s" % bin

link_directory(path, home)
link_directory(local_bin, bin)

