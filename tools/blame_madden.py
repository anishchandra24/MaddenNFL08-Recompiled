# Read-only. For every function that changed or disappeared between the OLD and
# NEW generated code, finds which manifest entries sit inside its old address
# range, and which entries produced a function bigger than their declared size.
# usage: python -I blame_madden.py <project> <old_gen_default> <new_gen_default> <compare.txt>
import glob, os, re, sys

proj, old_dir, new_dir, cmp_path = sys.argv[1:5]
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
ins_re = re.compile(r'^\s+// ([a-z][a-z0-9_.+-]*)( |$)')
map_re = re.compile(r'\{\s*0x([0-9A-Fa-f]{8}),\s*(\w+)\s*\}')

def counts(d):
    out = {}
    for path in sorted(glob.glob(os.path.join(d, "madden08_recomp.*.cpp"))):
        name = None
        n = 0
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = fn_re.match(line)
                if m:
                    if name:
                        out[name] = n
                    name = m.group(1)
                    n = 0
                elif name and ins_re.match(line):
                    n += 1
        if name:
            out[name] = n
    return out

def mapping(d):
    mp = {}
    for path in glob.glob(os.path.join(d, "madden08_init*.cpp")):
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = map_re.search(line)
                if m:
                    mp[m.group(2)] = int(m.group(1), 16)
    return mp

old_c, new_c = counts(old_dir), counts(new_dir)
old_map = mapping(old_dir)
print("old functions: %d, new functions: %d" % (len(old_c), len(new_c)))

def addr_of(name):
    m = re.match(r'^sub_([0-9A-F]{8})$', name)
    if m:
        return int(m.group(1), 16)
    return old_map.get(name)

man = open(os.path.join(proj, "madden08_manifest.toml"), "rb").read().decode("utf-8")
ents = []
for m in re.finditer(r'^\s*0x([0-9A-Fa-f]{8})\s*=\s*\{([^}]*)\}', man, re.M):
    sm = re.search(r'size\s*=\s*0x([0-9A-Fa-f]+)', m.group(2))
    ents.append((int(m.group(1), 16), int(sm.group(1), 16) if sm else None))
ents.sort()
print("manifest entries: %d" % len(ents))

lines = open(cmp_path).read().splitlines()
ci = lines.index("CHANGED"); di = lines.index("DISAPPEARED")
changed = [l.split()[0] for l in lines[ci + 1:di] if l.strip()]
gone = [l.strip() for l in lines[di + 1:] if l.strip()]

blame = set()
print()
print("=== CHANGED functions: entries inside their old range ===")
for name in changed:
    a = addr_of(name)
    n = old_c.get(name)
    if a is None or n is None:
        print("  %s: address unknown" % name)
        continue
    end = a + 4 * n
    inside = [e for e, s in ents if a < e < end]
    print("  %s  0x%08X..0x%08X (%d instr)  entries inside: %s" % (name, a, end, n, ", ".join("0x%08X" % e for e in inside) or "none"))
    blame.update(inside)

print()
print("=== DISAPPEARED functions: nearest entries just before them ===")
for name in gone:
    a = addr_of(name)
    if a is None:
        print("  %s: address unknown" % name)
        continue
    before = [(e, s) for e, s in ents if e <= a and a - e <= 0x400]
    print("  %s  at 0x%08X  entries within 0x400 before: %s" % (name, a, ", ".join("0x%08X(size %s)" % (e, ("0x%X" % s) if s is not None else "none") for e, s in before) or "none"))

print()
print("=== entries whose generated function is BIGGER than the size declared ===")
grew = []
for e, s in ents:
    n = new_c.get("sub_%08X" % e)
    if n is None or s is None:
        continue
    if n * 4 > s:
        grew.append(e)
        print("  0x%08X declared 0x%X (%d instr) but generated %d instr" % (e, s, s // 4, n))
if not grew:
    print("  none")

outp = os.path.join(proj, ".local", "blame_entries.txt")
with open(outp, "w") as o:
    for e in sorted(blame | set(grew)):
        o.write("0x%08X\n" % e)
print()
print("entries suggested for removal (inside changed functions or grew): %d, written to %s" % (len(blame | set(grew)), outp))