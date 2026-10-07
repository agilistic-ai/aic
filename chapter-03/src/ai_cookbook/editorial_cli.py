"""Generate, inspect, revise, approve, and export source-grounded editorial drafts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

from pydantic import ValidationError

from .editorial_checks import NAMES, checks
from .editorial_record import load_job
from .editorial_review import approve, export_approved, fingerprint, save
from .editorial_run import run


def emit(value):
    print(json.dumps(value, ensure_ascii=False))


def report(path, job):
    return {"package": str(path), "review_page": str(Path(path).with_suffix('.html')),
            "digest": fingerprint(job), "flags": checks(job), "approval": "required",
            "failure": job['failure'], "failure_stage": job.get('failure_stage')}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest='command', required=True)
    generation = commands.add_parser('run', help='Generate one saved package and review page.')
    generation.add_argument('folder', type=Path)
    generation.add_argument('--method', choices=('single', 'staged'), default='staged')
    generation.add_argument('--project', type=Path, default=Path('.'))
    generation.add_argument('--config', type=Path)
    generation.add_argument('--output', type=Path, help='Parent directory for a new UUID run folder.')
    showing = commands.add_parser('show', help='Show package status and mechanical findings.')
    showing.add_argument('package', type=Path)
    draft = commands.add_parser('draft', help='Copy a draft to a new editable text file.')
    draft.add_argument('--output', type=Path, required=True)
    revision = commands.add_parser('revise', help='Save a correction as a new package requiring fresh review.')
    revision.add_argument('--text-file', type=Path, required=True)
    revision.add_argument('--expected-digest', required=True)
    revision.add_argument('--editor', required=True)
    revision.add_argument('--reason', required=True)
    revision.add_argument('--output', type=Path, help='Parent directory for the new run folder.')
    approval = commands.add_parser('approve', help='Record the review of one exact package version.')
    approval.add_argument('--expected-digest', required=True)
    approval.add_argument('--reviewer', required=True)
    approval.add_argument('--meaning-reviewed', action='store_true')
    approval.add_argument('--language-reviewed', action='store_true')
    export = commands.add_parser('export', help='Export one approved version without publishing it.')
    export.add_argument('--output', type=Path, required=True)
    for sub in (draft, revision, approval, export):
        sub.add_argument('package', type=Path)
        sub.add_argument('name', choices=NAMES)
    compare = commands.add_parser('compare', help='Summarize generation usage; no automatic fidelity judgment.')
    compare.add_argument('packages', nargs='+', type=Path)
    return cli


def operate(args):
    if args.command == 'run':
        path, job = run(args.folder, method=args.method, project=args.project,
                        config=args.config, output=args.output)
        emit(report(path, job))
        return 1 if checks(job) else 0
    if args.command == 'compare':
        for path in args.packages:
            job = load_job(path)
            calls = job['calls']
            record = {'package': str(path), 'digest': fingerprint(job), 'method': job['method'],
                      'generation_calls': len(calls), 'generation_seconds': sum(c['seconds'] for c in calls),
                      'flags': checks(job), 'fidelity': 'human_assessment_required',
                      'revision_of': job.get('revision_of')}
            for name in ('input_tokens', 'output_tokens'):
                record[name + '_known'] = sum(c[name] for c in calls if c[name] is not None)
                record[name + '_unknown_calls'] = sum(c[name] is None for c in calls)
            emit(record)
        return 0
    job = load_job(args.package)
    if args.command == 'show':
        emit(report(args.package, job))
    elif args.command == 'draft':
        if args.name not in job['drafts']:
            raise ValueError('This generation has no such draft.')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as output:
            output.write(job['drafts'][args.name])
        emit({'draft_file': str(args.output), 'digest': fingerprint(job)})
    elif args.command == 'revise':
        if fingerprint(job) != args.expected_digest:
            raise ValueError('Reload the package before correcting it.')
        if job['failure'] or job['questions'] or set(job['drafts']) != set(NAMES):
            raise ValueError('Resolve source/brief questions and regenerate the incomplete package first.')
        if not args.editor.strip() or not args.reason.strip():
            raise ValueError('Identify the editor and explain the correction.')
        with args.text_file.open('rb') as source:
            raw = source.read(65537)
        if len(raw) > 65536 or not raw.decode('utf-8').strip():
            raise ValueError('The corrected draft must be nonblank UTF-8 of at most 65536 bytes.')
        job['revision_of'] = fingerprint(job)
        job['revision'] = {'editor': args.editor, 'reason': args.reason, 'draft': args.name,
                           'created_at': datetime.now(timezone.utc).isoformat()}
        job['drafts'][args.name] = raw.decode('utf-8')
        parent = args.output or args.package.parent.parent
        path = parent / uuid4().hex / 'run.json'
        save(job, path)
        emit(report(path, job))
        return 1 if checks(job) else 0
    elif args.command == 'approve':
        approve(args.package, args.name, expected_digest=args.expected_digest, reviewer=args.reviewer,
                meaning_reviewed=args.meaning_reviewed, language_reviewed=args.language_reviewed)
        emit({'approval_file': str(args.package.with_suffix(f'.{args.name}.approval.json'))})
    elif args.command == 'export':
        export_approved(args.package, args.name, args.output)
        emit({'exported': str(args.output)})
    return 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        return operate(args)
    except ValidationError:
        message = 'JSON fields or types do not match the source, brief, package, or approval schema.'
    except (OSError, ValueError) as error:
        message = str(error)
    except KeyboardInterrupt:
        print('Interrupted. Start a fresh generation; an unfinished run is not approved.', file=sys.stderr)
        return 130
    print(message, file=sys.stderr)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
