#!/usr/bin/env python3

import os

home = os.path.abspath(os.environ['HOME'])
path = os.path.abspath(os.path.dirname(__file__))

excludes = ['.gitignore', '.git', '.gitmodules', os.path.basename(
    __file__), 'init.sh', 'Brewfile', 'Brewfile.lock.json']


def ensure_directory(dir):
    relpath = os.path.relpath(dir, path)
    targetpath = os.path.join(home, relpath)
    if not os.path.exists(targetpath):
        os.mkdir(targetpath)
        print("mkdir %s" % targetpath)


def link_file(file):
    relpath = os.path.relpath(file, path)
    abspath = os.path.abspath(os.path.join(home, relpath))
    try:
        os.symlink(file, abspath)
        print("ln -s %s %s" % (file, abspath))
    except:
        if not os.path.islink(abspath):
            print("%s already exists!" % abspath)


def link_directory(dir):
    for file in os.listdir(dir):
        if file not in excludes:
            abspath = os.path.abspath(os.path.join(dir, file))
            if os.path.isfile(abspath):
                link_file(abspath)
            elif os.path.isdir(abspath):
                ensure_directory(abspath)
                link_directory(abspath)


link_directory(path)
