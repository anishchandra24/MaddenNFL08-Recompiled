import sys, re, glob, os, collections

pat = re.compile(r'warn|unimpl|unsupported|not supported|not implemented|fail|error|invalid|unexpected|fallback|stub', re.I)
norm = re.compile(r'0x[0-9a-fA-F]+|\d+')

def scan(path, limit=35):
    print("=" * 70)
    print(path)
    if not os.path.exists(path):
        print("  (not found)")
        return
    counts = collections.Counter()
    first = {}
    total = 0
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            total += 1
            if pat.search(line):
                key = norm.sub('#', line.strip())[:180]
                counts[key] += 1
                if key not in first:
                    first[key] = line.strip()[:180]
    print("  total lines: %d, distinct warning-like messages: %d" % (total, len(counts)))
    for key, n in counts.most_common(limit):
        print("  %6dx  %s" % (n, first[key]))

logs = 'C:\\Madden08\\.local\\logs'
scan(os.path.join(logs, 'gpu_E_rov_two_cores.log'))
fc = sorted(glob.glob(os.path.join(logs, 'forced_codegen_*.log')))
if fc:
    scan(fc[-1])
