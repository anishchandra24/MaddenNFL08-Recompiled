# Read-only. For each address we added to the manifest from the scan, look at the
# function that sits just before it in the generated code. If that function does
# not end in a return/jump, the new entry probably cut a real function in half.
# usage: python -I check_splits_madden.py <project> <entries_file>
import glob, os, re, sys, bisect

proj, entries = sys.argv[1], sys.argv[2]
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
                cur = [int(a.group(1), 16) if a else None, 0, ""]
                continue
            if cur is not None:
                i = ins_re.match(line)
                if i:
                    cur[1] += 1
                    cur[2] = i.group(1)
if cur and cur[0] is not None:
    funcs.append(tuple(cur))
funcs.sort()
starts = [f[0] for f in funcs]
print("generated functions: %d" % len(funcs))

RET = {"blr", "b", "bctr", "bcctr"}
cands = []
for line in open(entries):
    m = re.match(r'^\s*0x([0-9A-Fa-f]{8})', line)
    if m:
        cands.append(int(m.group(1), 16))

counts = {"clean gap": 0, "adjacent, previous ends with return/jump": 0, "SPLIT (previous falls through)": 0, "overlap": 0, "not generated": 0}
suspicious = []
for x in cands:
    j = bisect.bisect_left(starts, x)
    if j >= len(starts) or starts[j] != x:
        counts["not generated"] += 1
        suspicious.append((x, "not generated as its own function", ""))
        continue
    if j == 0:
        continue
    p = funcs[j - 1]
    pend = p[0] + 4 * p[1]
    if pend > x:
        counts["overlap"] += 1
        suspicious.append((x, "overlap with function 0x%08X..0x%08X" % (p[0], pend), p[2]))
    elif pend == x:
        if p[2] in RET:
            counts["adjacent, previous ends with return/jump"] += 1
        else:
            counts["SPLIT (previous falls through)"] += 1
            suspicious.append((x, "SPLIT: function 0x%08X..0x%08X ends with '%s' and runs into it" % (p[0], pend, p[2]), p[2]))
    else:
        counts["clean gap"] += 1
print("candidates checked: %d" % len(cands))
for k, v in counts.items():
    print("  %-45s %d" % (k, v))
print()
print("Suspicious entries (first 40):")
for x, why, last in suspicious[:40]:
    print("  0x%08X  %s" % (x, why))
outp = os.path.join(proj, ".local", "suspicious_entries.txt")
with open(outp, "w") as o:
    for x, why, last in suspicious:
        o.write("0x%08X  %s\n" % (x, why))
print()
print("wrote %d suspicious entries to %s" % (len(suspicious), outp))