"""Read-only exact identifier text search; not an engine interface validator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys


def search_symbol(game_root, symbol, max_matches=20):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', symbol):
        raise ValueError('symbol must be one identifier, without scope prefixes or expressions')
    if not 1 <= max_matches <= 100:
        raise ValueError('max_matches must be between 1 and 100')
    root = Path(game_root).resolve()
    if (root / 'game' / 'common').is_dir():
        root = root / 'game'
    if not all((root / directory).is_dir() for directory in ('common', 'events', 'gui')):
        raise ValueError('game root must contain common, events and gui, directly or under game/')
    rg = shutil.which('rg')
    if not rg:
        raise ValueError('rg is required; locate the existing ripgrep tool rather than installing silently')
    pattern = r'\b' + re.escape(symbol) + r'\b'
    args = [rg, '--json', '--color', 'never', '-g', '*.txt', '-g', '*.gui', '-g', '*.info',
            '--', pattern, str(root)]
    process = subprocess.run(args, capture_output=True, encoding='utf-8', errors='strict')
    if process.returncode not in (0, 1):
        raise ValueError('rg search failed: ' + process.stderr.strip())
    matches = []
    paths = set()
    for line in process.stdout.splitlines():
        item = json.loads(line)
        if item['type'] != 'match':
            continue
        data = item['data']
        if 'text' not in data['path'] or 'text' not in data['lines']:
            raise ValueError('non-UTF-8 source requires separate inspection; no complete result claimed')
        path = Path(data['path']['text'])
        paths.add(path)
        matches.append({'path': str(path.relative_to(root)), 'line': data['line_number'],
                        'text': data['lines']['text'].rstrip('\r\n')})
    matches.sort(key=lambda row: (row['path'], row['line']))
    return {
        'status': 'FOUND' if matches else 'NOT_FOUND', 'symbol': symbol,
        'match_kind': 'EXACT_IDENTIFIER_TEXT_OCCURRENCE',
        'game_root': str(root), 'pattern': pattern, 'rg_exit_code': process.returncode,
        'match_lines': len(matches), 'matched_files': len(paths),
        'matches_truncated': len(matches) > max_matches, 'matches': matches[:max_matches],
        'sources': [{'path': str(p.relative_to(root)),
                     'sha256': hashlib.sha256(p.read_bytes()).hexdigest().upper()}
                    for p in sorted(paths)],
        'engine_support': 'UNVERIFIED', 'interface_kind_and_scope': 'UNVERIFIED',
        'game_version': 'UNVERIFIED',
        'limits': 'Text can occur in comments, localization, declarations or calls; inspect context. '
                  'Zero occurrences do not prove engine removal or lack of support.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-root', required=True)
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--max-matches', type=int, default=20)
    args = parser.parse_args()
    try:
        result = search_symbol(args.game_root, args.symbol, args.max_matches)
    except (ValueError, OSError, UnicodeError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0  # NOT_FOUND is a completed search; rg's 1 is preserved separately.


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
