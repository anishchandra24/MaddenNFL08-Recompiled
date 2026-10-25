# Read-only. Prints a before/after diff of named functions between two generated folders.
# usage: python -I diff_func_madden.py <old_gen> <new_gen> <name> [<name> ...]
import difflib, glob, os, re, sys

old_dir, new_dir = sys.argv[1], sys.argv[2]
wanted = set(sys.argv[3:])
fn_re = re.compile(r'^DEFINE_REX_FUNC\((\w+)\)')

def grab(d):
    out = {}
    for path in sorted(glob.glob(os.path.join(d, "madden08_recomp.*.cpp"))):
        name = None
        buf = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = fn_re.match(line)
                if m:
                    if name in wanted:
                        out[name] = buf
                    name = m.group(1)
                    buf = []
                elif name in wanted:
                    buf.append(line.rstrip())
        if name in wanted:
            out[name] = buf
    return out

o, n = grab(old_dir), grab(new_dir)
for name in sorted(wanted):
    print("=========== %s ===========" % name)
    if name not in o or name not in n:
        print("  missing in %s" % ("old" if name not in o else "new"))
        continue
    diff = list(difflib.unified_diff(o[name], n[name], "old", "new", lineterm="", n=2))
    print("  %d diff lines" % len(diff))
    for l in diff[:50]:
        print("  " + l[:170])
    if len(diff) > 50:
        print("  ... (%d more)" % (len(diff) - 50))