# Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved
# SPDX-License-Identifier: MIT
#
# Provided without warranty. Use at your own risk.
# See LICENSE.txt and DISCLAIMER.md in this project for terms.

import argparse,json,sqlite3,sys
from pathlib import Path
from pydantic import ValidationError
from .reporting_data import initialize
from .reporting_report import report


def main(argv=None):
    parser=argparse.ArgumentParser(description="Inspect model-proposed SQL over a scoped read-only reporting snapshot.")
    subs=parser.add_subparsers(dest='action',required=True)
    init=subs.add_parser('init');init.add_argument('--database',type=Path,required=True)
    init.add_argument('--schema',type=Path,default=Path('examples/reporting/schema.sql'))
    ask=subs.add_parser('ask');ask.add_argument('question');ask.add_argument('--database',type=Path,required=True)
    ask.add_argument('--as-of',required=True);ask.add_argument('--output',type=Path,default=Path('runs/reporting'))
    ask.add_argument('--project',type=Path,default=Path('.'));ask.add_argument('--config',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=='init':
            initialize(args.database,args.schema);print(json.dumps({'database':str(args.database)}));return 0
        job=report(args.database,args.question,args.as_of,args.output,project=args.project,config=args.config)
        print(json.dumps(job,ensure_ascii=False,allow_nan=False));return 0
    except ValidationError: message='The model proposal failed schema validation.'
    except sqlite3.Error: message='The proposed query was denied or could not execute; no result was obtained.'
    except (OSError,ValueError) as error: message=str(error)
    except Exception: message='Report generation failed; check the configured model service.'
    print(message,file=sys.stderr);return 2

if __name__=='__main__': raise SystemExit(main())
