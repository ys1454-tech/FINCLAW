from __future__ import annotations

import argparse
import json

from .runner import AgentRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='FINCLAW internal automation agent controller')
    parser.add_argument('command', choices=['bootstrap', 'start', 'stop', 'run-once', 'status', 'describe'])
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    runner = AgentRunner()

    match args.command:
        case 'bootstrap':
            result = runner.bootstrap()
        case 'start':
            result = runner.start()
        case 'stop':
            result = runner.stop()
        case 'run-once':
            result = runner.run_once()
        case 'status':
            result = runner.status()
        case 'describe':
            result = runner.describe()
        case _:
            parser.error('Unsupported command')
            return

    print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
    main()
