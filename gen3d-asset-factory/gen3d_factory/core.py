# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender-independent report and limited Gaussian PLY inspection primitives."""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import math
from pathlib import Path
import struct
import uuid

VERSION = '0.2.0'

RULE_HELP = {
    'UV_MISSING': '贴图需要 UV：UV 告诉每个面应该读取图片的哪个位置。',
    'TEXTURE_MISSING': '材质使用了图片，但图片未指定或原文件找不到。',
    'TOPOLOGY_DEGENERATE': '检测到接近零面积的面，例如三个顶点落在一条直线上。',
    'NAMING': '对象名称不符合 SM_ 命名约定；不代表几何或渲染损坏。',
    'TOPOLOGY_BOUNDARY': '检测到开放边界；薄片可能合法，按交付用途决定。',
    'UV_RANGE': 'UV 超出 0–1；平铺贴图可能合法，需要结合采样方式。',
    'GS_POINT_COUNT': '高斯点数低于复核阈值；请检查是否符合实验预期。',
    'TRANSFORM_SCALE': '对象带有未应用缩放；不能不顾父子关系直接应用。',
    'MODIFIERS': '当前只检查基础网格，修改器的最终形状尚未检查。',
}


@dataclass
class Policy:
    max_triangles: int = 100000
    max_texture_size: int = 4096
    allow_boundaries: bool = True
    allow_tiled_uv: bool = True
    min_gaussians: int = 100


def issue(rule, severity, message, target='', count=None, hint=''):
    return dict(rule=rule, severity=severity, message=message, target=target,
                count=count, hint=hint)


def asset_result(name, kind, metrics, issues, not_checked=()):
    severity = {i['severity'] for i in issues}
    status = ('ERROR' if 'ERROR' in severity else 'UNSUPPORTED' if 'UNSUPPORTED' in severity
              else 'WARNING' if 'WARNING' in severity else 'PASS')
    return dict(name=name, kind=kind, status=status, metrics=metrics, issues=issues,
                not_checked=list(not_checked))


def inspect_ply(path, policy):
    """Stream Graphdeco-like vertex-only binary float32 records without changing input.

    Different PLY schemas are explicitly unsupported, never silently converted.
    Activation ranges are intentionally not validated without exporter provenance.
    """
    path = Path(path)
    metrics = {}
    issues = []
    untested = ['Mesh / UV / PBR: not applicable to Gaussian parameters',
                'Rendering, segmentation completeness, activation convention: not checked']
    try:
        with path.open('rb') as stream:
            digest = hashlib.sha256()
            header = []
            header_size = 0
            while True:
                line = stream.readline(4097)
                header_size += len(line)
                digest.update(line)
                if not line or len(line) > 4096 or header_size > 65536:
                    raise ValueError('Missing or oversized PLY header')
                header.append(line.decode('ascii').strip())
                if header[-1] == 'end_header':
                    break
            if header[0] != 'ply':
                raise ValueError('Missing PLY magic')
            elements = [s.split() for s in header if s.startswith('element ')]
            props = [s.split() for s in header if s.startswith('property ')]
            supported = ('format binary_little_endian 1.0' in header and len(elements) == 1
                         and len(elements[0]) == 3 and elements[0][1] == 'vertex'
                         and bool(props) and all(len(p) == 3 and p[1] == 'float' for p in props))
            if not supported:
                return asset_result(path.name, 'PLY', metrics,
                    [issue('GS_SCHEMA', 'UNSUPPORTED', 'Requires vertex-only little-endian float32 GS PLY')], untested)
            names = [p[2] for p in props]
            required = ['x', 'y', 'z', 'opacity'] + [f'f_dc_{i}' for i in range(3)] + [f'scale_{i}' for i in range(3)] + [f'rot_{i}' for i in range(4)]
            if len(set(names)) != len(names):
                raise ValueError('Duplicate property names')
            if any(name not in names for name in required):
                return asset_result(path.name, 'PLY', metrics,
                    [issue('GS_SCHEMA', 'UNSUPPORTED', 'Required Gaussian fields are missing')], untested)
            count = int(elements[0][2])
            if count < 0:
                raise ValueError('Negative vertex count')
            stride = len(names) * 4
            size = path.stat().st_size
            metrics.update(point_count=count, bytes=size, property_count=len(names), schema='GS float32')
            if size != header_size + count * stride:
                raise ValueError('Payload length disagrees with header')
            xyz_indices = [names.index(n) for n in ('x', 'y', 'z')]
            q_indices = [names.index(f'rot_{i}') for i in range(4)]
            low = [math.inf] * 3
            high = [-math.inf] * 3
            bad_values = zero_q = 0
            remaining = count
            while remaining:
                take = min(8192, remaining)
                block = stream.read(take * stride)
                if len(block) != take * stride:
                    raise ValueError('Truncated payload during read')
                digest.update(block)
                for row in struct.iter_unpack('<' + 'f'*len(names), block):
                    bad_values += sum(not math.isfinite(v) for v in row)
                    q = [row[i] for i in q_indices]
                    if all(math.isfinite(v) for v in q) and sum(v*v for v in q) < 1e-20:
                        zero_q += 1
                    for axis, idx in enumerate(xyz_indices):
                        if math.isfinite(row[idx]):
                            low[axis] = min(low[axis], row[idx])
                            high[axis] = max(high[axis], row[idx])
                remaining -= take
            metrics.update(sha256=digest.hexdigest(), nonfinite_values=bad_values,
                           zero_quaternions=zero_q,
                           bounds_min=[v if math.isfinite(v) else None for v in low],
                           bounds_max=[v if math.isfinite(v) else None for v in high])
            if bad_values:
                issues.append(issue('GS_FINITE', 'ERROR', 'Non-finite Gaussian parameters', count=bad_values))
            if zero_q:
                issues.append(issue('GS_ROTATION', 'ERROR', 'Zero-length rotation quaternions', count=zero_q))
            if count == 0:
                issues.append(issue('GS_EMPTY', 'ERROR', 'No Gaussian records'))
            elif count < policy.min_gaussians:
                issues.append(issue('GS_POINT_COUNT', 'WARNING', f'{count} points < configured review threshold {policy.min_gaussians}',
                                    count=count, hint='Check intended content and extraction history; small does not mean corrupt.'))
        return asset_result(path.name, 'GAUSSIAN', metrics, issues, untested)
    except (OSError, ValueError, UnicodeError, struct.error) as error:
        return asset_result(path.name, 'PLY', metrics,
                            [issue('INPUT_READ', 'ERROR', str(error))], untested)


