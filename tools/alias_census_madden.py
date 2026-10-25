import sys, re, glob, os, collections

gen = sys.argv[1]
out = sys.argv[2]
cre = re.compile(r'^\s*//\s*([a-z][a-z0-9_.]*)\b')
fre = re.compile(r'DEFINE_REX_FUNC\((\w+)\)')
dst_re = re.compile(r'^\s*(?:\w+\.)?v(\d+)\.(?:u8|u16|u32|u64|f32|s32|s16|s8)(?:\[[^\]]*\])?\s*[|]?=')
reg_re = re.compile(r'\bv(\d+)\b')

def classify(name, t):
    if name == 'vpkd3d128':
        if '0x404000FF' in t: return 'pack D3DCOLOR'
        if 'kPack2101010' in t: return 'pack NORMPACKED32'
        if '0xFFFFF' in t: return 'pack NORMPACKED64'
        if '0x7FE000' in t:
            return 'pack FLOAT16_2' if t.count('0x7FE000') == 2 else 'pack FLOAT16_4'
        if '32767' in t:
            return 'pack NORMSHORT2' if '<< 16' in t else 'pack NORMSHORT4'
        return 'pack OTHER'
    return name

stats = collections.defaultdict(lambda: [0, 0])
examples = collections.defaultdict(list)
for f in sorted(glob.glob(os.path.join(gen, 'madden08_recomp.*.cpp'))):
    lines = open(f, encoding='utf-8', errors='replace').read().split('\n')
    n = len(lines)
    func = '?'
    for i in range(n):
        fm = fre.search(lines[i])
        if fm:
            func = fm.group(1)
        m = cre.match(lines[i])
        if not m:
            continue
        name = m.group(1)
        if name not in ('vpkuhus', 'vpkuwus', 'vpkd3d128'):
            continue
        body = []
        j = i + 1
        while j < n and not cre.match(lines[j]) and len(body) < 60:
            body.append(lines[j])
            j += 1
        label = classify(name, '\n'.join(body))
        dest = None
        for b in body:
            dm = dst_re.match(b)
            if dm:
                dest = dm.group(1)
                break
        srcs = set()
        for b in body:
            if '=' in b:
                rhs = b.split('=', 1)[1]
                for rm in reg_re.finditer(rhs):
                    srcs.add(rm.group(1))
        alias = (dest is not None) and (dest in srcs)
        stats[label][0] += 1
        if alias:
            stats[label][1] += 1
            if len(examples[label]) < 6:
                examples[label].append('%s  (%s)  v%s' % (func, os.path.basename(f), dest))

res = ['=== pack instructions where the destination register is also a source ===',
       '  %-22s %6s %8s' % ('instruction', 'sites', 'aliased')]
for k in sorted(stats):
    res.append('  %-22s %6d %8d' % (k, stats[k][0], stats[k][1]))
res.append('')
res.append('=== examples of aliased sites ===')
for k in sorted(examples):
    res.append(k)
    for e in examples[k]:
        res.append('    ' + e)
text = '\n'.join(res)
open(out, 'w', encoding='utf-8').write(text)
print(text)
