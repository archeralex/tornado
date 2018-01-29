from __future__ import absolute_import, division, print_function
import os
import subprocess
from subprocess import Popen
import sys
from tempfile import mkdtemp

from tornado.test.util import unittest
import tornado.autoreload


class AutoreloadTest(unittest.TestCase):

    def test_reload_module(self):
        main = """\
import os
import sys

from tornado import autoreload

# This import will fail if path is not set up correctly
import testapp

print('Starting')
if 'TESTAPP_STARTED' not in os.environ:
    os.environ['TESTAPP_STARTED'] = '1'
    sys.stdout.flush()
    autoreload._reload()
"""

        # Create temporary test application
        path = mkdtemp()
        os.mkdir(os.path.join(path, 'testapp'))
        open(os.path.join(path, 'testapp/__init__.py'), 'w').close()
        with open(os.path.join(path, 'testapp/__main__.py'), 'w') as f:
            f.write(main)

        # Make sure the tornado module under test is available to the test
        # application
        pythonpath = os.getcwd()
        if 'PYTHONPATH' in os.environ:
            pythonpath += os.pathsep + os.environ['PYTHONPATH']

        p = Popen(
            [sys.executable, '-m', 'testapp'], stdout=subprocess.PIPE,
            cwd=path, env=dict(os.environ, PYTHONPATH=pythonpath),
            universal_newlines=True)
        out = p.communicate()[0]
        self.assertEqual(out, 'Starting\nStarting\n')

    def test_reload_module_with_argv_preservation(self):
        main = """\
import os
import sys

from tornado import autoreload

# This import will fail if path is not set up correctly
import testapp

print(autoreload._original_argv)
sys.stdout.flush()
if 'TESTAPP_STARTED' not in os.environ:
    os.environ['TESTAPP_STARTED'] = '1'
else:
    os._exit(0)
"""

        touch = """\
import os
import time
import sys
import stat

for i in range(500):
    time.sleep(0.1)
    # Touch the file
    with open(sys.argv[1], 'w') as f:
        f.write('')
        """

        # Create temporary test application
        path = mkdtemp()
        os.mkdir(os.path.join(path, 'testapp'))
        open(os.path.join(path, 'testapp/__init__.py'), 'w').close()
        with open(os.path.join(path, 'testapp/__main__.py'), 'w') as f:
            f.write(main)
        with open(os.path.join(path, 'testapp/touch.py'), 'w') as f:
            f.write(touch)

        # Make sure the tornado module under test is available to the test
        # application
        pythonpath = os.getcwd()
        if 'PYTHONPATH' in os.environ:
            pythonpath += os.pathsep + os.environ['PYTHONPATH']

        autoreload_proc = Popen(
            [sys.executable, '-m', 'tornado.autoreload', '-m', 'testapp'],
            stdout=subprocess.PIPE, cwd=path, env=dict(os.environ, PYTHONPATH=pythonpath),
            universal_newlines=True)
        touch_proc = Popen(
            [sys.executable, os.path.join(path, 'testapp/touch.py'),
             os.path.join(path, 'testapp/__init__.py')],
            cwd=path, env=dict(os.environ, PYTHONPATH=pythonpath),
            universal_newlines=True)

        # Once the autoreload process is done, we kill the touch process
        autoreload_proc.wait()
        touch_proc.terminate()
        touch_proc.wait()
        import time
        time.sleep(300)

        out = autoreload_proc.communicate()[0]
        self.assertEqual((str([os.path.join(os.path.dirname(os.path.abspath(tornado.autoreload.__file__)),
                                            'autoreload.py'), '-m', 'testapp']) + '\n') * 2, out)
