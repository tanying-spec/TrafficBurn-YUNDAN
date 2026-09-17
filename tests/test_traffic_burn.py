import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location('traffic_burn', ROOT / 'traffic_burn.py')
t = importlib.util.module_from_spec(spec); spec.loader.exec_module(t)

class Tests(unittest.TestCase):
    def test_cloudflare_url_exact_bytes(self):
        self.assertEqual(t.cloudflare_url(123), 'https://speed.cloudflare.com/__down?bytes=123')

    def test_windows_failure_falls_back(self):
        calls = []
        with patch.object(t, 'microsoft_iso_url', side_effect=RuntimeError('no link')), \
             patch.object(t, 'download', side_effect=lambda url, amount, limit: (calls.append(url) or amount, 1)):
            t.run(1024, 'windows', 1)
        self.assertIn('proof.ovh.net', calls[0])

    def test_auto_pool_has_multiple_providers_and_ovh_first(self):
        pool = t.source_pool('auto', 123)
        self.assertEqual(pool[0][0], 'OVH 欧洲')
        self.assertGreaterEqual(len(pool), 10)
        names = ' '.join(name for name, _ in pool)
        for provider in ('OVH', 'Vultr', 'Hetzner', 'Linode', 'Cloudflare'):
            self.assertIn(provider, names)

    def test_cloudflare_mode_is_cloudflare_only(self):
        self.assertEqual(t.source_pool('cloudflare', 123), [
            ('Cloudflare', 'https://speed.cloudflare.com/__down?bytes=123')
        ])

    def test_installer_hash_matches(self):
        import hashlib
        digest = hashlib.sha256((ROOT / 'traffic_burn.py').read_bytes()).hexdigest()
        installer = (ROOT / 'install.sh').read_text(encoding='utf-8')
        self.assertIn('PROGRAM_SHA256=' + digest, installer)
        openwrt = hashlib.sha256((ROOT / 'traffic_burn_openwrt.sh').read_bytes()).hexdigest()
        self.assertIn('OPENWRT_SHA256=' + openwrt, installer)

if __name__ == '__main__': unittest.main()
