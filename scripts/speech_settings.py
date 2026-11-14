"""Resolve speech policy with explicit fallback eligibility; never edit project choices."""
import argparse
import json
from pathlib import Path
from delivery_config import resolve


def resolve_speech(project, speech_present='unknown', reference_present='unknown', speech_brief=''):
    for name, value in (('speech_present', speech_present), ('reference_present', reference_present)):
        if value not in ('unknown', 'yes', 'no'):
            raise ValueError(f'{name} must be unknown, yes or no')
    if not isinstance(speech_brief, str):
        raise ValueError('speech_brief must be text')
    brief = speech_brief.strip()
    delivery = resolve(project)
    policies = json.loads((Path(__file__).resolve().parents[1] / 'assets/speech-rhythm.json').read_text('utf-8'))
    requested = delivery['config']['speech']['style']
    effective = 'default' if requested == 'auto' else requested
    policy = None
    applied = False
    if speech_present == 'no':
        status, reason = 'skip', 'no_speech'
    elif speech_present == 'unknown':
        status, reason = 'check_speech_presence', 'speech_presence_unknown'
    elif brief:
        status, reason = 'follow_speech_brief', 'explicit_speech_brief'
    elif effective != 'default':
        status, reason = 'use_selected_style', 'explicit_nondefault_style'
        policy = policies['styles'][effective]
    elif reference_present == 'yes':
        status, reason = 'analyze_reference', 'speech_reference_present'
    elif reference_present == 'unknown':
        status, reason = 'check_reference_presence', 'reference_presence_unknown'
    else:
        status, reason = 'plan_default', 'no_reference_or_speech_instructions'
        policy = policies['styles']['default']
        applied = True
    return {
        'schema_version': 1, 'workflow': 'qwen_f', 'requested_style': requested,
        'effective_style': effective if speech_present != 'no' else None,
        'speech_present': speech_present, 'reference_present': reference_present,
        'speech_brief': brief, 'skip_speech_editing': speech_present == 'no',
        'must_determine_speech_presence': speech_present == 'unknown',
        'must_determine_reference_presence': status == 'check_reference_presence',
        'default_preset_applied': applied, 'planning_status': status, 'selection_reason': reason,
        'choice_does_not_create_or_synthesize_speech': True,
        'base_model': policies['base_model'], 'aligner_model': policies['aligner_model'],
        'universal_quality_reference': policies['universal_quality_reference'],
        'rhythm_policy': policy, 'config_found': delivery['config_found'],
        'config_path': delivery['config_path'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--speech-present', choices=['unknown', 'yes', 'no'], default='unknown')
    parser.add_argument('--reference-present', choices=['unknown', 'yes', 'no'], default='unknown')
    parser.add_argument('--speech-brief', default='', help='Current explicit speech-editing instructions; not saved to project choices')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = resolve_speech(args.project, args.speech_present, args.reference_present, args.speech_brief)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        if args.output.resolve() in [Path(result['config_path']).resolve(), Path(args.project).resolve()]:
            parser.error('--output cannot overwrite the choices or project')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
