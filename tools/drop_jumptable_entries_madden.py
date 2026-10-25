# Removes manifest entries that are really jump tables (rows of code addresses),
# not function starts: 3 or more of the first 4 words are 4-byte-aligned
# addresses inside the code area.
# usage: python -I drop_jumptable_entries_madden.py <project> <image_dump.bin>
import os, re, struct, sys

proj, dump = sys.argv[1], sys.argv[2]
IBASE = 0x82000000
CBASE, CEND = 0x82370000, 0x82370000 + 0x00F5CA1C
man_path = os.path.join(proj, "madden08_manifest.toml")
data = open(dump, "rb").read()

def word(a):
    o = a - IBASE
    return struct.unpack(">I", data[o:o + 4])[0] if 0 <= o <= len(data) - 4 else 0

def table_like(a):
    n = 0
    for k in range(4):
        w = word(a + 4 * k)
        if CBASE <= w < CEND and (w & 3) == 0:
            n += 1
    return n >= 3

raw = open(man_path, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
out, removed = [], []
for line in raw.split("\n") if nl == "\n" else raw.split("\r\n"):
    m = re.match(r'^\s*0x([0-9A-Fa-f]{8})\s*=', line)
    if m:
        a = int(m.group(1), 16)
        if table_like(a):
            removed.append((a, line.strip()))
            continue
    out.append(line)
print("manifest entries that look like jump tables: %d" % len(removed))
for a, l in removed:
    print("  %s   words: %s" % (l.split('#')[0].strip(), " ".join("%08X" % word(a + 4 * k) for k in range(4))))
crash = 0x8298A7D0
print("crash target 0x8298A7D0 table-like: %s" % ("YES (would be removed!)" if table_like(crash) else "no (kept)"))
if removed:
    with open(man_path, "wb") as f:
        f.write(nl.join(out).encode("utf-8"))
    print("manifest saved.")