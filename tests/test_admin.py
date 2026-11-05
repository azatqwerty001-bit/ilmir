"""Run: python3 -m unittest discover -s tests -v"""
import http.cookiejar
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

class AdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.password = secrets.token_urlsafe(24)
        cls.env = dict(os.environ, CAFE_ADMIN_STATE=cls.temp.name, CAFE_ADMIN_PASSWORD=cls.password)
        subprocess.run(['python3', 'admin_server.py', '--init'], cwd=ROOT, env=cls.env, check=True, stdout=subprocess.DEVNULL)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.base = f'http://127.0.0.1:{cls.port}'
        cls.server = subprocess.Popen(['python3', 'admin_server.py', '--port', str(cls.port)], cwd=ROOT, env=cls.env, stdout=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + '/api/session', timeout=1).close()
                break
            except OSError:
                time.sleep(.05)
        else:
            cls.server.terminate()
            raise RuntimeError('Server did not start')

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=5)
        cls.temp.cleanup()

    def request(self, path, body=None, cookie=None, origin=None):
        headers = {'Origin': origin or self.base}
        if body is not None:
            headers['Content-Type'] = 'application/json'
        if cookie:
            headers['Cookie'] = cookie
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as response_error:
            response = response_error
        with response:
            return response.status, response.read(), response.headers

    def login(self):
        status, _, headers = self.request('/api/login', {'password': self.password})
        self.assertEqual(status, 200)
        return headers['Set-Cookie'].split(';')[0]

    def test_authentication_and_origin(self):
        self.assertEqual(self.request('/api/menu')[0], 401)
        self.assertEqual(self.request('/api/menu', {})[0], 401)
        self.assertEqual(self.request('/api/login', {'password': 'wrong'})[0], 401)
        self.assertEqual(self.request('/api/login', {'password': self.password}, origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/api/logout', {}, self.login())[0], 200)

    def test_save_validation_export_and_private_files(self):
        cookie = self.login()
        data = json.loads(self.request('/api/menu', cookie=cookie)[1])
        data['items'][0]['price'] = 287
        self.assertEqual(self.request('/api/menu', data, cookie)[0], 200)
        self.assertEqual(json.loads(self.request('/menu-data.json')[1])['items'][0]['price'], 287)
        invalid = json.loads(json.dumps(data))
        invalid['items'][0]['price'] = -1
        self.assertEqual(self.request('/api/menu', invalid, cookie)[0], 400)
        invalid['items'][0]['price'] = 287
        invalid['items'][0]['image'] = 'https://evil.example/x.webp'
        self.assertEqual(self.request('/api/menu', invalid, cookie)[0], 400)
        self.assertEqual(self.request('/.git/config')[0], 404)
        self.assertEqual(self.request('/admin_server.py')[0], 404)
        with zipfile.ZipFile(io.BytesIO(self.request('/api/export', cookie=cookie)[1])) as archive:
            self.assertNotIn('admin_server.py', archive.namelist())
            self.assertFalse(any('auth' in name for name in archive.namelist()))
            self.assertIn('287 ₽', archive.read('menu.html').decode())
            self.assertEqual(json.loads(archive.read('menu-data.json'))['items'][0]['price'], 287)

if __name__ == '__main__':
    unittest.main()
