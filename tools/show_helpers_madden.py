# Read-only. Shows what the OLD generated code had for the functions that
# disappeared, which of the added manifest entries sit in or next to them, and
# what the NEW generated code has in those same address areas.
# usage: python -I show_helpers_madden.py <old_gen_default> <new_gen_default> <compare.txt> <entries.txt>
import glob, os, re, sys

old_dir, new_dir, cmp_path, ent_path = sys.argv[1:5]
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
hex_re = re.compile(r'0x(8[0-9A-Fa-f]{7})')

lines = open(cmp_path).read().splitlines()
gone = lines[lines.index("DISAPPEARED") + 1:]
gone = [g.strip() for g in gone if g.strip()]
cands = sorted(int(m.group(1), 16) for m in (re.match(r'^\s*0x([0-9A-Fa-f]{8})', l) for l in open(ent_path)) if m)
print("disappeared: %d, candidate entries: %d" % (len(gone), len(cands)))

def scan(d, wanted=None):
    out = {}
    for path in sorted(glob.glob(os.path.join(d, "madden08_recomp.*.cpp"))):
        name = None
        buf = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = fn_re.match(line)
                if m:
                    if name is not None and (wanted is None or name in wanted):
                        out[name] = buf
                    name = m.group(1)
                    buf = []
                    continue
                if name is not None and len(buf) < 40:
                    buf.append(line.rstrip())
            if name is not None and (wanted is None or name in wanted):
                out[name] = buf
    return out

old = scan(old_dir, set(gone))
print()
for g in gone:
    print("=== OLD %s ===" % g)
    for l in old.get(g, ["(not found)"])[:9]:
        print("   " + l)
    if g.startswith("sub_"):
        a = int(g[4:], 16)
        print("   candidate entry at exactly this address: %s" % ("YES" if a in cands else "no"))
    print()

# areas: any 0x8282xxxx / 0x8299Fxxx names, then the NEW functions in those areas
areas = [(0x82824400, 0x82824700), (0x8299F300, 0x8299F600)]
print("=== candidate entries inside the two areas ===")
for lo, hi in areas:
    print("area 0x%08X..0x%08X: %s" % (lo, hi, ", ".join("0x%08X" % c for c in cands if lo <= c < hi) or "none"))
print()
print("=== NEW functions in those areas ===")
new_names = {}
for path in sorted(glob.glob(os.path.join(new_dir, "madden08_recomp.*.cpp"))):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = fn_re.match(line)
            if m:
                n = m.group(1)
                mm = re.match(r'^sub_([0-9A-F]{8})$', n)
                if mm:
                    a = int(mm.group(1), 16)
                    for lo, hi in areas:
                        if lo <= a < hi:
                            new_names[a] = n
for a in sorted(new_names):
    print("  %s" % new_names[a])