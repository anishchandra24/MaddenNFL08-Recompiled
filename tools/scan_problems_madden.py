# Read-only. Counts things in the generated code that would fail if executed.
# usage: python -I scan_problems_madden.py <generated_default_dir>
import glob, os, re, sys
from collections import Counter, defaultdict

gen = sys.argv[1]
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')
unimpl_re = re.compile(r'// UNIMPLEMENTED: (\S+)')
unres_branch = re.compile(r'REX_FATAL\("Unresolved branch from 0x([0-9A-F]+) to 0x([0-9A-F]+)"')
unres_jump = re.compile(r'REX_FATAL\("Jump target 0x([0-9A-F]+) unresolved at bctr 0x([0-9A-F]+)"')
unimpl = Counter(); unimpl_where = defaultdict(list)
branches = []; jumps = []
other_fatal = Counter()
for path in sorted(glob.glob(os.path.join(gen, "madden08_recomp.*.cpp"))):
    name = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = fn_re.match(line)
            if m:
                name = m.group(1); continue
            if "UNIMPLEMENTED" in line:
                u = unimpl_re.search(line)
                if u:
                    unimpl[u.group(1)] += 1
                    if len(unimpl_where[u.group(1)]) < 3:
                        unimpl_where[u.group(1)].append(name)
            elif "REX_FATAL(" in line:
                b = unres_branch.search(line)
                if b:
                    branches.append((name, b.group(1), b.group(2))); continue
                j = unres_jump.search(line)
                if j:
                    jumps.append((name, j.group(1), j.group(2))); continue
                other_fatal[line.strip()[:110]] += 1
print("=== UNIMPLEMENTED instructions (throw if executed) ===")
if not unimpl:
    print("  none")
for k, v in unimpl.most_common(30):
    print("  %-14s %5d   e.g. %s" % (k, v, ", ".join(unimpl_where[k])))
print()
print("=== unresolved conditional/unconditional branches: %d ===" % len(branches))
for n, a, b in branches[:12]:
    print("  %s: 0x%s -> 0x%s" % (n, a, b))
print("=== unresolved jump-table targets: %d ===" % len(jumps))
for n, t, a in jumps[:12]:
    print("  %s: target 0x%s at bctr 0x%s" % (n, t, a))
print("=== other REX_FATAL lines: %d distinct ===" % len(other_fatal))
for k, v in other_fatal.most_common(10):
    print("  %5d  %s" % (v, k))