#!/usr/bin/env python3
"""从实际文件确定性提取raw及来源证明，避免手抄摘录时删注释或改单位。"""
import argparse
import json
from pathlib import Path
from verify_research import digest, extract, ensure_distinct_output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--code-id', required=True)
    parser.add_argument('--selector', type=Path, required=True, help='选择器JSON，字段见references/10')
    parser.add_argument('--encoding', default='utf-8-sig')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        source, root = args.source.resolve(), args.source_root.resolve()
        if not source.is_relative_to(root): raise ValueError('源文件不在source-root内')
        ensure_distinct_output(args.output, [source,args.selector])
        if args.output.exists() and not args.overwrite: raise ValueError('输出已存在；换名或明确--overwrite')
        content = source.read_bytes()
        selector = json.loads(args.selector.read_text('utf-8-sig'))
        result = {'source':{'source_id':args.source_id,'path':source.relative_to(root).as_posix(),
                            'sha256':digest(content),'encoding':args.encoding},
                  'excerpt':{'code_id':args.code_id,'source_id':args.source_id,'selector':selector},
                  'raw':extract(content.decode(args.encoding), selector),
                  'boundary':'只提取文本，不推断游戏机制。教学解释另写，原文原有注释保留。'}
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'已提取：{args.output}')
        return 0
    except (OSError,ValueError,TypeError,KeyError,LookupError) as exc:
        print(f'提取失败：{exc}')
        return 1

if __name__ == '__main__': raise SystemExit(main())
