#!/usr/bin/env python3
"""
smoke_test.py — cross-platform regression guards (target-leak + portability).

Runs on the non-MOSIP com.acme fixture. Portable by construction: ALL file I/O uses
Python tempfiles (no '/tmp' literal, no path handed across a bash<->python boundary —
the very Windows bug class this guards against). Exit 0 if all guards pass.

  python smoke_test.py        # or via the smoke_test.sh wrapper
"""
import json, os, subprocess, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.abspath(os.path.join(HERE, "..", ".."))
JAR = os.path.join(ATLAS, "adapters", "java-maven", "callgraph-jvm", "target", "callgraph.jar")
FIX = os.path.join(HERE, "fixtures", "acme", "src", "main", "java")
PY = sys.executable  # same interpreter for every sub-tool — no python3/py mismatch

fails = []
def ok(m): print(f"  ✓ {m}")
def bad(m): print(f"  ✗ {m}"); fails.append(m)

def have(cmd):
    return shutil.which(cmd) is not None

def main():
    print("== system-atlas smoke test (non-MOSIP fixture, portable harness) ==")

    if not os.path.isfile(JAR):
        if have("mvn"):
            subprocess.run(["mvn", "-q", "-DskipTests", "package"],
                           cwd=os.path.join(ATLAS, "adapters", "java-maven", "callgraph-jvm"),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.isfile(JAR):
            bad("callgraph.jar missing and could not be built — cannot run GUARD 1/2")
            return finish()

    # GUARD 1 — target-leak: interface->impl override edges emit on a non-MOSIP package.
    # Pipe the jar's stdout straight into json (no intermediate file path crosses a boundary).
    cg = None
    try:
        out = subprocess.run(["java", "-jar", JAR, "--src", FIX],
                             capture_output=True, text=True, check=True).stdout
        cg = json.loads(out)
        n = cg["counts"]["override_edges"]
        edge = any(e.get("dispatch") == "override" and e["callee"]["owner_fqn"] == "com.acme.RepoImpl"
                   for e in cg["edges"])
        if n >= 1 and edge:
            ok(f"override edges emit on com.acme (interface->impl, generic) [override_edges={n}]")
        else:
            bad(f"override edges NOT emitted on com.acme (target-leak regression!) override_edges={n}")
    except Exception as e:
        bad(f"GUARD 1 could not run the jar: {type(e).__name__}: {e}")

    # GUARD 2 — seq_diagram infers the project package (no hardcoded MOSIP default).
    if cg is not None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        try:
            json.dump(cg, tmp); tmp.close()
            r = subprocess.run([PY, os.path.join(ATLAS, "tools", "seq_diagram.py"),
                                tmp.name, "Svc#run", "--depth", "2"],
                               capture_output=True, text=True)
            if "inferred --project=com.acme" in (r.stderr + r.stdout):
                ok("seq_diagram infers --project=com.acme (no MOSIP default)")
            else:
                bad("seq_diagram did not infer com.acme")
        finally:
            os.unlink(tmp.name)

    # GUARD 3 — portability: finalize survives a degraded pack with no 90-evidence/ dir.
    if have("bash"):
        d = tempfile.mkdtemp()
        pack = os.path.join(d, "behavior-baselines", "toy-pack")
        os.makedirs(os.path.join(pack, "03-operations"))
        r = subprocess.run(["bash", os.path.join(ATLAS, "tools", "finalize_pack.sh"), pack, PY],
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.isfile(os.path.join(pack, "MANIFEST.md")):
            ok("finalize survives a degraded/non-Java pack (mkdir 90-evidence)")
        else:
            bad(f"finalize crashed on a degraded pack (rc={r.returncode})")
        shutil.rmtree(d, ignore_errors=True)
    else:
        print("  ~ GUARD 3 skipped (no bash; finalize is a shell script)")

    return finish()

def finish():
    print()
    if not fails:
        print("SMOKE: PASS"); return 0
    print(f"SMOKE: FAIL ({len(fails)})"); return 1

if __name__ == "__main__":
    sys.exit(main())
