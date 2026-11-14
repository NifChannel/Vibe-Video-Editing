"""Behavioral checks for fallback activation, overrides and read-only project compatibility."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from delivery_config import defaults
from speech_settings import resolve_speech


class SpeechSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def choices(self, style='default', legacy=False):
        data = defaults(self.project)
        if legacy:
            data.pop('speech')
            data['schema_version'] = 1
        else:
            data['speech']['style'] = style
        path = self.project / 'video-editing.delivery.json'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return path, path.read_bytes()

    def test_no_reference_or_instructions_emits_all_approved_targets(self):
        result = resolve_speech(self.project, 'yes', 'no')
        self.assertTrue(result['default_preset_applied'])
        self.assertEqual(result['rhythm_policy']['pause_targets_seconds'], {
            'clause_or_list': {'target': .25, 'range': [.2, .4]},
            'sentence': {'target': .8, 'range': [.6, 1.1]},
            'concept': {'target': 2.2, 'range': [1.9, 2.6]},
        })
        self.assertFalse((self.project / 'video-editing.delivery.json').exists())

    def test_reference_takes_precedence_over_default_selection(self):
        path, raw = self.choices()
        result = resolve_speech(self.project, 'yes', 'yes')
        self.assertFalse(result['default_preset_applied'])
        self.assertIsNone(result['rhythm_policy'])
        self.assertEqual(result['planning_status'], 'analyze_reference')
        self.assertEqual(path.read_bytes(), raw)

    def test_explicit_brief_takes_precedence_even_with_reference(self):
        for reference in ('yes', 'no', 'unknown'):
            result = resolve_speech(self.project, 'yes', reference, '  保留所有理解停顿  ')
            self.assertEqual(result['speech_brief'], '保留所有理解停顿')
            self.assertEqual(result['planning_status'], 'follow_speech_brief')
            self.assertFalse(result['default_preset_applied'])
            self.assertIsNone(result['rhythm_policy'])

    def test_unknown_reference_does_not_assume_absence(self):
        result = resolve_speech(self.project, 'yes')
        self.assertTrue(result['must_determine_reference_presence'])
        self.assertFalse(result['default_preset_applied'])
        self.assertIsNone(result['rhythm_policy'])

    def test_no_or_unknown_speech_never_emits_default_seconds(self):
        for speech in ('no', 'unknown'):
            result = resolve_speech(self.project, speech, 'no')
            self.assertFalse(result['default_preset_applied'])
            self.assertIsNone(result['rhythm_policy'])
        self.assertTrue(resolve_speech(self.project, 'no', 'no')['skip_speech_editing'])

    def test_existing_nondefault_styles_are_preserved_without_rewriting(self):
        policies = json.loads((Path(__file__).resolve().parents[1] / 'assets/speech-rhythm.json').read_text('utf-8'))
        for style in ('compact', 'relaxed'):
            path, raw = self.choices(style)
            result = resolve_speech(self.project, 'yes', 'yes')
            self.assertFalse(result['default_preset_applied'])
            self.assertEqual(result['rhythm_policy'], policies['styles'][style])
            self.assertEqual(path.read_bytes(), raw)

    def test_auto_choice_resolves_without_disk_changes(self):
        path, raw = self.choices('auto')
        result = resolve_speech(self.project, 'yes', 'no')
        self.assertEqual(result['requested_style'], 'auto')
        self.assertTrue(result['default_preset_applied'])
        self.assertEqual(path.read_bytes(), raw)

    def test_unsupported_legacy_config_is_rejected_without_rewriting(self):
        path, raw = self.choices('auto', legacy=True)
        with self.assertRaises(ValueError):
            resolve_speech(self.project, 'yes', 'no')
        self.assertEqual(path.read_bytes(), raw)

    def test_invalid_context_is_rejected(self):
        for kwargs in ({'speech_present': 'maybe'}, {'reference_present': 'maybe'}, {'speech_brief': None}):
            with self.assertRaises(ValueError):
                resolve_speech(self.project, **kwargs)

    def test_cli_serializes_decision_and_refuses_config_overwrite(self):
        path, raw = self.choices()
        script = Path(__file__).with_name('speech_settings.py')
        output = self.project / 'work/speech-settings.json'
        command = [sys.executable, str(script), '--project', str(self.project), '--speech-present', 'yes', '--reference-present', 'no']
        subprocess.run(command + ['--output', str(output)], capture_output=True, check=True)
        self.assertTrue(json.loads(output.read_text('utf-8'))['default_preset_applied'])
        rejected = subprocess.run(command + ['--output', str(path)], capture_output=True)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
