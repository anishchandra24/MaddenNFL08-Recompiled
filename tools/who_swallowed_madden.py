# Read-only. usage: python -I who_swallowed_madden.py <old_gen> <new_gen> <entries.txt>
import glob, os, re, sys

old_dir, new_dir, ent_path = sys.argv[1:4]
names = ["__restfpr_14", "__restgprlr_14", "__restvmx_14", "__savefpr_14", "__savegprlr_14", "__savevmx_14"]
subs = [0x82824560, 0x82824574, 0x82824588, 0x8282459C, 0x8299F410, 0x8299F494, 0x8299F4EC]

ents = []
for l in open(ent_path):
    m = re.match(r'^\s*0x([0-9A-Fa-f]{8}) = \{ size = 0x([0-9A-Fa-f]+) \}', l)
    if m:
        ents.append((int(m.group(1), 16), int(m.group(2), 16)))
ents.sort()

def grep(d, label):
    print("=== %s: lines mentioning the 6 helper names (not their definitions) ===" % label)
    shown = {n: 0 for n in names}
    pat = re.compile("|".join(names))
    for path in sorted(glob.glob(os.path.join(d, "*.cpp")) + glob.glob(os.path.join(d, "*.h"))):
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                m = pat.search(line)
                if m and "DEFINE_REX_FUNC" not in line:
                    n = m.group(0)
                    if shown[n] < 3:
                        shown[n] += 1
                        print("  %s:%d: %s" % (os.path.basename(path), i, line.strip()[:150]))
    print()

grep(old_dir, "OLD")
grep(new_dir, "NEW")

print("=== entries whose range covers one of the 7 missing sub_ addresses ===")
for a in subs:
    cov = [(e, s) for e, s in ents if e <= a < e + s]
    print("  0x%08X covered by: %s" % (a, ", ".join("0x%08X size 0x%X" % x for x in cov) or "no entry"))
print()
print("=== the 12 entries with the largest size ===")
for e, s in sorted(ents, key=lambda x: -x[1])[:12]:
    print("  0x%08X size 0x%X" % (e, s))
print()
print("=== entries within 0x100 of the sub_ addresses ===")
for a in subs:
    near = [(e, s) for e, s in ents if abs(e - a) <= 0x100]
    print("  near 0x%08X: %s" % (a, ", ".join("0x%08X(0x%X)" % x for x in near) or "none"))