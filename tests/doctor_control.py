"""Positive control for gate D1 (Chrysalis passes its own doctor): copies this repository's tracked
files into a throwaway git repo, plants one source file with a deferral marker that cites no register
row, and runs doctor on the copy.

Exit 1 (red, as a control must be) only when doctor fails and names the deferral-marker check, so a
doctor that fails for some other reason does not count as proof. Exit 0 means the gate is blind.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MK = "TO" + "DO"


def main() -> int:
    # Tracked files and new ones not yet committed, so the control tests the working tree being judged.
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, text=True,
                             encoding="utf-8", check=True).stdout.splitlines()
    with tempfile.TemporaryDirectory(prefix="doctor-control-") as d:
        copy = pathlib.Path(d) / "chrysalis"
        for rel in tracked:
            src = ROOT / rel
            if src.is_file():
                (copy / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, copy / rel)
        (copy / "scripts" / "planted.py").write_text(f"x = 1  # {MK} finish this\n", encoding="utf-8")
        g = ["git", "-C", str(copy), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
        subprocess.run(["git", "init", "-q", "-b", "main", str(copy)], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "copy"], check=True)
        r = subprocess.run([sys.executable, str(copy / "scripts" / "chrysalis.py"), "doctor", "--repo", str(copy),
                            "--release"], capture_output=True, text=True, encoding="utf-8")
        print(r.stdout)
        if r.stderr.strip():
            print(r.stderr)
        named = any(line.startswith("FAIL  deferral markers") for line in r.stdout.splitlines())
        planted = "scripts/planted.py" in r.stdout
        if r.returncode != 0 and named and planted:
            print("control: doctor refused the planted marker, as required")
            return 1
        print("control: doctor did not refuse the planted marker; gate D1 is blind")
        return 0


if __name__ == "__main__":
    sys.exit(main())
