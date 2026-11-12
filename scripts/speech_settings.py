"""Resolve the per-project speech choice without changing the user's config."""
import argparse,json
from pathlib import Path
from delivery_config import resolve


def resolve_speech(project, speech_present='unknown'):
    if speech_present not in ('unknown','yes','no'):
        raise ValueError('speech_present must be unknown, yes or no')
    settings=resolve(project)
    policies=json.loads((Path(__file__).resolve().parents[1]/'assets/speech-rhythm.json').read_text('utf-8'))
    requested=settings['config']['speech']['style']
    effective='default' if requested=='auto' else requested
    return {'schema_version':1,'workflow':'qwen_f','requested_style':requested,
        'effective_style':effective if speech_present!='no' else None,
        'speech_present':speech_present,'skip_speech_editing':speech_present=='no',
        'must_determine_speech_presence':speech_present=='unknown',
        'choice_does_not_create_or_synthesize_speech':True,
        'base_model':policies['base_model'],'aligner_model':policies['aligner_model'],
        'universal_quality_reference':policies['universal_quality_reference'],
        'rhythm_policy':policies['styles'][effective],
        'config_found':settings['config_found'],'config_path':settings['config_path']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True)
    p.add_argument('--speech-present',choices=['unknown','yes','no'],default='unknown')
    p.add_argument('--output',type=Path)
    args=p.parse_args();result=resolve_speech(args.project,args.speech_present)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        if args.output.resolve() in [Path(result['config_path']).resolve(),Path(args.project).resolve()]:
            p.error('--output cannot overwrite the choices or project')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text,encoding='utf-8')
    print(text)


if __name__=='__main__':main()
