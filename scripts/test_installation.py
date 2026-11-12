"""Offline checks for relocation, install failure recovery and launch safety."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import bootstrap
import runtime_config as runtime


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        bootstrap.system_tag()  # Resolve Windows platform before subprocess mocks.
        clean = {key: value for key, value in os.environ.items()
                 if key not in ('VIBE_VIDEO_CONFIG', 'FFMPEG_BIN', 'FFPROBE_BIN', 'BLENDER_BIN')}
        self.environment = patch.dict(os.environ, clean, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def config(self, folder, **values):
        folder.mkdir(exist_ok=True)
        path = folder / 'runtime.json'
        path.write_text(json.dumps({'schema_version': 1, **values}), encoding='utf-8')
        return path

    def test_relative_paths_follow_relocated_config(self):
        first = self.config(self.root / 'first', asr_model='models/asr')
        second = self.config(self.root / 'second', asr_model='models/asr')
        self.assertEqual(runtime.load(first)['asr_model'], str(first.parent / 'models/asr'))
        self.assertEqual(runtime.load(second)['asr_model'], str(second.parent / 'models/asr'))

    def test_explicit_missing_or_invalid_config_fails(self):
        with self.assertRaises(FileNotFoundError):
            runtime.load(self.root / 'missing.json')
        invalid = self.config(self.root, unknown_field='mistyped dependency')
        with self.assertRaises(ValueError):
            runtime.load(invalid)
        invalid.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            runtime.load(invalid)

    def test_environment_override_and_no_remote_voice_endpoint(self):
        config = self.config(self.root, ffmpeg='local-tool', vision_url='http://127.0.0.1:1234/v1')
        with patch.dict(os.environ, {'FFMPEG_BIN': str(self.root / 'override.exe')}):
            self.assertEqual(runtime.load(config)['ffmpeg'], str(self.root / 'override.exe'))
        for endpoint in ('https://remote.example/v1', 'http://user:secret@127.0.0.1:12',
                         'http://127.0.0.1:99999', 'http://127.0.0.1/?token=private'):
            config = self.config(self.root, vision_url=endpoint)
            with self.assertRaises(ValueError):
                runtime.load(config)

    def test_qwen_launch_uses_paths_as_arguments_and_protects_outputs(self):
        data = runtime.load()
        for key in ('ffmpeg', 'ffprobe', 'speech_python'):
            path = self.root / (key + " space O'Brien.exe")
            path.touch()
            data[key] = str(path)
        for key in ('asr_model', 'aligner_model'):
            path = self.root / key
            path.mkdir()
            (path / 'config.json').write_text('{}')
            data[key] = str(path)
        media = self.root / "source space O'Brien.wav"
        media.touch()
        output = self.root / 'fresh-output'
        command = runtime.qwen_command(data, media, output, 'Chinese')
        self.assertIn(str(media), command)
        self.assertEqual(command[0], data['speech_python'])
        self.assertFalse(output.exists())
        output.mkdir()
        with self.assertRaises(ValueError):
            runtime.qwen_command(data, media, output, 'Chinese')

    def test_plan_does_not_download_or_create_environment(self):
        target = self.root / 'not-created'
        args = ['bootstrap.py', '--root', str(target)]
        with (patch('sys.argv', args), patch('windows_portable.provision', side_effect=AssertionError('network')),
              patch.object(bootstrap.subprocess, 'run', side_effect=AssertionError('process')),
              contextlib.redirect_stdout(io.StringIO()) as output):
            bootstrap.main()
        self.assertFalse(target.exists())
        self.assertFalse(json.loads(output.getvalue())['executed'])

    def test_failed_install_preserves_existing_config_and_unlocks(self):
        config = self.config(self.root, ffmpeg='previous-valid-location')
        original = config.read_bytes()
        target = self.root / 'environment'
        failed = subprocess.CompletedProcess(['fake'], 5)
        with patch('windows_portable.provision', return_value={'python': target / 'python.exe',
                   'ffmpeg': target / 'ffmpeg.exe', 'ffprobe': target / 'ffprobe.exe'}), \
             patch.object(bootstrap.subprocess, 'run', return_value=failed):
            with self.assertRaises(RuntimeError):
                bootstrap.install(target, config, ['base'])
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse((target / 'install.lock').exists())
        self.assertEqual(json.loads((target / 'install-receipt.json').read_text())['status'], 'failed')

    def test_gpu_backend_requires_supported_official_source(self):
        for source in (None, 'https://untrusted.example/whl/cu128', 'https://download.pytorch.org/whl/cpu'):
            with self.assertRaises(ValueError):
                bootstrap.install(self.root / 'gpu', self.root / 'config.json', ['speech'], source)
        self.assertFalse((self.root / 'gpu').exists())

    def test_platform_matrix_is_explicit(self):
        self.assertEqual(bootstrap.system_tag('Windows', 'AMD64'), 'win-64')
        for system, machine in [('Darwin', 'arm64'), ('Linux', 'x86_64'),
                                ('Windows', 'arm64'), ('Windows', 'x86')]:
            with self.assertRaises(ValueError):
                bootstrap.system_tag(system, machine)
        target = self.root / 'unsupported-environment'
        with patch.object(bootstrap.platform, 'system', return_value='Linux'), \
             patch('windows_portable.provision', side_effect=AssertionError('network')):
            with self.assertRaises(ValueError):
                bootstrap.install(target, self.root / 'unused.json', ['base'])
        self.assertFalse(target.exists())

    def test_project_speech_preferences_and_output_protection(self):
        import delivery_config
        import speech_settings
        initial = delivery_config.read(self.root)
        self.assertFalse(initial['exists'])
        self.assertEqual(initial['config']['schema_version'], 2)
        self.assertEqual(initial['config']['speech']['style'], 'default')
        self.assertFalse((self.root / delivery_config.FILENAME).exists())
        config = initial['config']
        config['speech']['style'] = 'compact'
        saved = delivery_config.write(self.root, config, initial['revision'])
        self.assertTrue(saved['exists'])
        self.assertEqual(delivery_config.resolve(self.root)['speech_style'], 'compact')
        policy = speech_settings.resolve_speech(self.root, 'yes')
        self.assertEqual(policy['effective_style'], 'compact')
        self.assertTrue((runtime.ROOT / policy['rhythm_policy']['basis_reference']).is_file())
        self.assertTrue(speech_settings.resolve_speech(self.root, 'no')['skip_speech_editing'])
        with self.assertRaises(ValueError):
            delivery_config.write(self.root, config, None)

    def test_old_project_format_is_rejected_without_rewriting(self):
        import delivery_config
        path = self.root / delivery_config.FILENAME
        raw = b'{"schema_version":1,"speech":{"style":"relaxed"}}'
        path.write_bytes(raw)
        with self.assertRaises(ValueError):
            delivery_config.read(self.root)
        self.assertEqual(path.read_bytes(), raw)

    def test_github_checkout_without_empty_styles_directory(self):
        import library
        (self.root / 'Functional Skills').mkdir()
        with patch.object(library, 'ROOT', self.root):
            catalog = library.sync()
        self.assertEqual(catalog['styles'], [])
        self.assertTrue((self.root / 'Styles').is_dir())
        self.assertEqual(list((self.root / 'Styles').iterdir()), [])

    def test_portable_archive_rejects_path_traversal_before_extracting(self):
        import windows_portable
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('safe/file.txt', 'allowed')
            output.writestr('../escaped.txt', 'forbidden')
        with self.assertRaises(ValueError):
            windows_portable.unpack(archive, self.root / 'extracted')
        self.assertFalse((self.root / 'escaped.txt').exists())
        self.assertFalse((self.root / 'extracted/safe/file.txt').exists())

    def test_checksum_failure_keeps_unverified_archive_uninstalled(self):
        import windows_portable
        archive = self.root / 'unverified.zip'
        with patch.object(windows_portable, 'urlopen', return_value=io.BytesIO(b'not the expected archive')):
            with self.assertRaises(ValueError):
                windows_portable.download('https://example.invalid/test.zip', archive, '0' * 64)
        self.assertFalse(archive.exists())


if __name__ == '__main__':
    unittest.main()
