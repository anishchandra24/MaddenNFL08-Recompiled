import sys, re, glob, os, collections

gen = sys.argv[1]
out = sys.argv[2]
cre = re.compile(r'^\s*//\s*([a-z][a-z0-9_.]*)\b')

def classify(name, t):
    if name == 'vupkd3d128':
        if '0x3F800000' in t and '.u8[' in t: return 'D3DCOLOR'
        if '<< 22) >> 22' in t: return 'NORMPACKED32 (2_10_10_10)'
        if '<< 44) >> 44' in t: return 'NORMPACKED64'
        if '0x1C000' in t:
            return 'FLOAT16_2' if '.f32[0] = 1.0f' in t else 'FLOAT16_4'
        if '3.0f' in t:
            return 'NORMSHORT2' if '.f32[1] = 0.0f' in t else 'NORMSHORT4'
    else:
        if '0x404000FF' in t: return 'D3DCOLOR'
        if 'kPack2101010' in t: return 'NORMPACKED32 (2_10_10_10)'
        if '0xFFFFF' in t: return 'NORMPACKED64'
        if '0x7FE000' in t:
            return 'FLOAT16_2' if t.count('0x7FE000') == 2 else 'FLOAT16_4'
        if '32767' in t:
            return 'NORMSHORT2' if '<< 16' in t else 'NORMSHORT4'
    return 'OTHER'

mn = collections.Counter()
var = collections.Counter()
for f in sorted(glob.glob(os.path.join(gen, 'madden08_recomp.*.cpp'))):
    lines = open(f, encoding='utf-8', errors='replace').read().split('\n')
    n = len(lines)
    for i in range(n):
        m = cre.match(lines[i])
        if not m:
            continue
        name = m.group(1)
        mn[name] += 1
        if name in ('vupkd3d128', 'vpkd3d128'):
            body = []
            j = i + 1
            while j < n and not cre.match(lines[j]) and len(body) < 60:
                body.append(lines[j])
                j += 1
            var[(name, classify(name, '\n'.join(body)))] += 1

res = []
res.append('=== vpkd3d128 / vupkd3d128 variants used by Madden 08 ===')
for k, v in sorted(var.items()):
    res.append('  %-12s %-28s %d' % (k[0], k[1], v))
res.append('')
res.append('=== All vector / vector-memory instructions, most used first ===')
vec = [(k, v) for k, v in mn.items() if k.startswith('v') or k.startswith('lv') or k.startswith('stv')]
for k, v in sorted(vec, key=lambda x: -x[1]):
    res.append('  %-14s %d' % (k, v))
text = '\n'.join(res)
open(out, 'w', encoding='utf-8').write(text)
print(text)
