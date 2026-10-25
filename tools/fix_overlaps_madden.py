# Trims any manifest entry whose declared size runs into the next entry.
# usage: python -I fix_overlaps_madden.py <project>
import os, re, sys

man_path = os.path.join(sys.argv[1], "madden08_manifest.toml")
raw = open(man_path, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
lines = raw.split(nl) if nl == "\r\n" else raw.split("\n")

addr_re = re.compile(r'^\s*0x([0-9A-Fa-f]{8})\s*=')
sized_re = re.compile(r'^(\s*0x([0-9A-Fa-f]{8})\s*=\s*\{\s*size\s*=\s*)0x([0-9A-Fa-f]+)(\s*\}.*)$')

addrs = sorted(set(int(m.group(1), 16) for m in (addr_re.match(l) for l in lines) if m))
changes = 0
for i, l in enumerate(lines):
    m = sized_re.match(l)
    if not m:
        continue
    a, size = int(m.group(2), 16), int(m.group(3), 16)
    j = None
    for x in addrs:
        if x > a:
            j = x
            break
    if j is not None and a + size > j:
        new = j - a
        lines[i] = "%s0x%X%s" % (m.group(1), new, m.group(4))
        print("trimmed 0x%08X: size 0x%X -> 0x%X (next entry at 0x%08X)" % (a, size, new, j))
        changes += 1
if changes:
    with open(man_path, "wb") as f:
        f.write(nl.join(lines).encode("utf-8"))
print("entries trimmed: %d" % changes)