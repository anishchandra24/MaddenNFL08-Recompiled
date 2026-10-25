# Read-only. Looks at what the game's memory image holds at each suggested
# address and splits the suggestions into "looks like code" and "does not".
# usage: python -I check_suggestions_madden.py <project> <image_dump.bin>
import os, re, struct, sys

proj, dump = sys.argv[1], sys.argv[2]
IBASE, CBASE, CEND = 0x82000000, 0x82370000, 0x82370000 + 0x00F5CA1C
sug_path = os.path.join(proj, ".local", "suggested_functions.txt")
line_re = re.compile(r'^0x([0-9A-F]{8}) = \{ size = 0x([0-9A-F]+) \}\s+# (\d+) reference\(s\), first at 0x([0-9A-F]{8})')
data = open(dump, "rb").read()

def word(a):
    o = a - IBASE
    return struct.unpack(">I", data[o:o + 4])[0] if 0 <= o <= len(data) - 4 else 0

BAD_PRIMARY = {0, 1, 9, 22}
def looks_like_code(a):
    w = word(a)
    return w != 0 and (w >> 26) not in BAD_PRIMARY

rows = []
for line in open(sug_path):
    m = line_re.match(line)
    if m:
        t, size, n, r = int(m.group(1), 16), int(m.group(2), 16), int(m.group(3)), int(m.group(4), 16)
        rows.append((t, size, n, r))
print("suggestions read: %d" % len(rows))

good = [x for x in rows if looks_like_code(x[0])]
bad = [x for x in rows if not looks_like_code(x[0])]
print("first word looks like an instruction: %d, looks like data/padding: %d" % (len(good), len(bad)))

in_code = [x for x in good if CBASE <= x[3] < CEND]
in_data = [x for x in good if not (CBASE <= x[3] < CEND)]
print("of the plausible ones, first reference lives in the data area: %d, inside the code area: %d" % (len(in_data), len(in_code)))

blr = [x for x in good if x[1] == 8 and word(x[0] + 4) == 0x4E800020]
print("tiny 2-instruction functions ending in blr: %d" % len(blr))
multi = [x for x in good if x[2] >= 2]
print("plausible ones referenced 2+ times: %d" % len(multi))

crash = [x for x in rows if x[0] == 0x831DA158]
print("crash target 0x831DA158 in the list: %s" % (("yes, size 0x%X, %d refs" % (crash[0][1], crash[0][2])) if crash else "NO"))

def show(title, lst, k=12):
    print()
    print(title)
    for t, size, n, r in lst[:k]:
        print("  0x%08X size 0x%X refs %d  words %08X %08X  (first ref 0x%08X)" % (t, size, n, word(t), word(t + 4), r))

show("Samples that look like DATA (rejected):", bad)
show("Samples whose reference is inside the code area:", in_code)
show("Samples from the data area (typical vtable/function-pointer tables):", in_data[len(in_data)//2:])

outp = os.path.join(proj, ".local", "suggested_filtered.txt")
with open(outp, "w") as o:
    for t, size, n, r in good:
        o.write("0x%08X = { size = 0x%X }\n" % (t, size))
print()
print("wrote %d plausible entries to %s" % (len(good), outp))