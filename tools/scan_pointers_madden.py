# Finds function addresses the game's data points at that the recompiler did not
# generate. Read-only: it only reads the dump and the generated code, and writes
# a text file of suggested manifest lines.
# usage: python -I scan_pointers_madden.py <project> <image_dump.bin> <run_log>
import glob, os, re, struct, sys, bisect

proj, dump, logf = sys.argv[1], sys.argv[2], sys.argv[3]
base = os.path.join(proj, "generated", "default")
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
addr_re = re.compile(r'^sub_([0-9A-F]{8})$')
ins_re = re.compile(r'^\s+// ([a-z][a-z0-9_.+-]*)( |$)')

funcs = []
cur = None
for path in sorted(glob.glob(os.path.join(base, "madden08_recomp.*.cpp"))):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = fn_re.match(line)
            if m:
                if cur and cur[0] is not None:
                    funcs.append(tuple(cur))
                a = addr_re.match(m.group(1))
                cur = [int(a.group(1), 16) if a else None, 0]
                continue
            if cur is not None and ins_re.match(line):
                cur[1] += 1
if cur and cur[0] is not None:
    funcs.append(tuple(cur))
funcs.sort()
starts = [f[0] for f in funcs]
ends = [f[0] + 4 * f[1] for f in funcs]
print("generated functions: %d" % len(funcs))

txt = open(logf, encoding="utf-8", errors="replace").read()
m = re.search(r'image base ([0-9A-Fa-f]{8}) size ([0-9A-Fa-f]{8}) code base ([0-9A-Fa-f]{8}) code size ([0-9A-Fa-f]{8})', txt)
if not m:
    print("Could not find the 'image base ... code size' line in the log."); sys.exit(1)
ibase, isize, cbase, csize = [int(x, 16) for x in m.groups()]
cend = cbase + csize
print("image %08X..%08X, code %08X..%08X" % (ibase, ibase + isize, cbase, cend))

data = open(dump, "rb").read()
print("dump size: %d bytes (expected %d)" % (len(data), isize))
if len(data) < isize:
    print("Dump is shorter than expected."); sys.exit(1)

def in_generated(t):
    i = bisect.bisect_right(starts, t) - 1
    return i >= 0 and t < ends[i]

words = struct.unpack(">%dI" % (len(data) // 4), data[: len(data) // 4 * 4])
hits = {}
for idx, w in enumerate(words):
    if cbase <= w < cend and (w & 3) == 0 and not (cbase <= ibase + idx * 4 < cend) and not in_generated(w):
        hits.setdefault(w, []).append(ibase + idx * 4)
print("distinct code addresses found in data that are NOT inside a generated function: %d" % len(hits))

def next_start(t):
    i = bisect.bisect_right(starts, t)
    return starts[i] if i < len(starts) else cend

cands = sorted(hits)
out = []
for k, t in enumerate(cands):
    nxt = next_start(t)
    if k + 1 < len(cands) and cands[k + 1] < nxt:
        nxt = cands[k + 1]
    out.append((t, nxt - t, len(hits[t]), hits[t][0]))

outp = os.path.join(proj, ".local", "suggested_functions.txt")
with open(outp, "w") as o:
    for t, size, n, r in out:
        o.write("0x%08X = { size = 0x%X }   # %d reference(s), first at 0x%08X\n" % (t, size, n, r))
print("wrote %d suggestions to %s" % (len(out), outp))
print()
print("First 25 suggestions:")
for t, size, n, r in out[:25]:
    print("0x%08X = { size = 0x%X }   # %d ref(s), first at 0x%08X" % (t, size, n, r))