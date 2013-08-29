from __future__ import absolute_import, unicode_literals

import errno
import os
import shutil
import tempfile

from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.conf import settings
from django.contrib.staticfiles import storage
from django.core.wsgi import get_wsgi_application

from .utils import TestServer

from whitenoise.django import DjangoWhiteNoise


ROOT_FILE = '/robots.txt'
ASSET_FILE = '/some/test.js'
TEST_FILES = {
    'root' + ROOT_FILE: b'some text',
    'static' + ASSET_FILE: b'this is some javascript'
}


@override_settings()
class DjangoWhiteNoiseTest(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        # Keep a record of the original lazy storage instance so we can
        # restore it afterwards. We overwrite this in the setUp method so
        # that any new settings get picked up.
        if not hasattr(cls, '_original_staticfiles_storage'):
            cls._original_staticfiles_storage = storage.staticfiles_storage
        # Make a temporary directory and copy in test files
        cls.tmp = tempfile.mkdtemp()
        settings.STATIC_ROOT = os.path.join(cls.tmp, 'static')
        settings.WHITENOISE_ROOT = os.path.join(cls.tmp, 'root')
        for path, contents in TEST_FILES.items():
            path = os.path.join(cls.tmp, path.lstrip('/'))
            try:
                os.makedirs(os.path.dirname(path))
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            with open(path, 'wb') as f:
                f.write(contents)
        # Initialize test application
        django_app = get_wsgi_application()
        cls.application = DjangoWhiteNoise(django_app)
        cls.server = TestServer(cls.application)
        super(DjangoWhiteNoiseTest, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(DjangoWhiteNoiseTest, cls).tearDownClass()
        # Restore monkey-patched values
        if hasattr(cls, '_original_staticfiles_storage'):
            storage.staticfiles_storage = cls._original_staticfiles_storage
            del cls._original_staticfiles_storage
        # Remove temporary directory
        shutil.rmtree(cls.tmp)

    def setUp(self):
        # Configure a new lazy storage instance so it will pick up
        # any new settings
        storage.staticfiles_storage = storage.ConfiguredStorage()

    def test_get_static_file(self):
        url = storage.staticfiles_storage.url(ASSET_FILE.lstrip('/'))
        response = self.server.get(url)
        self.assertEqual(response.content, TEST_FILES['static' + ASSET_FILE])

    def test_get_root_file(self):
        url = storage.staticfiles_storage.url(ROOT_FILE)
        response = self.server.get(url)
        self.assertEqual(response.content, TEST_FILES['root' + ROOT_FILE])
