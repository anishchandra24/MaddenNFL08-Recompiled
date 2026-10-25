import glob, os, re, sys

proj = sys.argv[1] if len(sys.argv) > 1 else r"C:\Madden08"
logf = sys.argv[2] if len(sys.argv) > 2 else os.path.join(proj, ".local", "logs", "codegen2.log")
base = os.path.join(proj, "generated", "default")
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
addr_re = re.compile(r'^sub_([0-9A-F]{8})$')
ins_re = re.compile(r'^\s+// ([a-z][a-z0-9_.+-]*)( |$)')
tgt_re = re.compile(r'^\s+0x([0-9A-Fa-f]{8}) from 0x([0-9A-Fa-f]{8})')

funcs = []  # [start, instruction_count, last_mnemonic]
files = sorted(glob.glob(os.path.join(base, "madden08_recomp.*.cpp")))
for path in files:
    cur = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = fn_re.match(line)
            if m:
                if cur and cur[0] is not None:
                    funcs.append(cur)
                a = addr_re.match(m.group(1))
                cur = [int(a.group(1), 16) if a else None, 0, ""]
                continue
            if cur is not None:
                i = ins_re.match(line)
                if i:
                    cur[1] += 1
                    cur[2] = i.group(1)
    if cur and cur[0] is not None:
        funcs.append(cur)
funcs.sort()
print("read %d generated source files, %d functions" % (len(files), len(funcs)))
if not funcs:
    print("No functions found. Check that the generated folder has madden08_recomp.*.cpp files.")
    sys.exit(1)

targets = []
seen = set()
if os.path.exists(logf):
    with open(logf, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = tgt_re.match(line)
            if m:
                t = int(m.group(1), 16)
                if t not in seen:
                    seen.add(t)
                    targets.append((t, int(m.group(2), 16)))
print("%d unresolved targets listed in %s" % (len(targets), logf))
print()
for t, src in targets:
    prev = None
    nxt = None
    for fn in funcs:
        if fn[0] <= t:
            prev = fn
        elif nxt is None:
            nxt = fn
            break
    print("target 0x%08X (called from 0x%08X)" % (t, src))
    if prev is not None:
        pend = prev[0] + 4 * prev[1]
        if t < pend:
            print("   INSIDE generated function 0x%08X..0x%08X" % (prev[0], pend))
            continue
        print("   previous function ends at 0x%08X (last instruction: %s)" % (pend, prev[2] or "?"))
    if nxt is not None:
        print("   next function starts at 0x%08X" % nxt[0])
        print("   distance target -> next function: 0x%X (%d bytes)" % (nxt[0] - t, nxt[0] - t))
    print("   gap start -> target: 0x%X" % (t - (prev[0] + 4 * prev[1]) if prev else 0))

holes = []
for (a, n, last), (b, _, _) in zip(funcs, funcs[1:]):
    end = a + 4 * n
    size = b - end
    if 4 <= size <= 0x100 and last in ("blr", "bctr", "b"):
        holes.append((end, size))
out = os.path.join(proj, ".local", "holes.txt")
with open(out, "w") as o:
    for s, z in holes:
        o.write("0x%08X %d\n" % (s, z))
print()
print("%d possible holes (4-256 bytes after a return/jump), written to %s" % (len(holes), out))
