# Read-only. Finds function addresses that the game's CODE builds with
# "lis rX,hi" + "addi rY,rX,lo" (or "ori") pairs, that point at code the
# recompiler did not generate. Safe candidates (in a gap, not inside any
# function, not a block label) are written as manifest lines.
# usage: python -I scan_code_pointers_madden.py <project> <image_dump.bin>
import bisect, glob, os, re, struct, sys

proj, dump = sys.argv[1], sys.argv[2]
IBASE = 0x82000000
CBASE, CEND = 0x82370000, 0x82370000 + 0x00F5CA1C
gen = os.path.join(proj, "generated", "default")
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
ins_re = re.compile(r'^\s+// ([a-z][a-z0-9_.+-]*)( |$)')
lab_re = re.compile(r'^loc_([0-9A-F]{8}):')
map_re = re.compile(r'\{\s*0x([0-9A-Fa-f]{8}),\s*(\w+)\s*\}')

# --- generated functions (named ones too), labels
mp = {}
for p in glob.glob(os.path.join(gen, "madden08_init*.cpp")):
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = map_re.search(line)
            if m:
                mp[m.group(2)] = int(m.group(1), 16)
funcs = []
labels = set()
for path in sorted(glob.glob(os.path.join(gen, "madden08_recomp.*.cpp"))):
    name, n = None, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = fn_re.match(line)
            if m:
                if name is not None:
                    a = int(name[4:], 16) if re.match(r'^sub_[0-9A-F]{8}$', name) else mp.get(name)
                    if a is not None:
                        funcs.append((a, n))
                name, n = m.group(1), 0
                continue
            if name is not None:
                if ins_re.match(line):
                    n += 1
                else:
                    l = lab_re.match(line)
                    if l:
                        labels.add(int(l.group(1), 16))
    if name is not None:
        a = int(name[4:], 16) if re.match(r'^sub_[0-9A-F]{8}$', name) else mp.get(name)
        if a is not None:
            funcs.append((a, n))
funcs.sort()
starts = [f[0] for f in funcs]
ends = [f[0] + 4 * f[1] for f in funcs]
startset = set(starts)
print("generated functions: %d, labels: %d" % (len(funcs), len(labels)))

data = open(dump, "rb").read()
def word(a):
    o = a - IBASE
    return struct.unpack(">I", data[o:o + 4])[0] if 0 <= o <= len(data) - 4 else 0

# --- lis + addi/ori pairs in the code area
hits = {}
a = CBASE
while a < CEND:
    w = word(a)
    if (w >> 26) == 15 and ((w >> 16) & 31) == 0:           # lis rD, imm
        rd = (w >> 21) & 31
        hi = w & 0xFFFF
        if 0x8237 <= hi <= 0x832C:
            for k in range(1, 7):
                w2 = word(a + 4 * k)
                op = w2 >> 26
                if op == 14 and ((w2 >> 16) & 31) == rd:      # addi rY, rD, lo
                    lo = w2 & 0xFFFF
                    if lo & 0x8000:
                        lo -= 0x10000
                    t = ((hi << 16) + lo) & 0xFFFFFFFF
                    hits.setdefault(t, []).append(a)
                    break
                if op == 24 and ((w2 >> 21) & 31) == rd:      # ori rY, rD, lo
                    t = (hi << 16) | (w2 & 0xFFFF)
                    hits.setdefault(t, []).append(a)
                    break
    a += 4
print("distinct addresses built from lis+addi/ori inside the code range: %d" %
      sum(1 for t in hits if CBASE <= t < CEND))

def in_func(t):
    i = bisect.bisect_right(starts, t) - 1
    return i >= 0 and t < ends[i]

BAD = {0, 1, 9, 22}
cats = {"already a function": 0, "unaligned": 0, "inside a function": 0, "block label": 0, "looks like data": 0, "GAP": 0}
gap, labs = [], []
for t in sorted(hits):
    if not (CBASE <= t < CEND):
        continue
    if t & 3:
        cats["unaligned"] += 1; continue
    if t in startset:
        cats["already a function"] += 1; continue
    if t in labels:
        cats["block label"] += 1; labs.append(t); continue
    if in_func(t):
        cats["inside a function"] += 1; continue
    w = word(t)
    if w == 0 or (w >> 26) in BAD:
        cats["looks like data"] += 1; continue
    cats["GAP"] += 1
    gap.append(t)
for k, v in cats.items():
    print("  %-22s %d" % (k, v))

def next_start(t):
    i = bisect.bisect_right(starts, t)
    return starts[i] if i < len(starts) else CEND

out = []
for k, t in enumerate(gap):
    nxt = next_start(t)
    if k + 1 < len(gap) and gap[k + 1] < nxt:
        nxt = gap[k + 1]
    size = nxt - t
    out.append((t, size, len(hits[t])))
outp = os.path.join(proj, ".local", "code_pointer_entries.txt")
with open(outp, "w") as o:
    for t, size, n in out:
        if size > 0x2000:
            o.write("0x%08X = {}   # %d ref(s)\n" % (t, n))
        else:
            o.write("0x%08X = { size = 0x%X }   # %d ref(s)\n" % (t, size, n))
print()
print("wrote %d gap entries to %s" % (len(out), outp))
print("crash target 0x8298A7D0: %s" % ("in the gap list" if 0x8298A7D0 in gap else ("block label" if 0x8298A7D0 in labs else ("already generated/inside" if (0x8298A7D0 in startset or in_func(0x8298A7D0)) else "not found by this scan"))))
print("block labels that are also built in code (not auto-added): %d" % len(labs))
for t in labs[:15]:
    print("  0x%08X" % t)
print()
print("First 20 gap entries:")
for t, size, n in out[:20]:
    print("  0x%08X size 0x%X refs %d" % (t, size, n))