def report_document(assets, policy, environment, source):
    return dict(tool='Gen3D Asset Factory', version=VERSION,
                created_utc=datetime.now(timezone.utc).isoformat(), source=source,
                environment=environment, policy=asdict(policy), assets=assets,
                scope='PASS means only implemented checks passed; visual acceptance is separate.')


def write_report(document, directory):
    """New report subdirectory on each run; all HTML values are escaped."""
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    run = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8])
    run.mkdir()
    json_path = run / 'report.json'
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    cards = []
    delivery = document.get('delivery')
    groups = [('Source / 原始输入',document['assets'])]
    if delivery:
        groups.append(('Copy / 命名修正后的副本',delivery.get('copy_assets',[])))
    for group_name,asset in [(name,a) for name,assets in groups for a in assets]:
        rows = ''.join('<tr>' + ''.join(f'<td>{escape(str(i[k]))}</td>' for k in ('severity', 'rule', 'target', 'message', 'hint'))
                       + '<td>'+escape(RULE_HELP.get(i['rule'],''))+'</td></tr>' for i in asset['issues'])
        cards.append(f"<section><h2>{escape(asset['name'])} <span>{escape(asset['status'])}</span></h2>"
                     f"<p>{escape(group_name)} · {escape(asset['kind'])}</p><pre>{escape(json.dumps(asset['metrics'],ensure_ascii=False,indent=2))}</pre>"
                     '<table><thead><tr><th>Status</th><th>Rule</th><th>Object</th><th>Finding</th><th>Action</th><th>中文解释</th></tr></thead>'
                     f'<tbody>{rows}</tbody></table><h3>Coverage limits</h3><ul>'
                     + ''.join(f'<li>{escape(v)}</li>' for v in asset['not_checked']) + '</ul></section>')
    page = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Gen3D Quality Report</title><style>
body{background:#101820;color:#dde5eb;font:15px/1.55 system-ui;margin:0 auto;padding:32px;max-width:1180px}
h1{color:#6ee7cb}section{background:#192630;padding:24px;margin:22px 0;border-radius:12px}
span{font-size:14px;color:#f5c878}table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #3b4b58;padding:10px;overflow-wrap:anywhere}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#101820;padding:16px}h3{font-size:15px;color:#a7b8c6}
</style><h1>Gen3D Asset Factory</h1>'''
    page += '<p>' + escape(document['scope']) + '</p><pre>' + escape(json.dumps(
        {k: document[k] for k in ('version', 'created_utc', 'source', 'environment', 'policy')}, ensure_ascii=False, indent=2)) + '</pre>'
    if delivery:
        page += '<section><h2>交付结果 / '+escape(delivery['status'])+'</h2>'
        page += '<p>原始对象保持不变。VERIFIED 仅代表本报告列出的机器检查通过，仍需要视觉验收。</p>'
        page += '<pre>'+escape(json.dumps({k:delivery.get(k) for k in ('glb','problems','limits')},ensure_ascii=False,indent=2))+'</pre>'
        page += '<h3>副本命名映射</h3><table><tr><th>原名称</th><th>导出名称</th></tr>'
        page += ''.join('<tr><td>'+escape(p['source'])+'</td><td>'+escape(p['export_name'])+'</td></tr>' for p in delivery['plan'])+'</table>'
        page += '<h3>重新导入后的对照检查</h3><pre>'+escape(json.dumps(delivery['checks'],ensure_ascii=False,indent=2))+'</pre></section>'
    page += ''.join(cards) + '</html>'
    html_path = run / 'report.html'
    html_path.write_text(page, encoding='utf-8')
    return str(json_path), str(html_path)
