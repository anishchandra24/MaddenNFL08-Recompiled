# Adds function entries to the manifest. Two modes:
#   python -I manifest_tool_madden.py <project> list <file_with_manifest_lines>
#   python -I manifest_tool_madden.py <project> log  <codegen_log>
# "list" appends the lines of the file (skipping addresses already present).
# "log" reads the unresolved call targets out of a failed codegen log and adds
# an entry for each one, sized to the next known function start.
# Exit codes: 0 = something was added, 2 = nothing to add (stop the loop).
import bisect, glob, os, re, sys

proj, mode, src = sys.argv[1], sys.argv[2], sys.argv[3]
man_path = os.path.join(proj, "madden08_manifest.toml")
man = open(man_path, "rb").read().decode("utf-8")

# the manifest must end inside [entrypoint.functions]
heads = re.findall(r'^\s*\[+[^\]\n]+\]+\s*$', man, re.M)
if not heads or heads[-1].strip() != "[entrypoint.functions]":
    print("The manifest does not end with [entrypoint.functions]; refusing to edit it.")
    sys.exit(3)
present = set(int(x, 16) for x in re.findall(r'^\s*0x([0-9A-Fa-f]{8})\s*=', man, re.M))

def read_text(path):
    b = open(path, "rb").read()
    if b[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return b.decode("utf-16", errors="replace")
    return b.decode("utf-8", errors="replace")

new_lines = []
if mode == "list":
    for line in read_text(src).splitlines():
        m = re.match(r'^\s*0x([0-9A-Fa-f]{8})\s*=\s*\{\s*size\s*=\s*0x[0-9A-Fa-f]+\s*\}', line)
        if m and int(m.group(1), 16) not in present:
            new_lines.append(line.strip().split('#')[0].strip())
            present.add(int(m.group(1), 16))
    print("entries to add from the list: %d" % len(new_lines))
else:
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
                elif cur is not None and ins_re.match(line):
                    cur[1] += 1
    if cur and cur[0] is not None:
        funcs.append(tuple(cur))
    funcs.sort()
    gstarts = [f[0] for f in funcs]
    gends = [f[0] + 4 * f[1] for f in funcs]
    starts = sorted(set(gstarts) | present)
    tgt_re = re.compile(r'^\s+0x([0-9A-Fa-f]{8}) from 0x([0-9A-Fa-f]{8})')
    targets = []
    for line in read_text(src).splitlines():
        m = tgt_re.match(line)
        if m:
            t = int(m.group(1), 16)
            if t not in targets:
                targets.append(t)
    print("unresolved targets in the log: %d" % len(targets))
    targets.sort()
    skipped = 0
    for k, t in enumerate(targets):
        if t in present:
            continue
        i = bisect.bisect_right(gstarts, t) - 1
        if i >= 0 and t < gends[i]:
            print("  SKIPPED 0x%08X: inside generated function 0x%08X..0x%08X (needs a look)" % (t, gstarts[i], gends[i]))
            skipped += 1
            continue
        j = bisect.bisect_right(starts, t)
        nxt = starts[j] if j < len(starts) else t + 4
        if k + 1 < len(targets) and targets[k + 1] < nxt:
            nxt = targets[k + 1]
        if nxt - t > 0x2000:
            new_lines.append("0x%08X = {}" % t)   # far from the next function: let codegen find the end
        else:
            new_lines.append("0x%08X = { size = 0x%X }" % (t, nxt - t))
        present.add(t)
    print("entries to add: %d (skipped %d)" % (len(new_lines), skipped))

if not new_lines:
    print("Nothing to add.")
    sys.exit(2)
raw = open(man_path, "rb").read().decode("utf-8")
nl = "\r\n" if "\r\n" in raw else "\n"
if not raw.endswith("\n"):
    raw += nl
raw += nl.join(new_lines) + nl
with open(man_path, "wb") as f:
    f.write(raw.encode("utf-8"))
print("manifest updated: +%d entries" % len(new_lines))
sys.exit(0)