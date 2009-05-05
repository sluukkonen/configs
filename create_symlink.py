#!/usr/bin/env python
import os
home = os.path.abspath(os.environ['HOME'])
path = os.path.join(home, 'Downloads/configs') 
excludes = ['.gitignore', '.config', 'create_symlink.py', 'copy_config.sh'] 
for f in os.listdir(path):
    if f not in excludes:
        dst = os.path.join(home, f)
        src = os.path.abspath(f)
        try:
            print "Symlinking %s to %s" % (src, dst)
            os.symlink(src, dst)
        except Exception, msg:
            print "Failed to symlink %s to %s " % (src, dst)
            print msg
