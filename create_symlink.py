#!/usr/bin/env python3

import filecmp
import os
import uuid

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

    if os.path.lexists(abspath):
        if os.path.islink(abspath):
            return

        if os.path.isfile(abspath) and filecmp.cmp(file, abspath, shallow=False):
            # Create the link before replacing the file so a failure cannot
            # leave the user without their existing config.
            temporary_path = "%s.symlink-%s" % (abspath, uuid.uuid4().hex)
            try:
                os.symlink(file, temporary_path)
                os.replace(temporary_path, abspath)
                print("ln -s %s %s (replaced identical file)" % (file, abspath))
            except OSError as error:
                if os.path.lexists(temporary_path):
                    os.unlink(temporary_path)
                print("Could not replace %s: %s" % (abspath, error))
            return

        print("%s already exists!" % abspath)
        return

    try:
        os.symlink(file, abspath)
        print("ln -s %s %s" % (file, abspath))
    except OSError as error:
        print("Could not link %s: %s" % (abspath, error))


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
