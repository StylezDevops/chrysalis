"""Real-input simulation for the control packs (PACKS.md K11, K12), run in Docker on this machine or a
CI runner. Every tool image is pinned by digest. Each stage prints PASS or FAIL with its time, and every
planted defect a stage catches is printed as a stable finding ID:

  FINDING <id> <stage>

  python tests/infra_sim.py              all stages; exit 0 only if every stage passes
  python tests/infra_sim.py --only policy migration
  python tests/infra_sim.py --control    the policy stage run on the planted-bad fixtures as if they were
                                         the project's own: it must fail and name the planted findings

Without Docker it prints SKIPPED and exits 3, never 0 (U2).

Stages:
  policy      checkov on Kubernetes, Terraform, Bicep, ARM and Dockerfile fixtures: the good fixture passes
              every selected check, and the bad fixture fails every one, by finding ID (K11 step 2)
  validate    kubeconform (strict) and hadolint on the good fixtures; a malformed manifest must be refused
  plan        terraform init, validate and plan on a module that needs no cloud account; the plan is
              captured as JSON and must show the one planned change (K11 step 1)
  bicep       az bicep build compiles the Bicep fixtures to ARM (K11 step 2, the format's own validator)
  deploy      a throwaway k3s cluster: apply, wait for the rollout, verify from inside the cluster, and
              show the NetworkPolicy refusing a pod it does not admit (K11 steps 6 and 7)
  rollback    a broken release must fail its rollout; rollout undo brings the last release back, and it is
              verified serving again (K11 step 8)
  migration   Postgres: up, up again with no error and no change, down to the empty schema, up again; the
              planted non-idempotent migration must fail its second run (K12)
"""

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "infra"
IMG = {
    "checkov": "bridgecrew/checkov@sha256:ead6eb24cf9884859566ecb461bf396d0e52bd9c3b9d71a221f3f5e054308347",
    "kubeconform": "ghcr.io/yannh/kubeconform@sha256:0925177fb05b44ce18574076141b5c3d83235e1904d3f952182ac99ddc45762c",
    "hadolint": "hadolint/hadolint@sha256:30a8fd2e785ab6176eed53f74769e04f125afb2f74a6c52aef7d463583b6d45e",
    "terraform": "hashicorp/terraform@sha256:18f9986038bbaf02cf49db9c09261c778161c51dcc7fb7e355ae8938459428cd",
    "k3s": "rancher/k3s@sha256:204d4094343ed60ff60ed4b009785151c43d8f611761929aae3a1beb02fc0adf",
    "postgres": "postgres@sha256:5660c2cbfea50c7a9127d17dc4e48543eedd3d7a41a595a2dfa572471e37e64c",
    "azcli": "mcr.microsoft.com/azure-cli@sha256:6d7791e595999664478813ee6da9b340dc087be87cce9f581ded83cc4bf15ca0",
    "app": "python@sha256:c5ba3deef00c7758561a0f03c26f44f10589263d40e732b8748e0d1f38f6dd89",
    "probe": "busybox@sha256:73aaf090f3d85aa34ee199857f03fa3a95c8ede2ffd4cc2cdb5b94e566b11662",
}
# The reviewed policy set per format: what each check refuses is in its name. A project picks its own
# set; what makes it a control is that every selected check is shown passing on good input and failing,
# by ID, on a planted violation.
POLICY = {
    "kubernetes": ("k8s", ["CKV_K8S_16", "CKV_K8S_20", "CKV_K8S_23", "CKV_K8S_11", "CKV_K8S_13", "CKV_K8S_14"]),
    "terraform": ("terraform", ["CKV_AWS_24", "CKV_AWS_62", "CKV_AWS_63", "CKV_AWS_355"]),
    "bicep": ("bicep", ["CKV_AZURE_3", "CKV_AZURE_44"]),
    "arm": ("arm", ["CKV_AZURE_3", "CKV_AZURE_44"]),
    "dockerfile": ("docker", ["CKV_DOCKER_2", "CKV_DOCKER_3", "CKV_DOCKER_4", "CKV_DOCKER_7"]),
}
K3S = "chrysalis-sim-k3s"
PG = "chrysalis-sim-pg"


def sh(args, timeout=600, input=None):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                       input=input)
    return r.returncode, (r.stdout + r.stderr)


def vol(path: pathlib.Path, target: str, ro=True) -> list[str]:
    return ["-v", f"{path.resolve().as_posix()}:{target}" + (":ro" if ro else "")]


def checkov(side: str, fw: str, folder: str, checks: list[str]) -> tuple[set, int]:
    """(failed check IDs among `checks`, exit code) for one fixture folder."""
    code, out = sh(["docker", "run", "--rm", *vol(FIX / side / folder, "/src"), IMG["checkov"], "-d", "/src",
                    "--framework", fw, "--check", ",".join(checks), "--compact", "--quiet", "-o", "json"])
    # The first JSON value in the output; checkov prints more after it on Linux (measured in CI), which a
    # whole-string json.loads refused.
    starts = [i for i in (out.find("{"), out.find("[")) if i >= 0]
    try:
        data, _ = json.JSONDecoder().raw_decode(out[min(starts):]) if starts else (None, 0)
    except ValueError:
        data = None
    if data is None:
        return {f"<checkov output unreadable: {out[:200]}>"}, code
    reports = data if isinstance(data, list) else [data]
    return {c["check_id"] for r in reports for c in (r.get("results") or {}).get("failed_checks", [])}, code


def stage_policy(control: bool):
    problems, findings = [], []
    for fw, (folder, checks) in POLICY.items():
        good, _ = checkov("bad" if control else "good", fw, folder, checks)
        if good:
            problems.append(f"{fw}: the {'planted' if control else 'good'} fixture fails {sorted(good)}")
            if control:
                findings += [(c, f"policy:{fw}") for c in sorted(good)]
        if control:
            continue
        bad, _ = checkov("bad", fw, folder, checks)
        missed = sorted(set(checks) - bad)
        if missed:
            problems.append(f"{fw}: the planted fixture is not caught by {missed}")
        findings += [(c, f"policy:{fw}") for c in sorted(bad & set(checks))]
    return problems, findings


def stage_validate(_control):
    problems, findings = [], []
    code, out = sh(["docker", "run", "--rm", *vol(FIX / "good" / "k8s", "/m"), IMG["kubeconform"], "-strict",
                    "-summary", "/m"])
    if code:
        problems.append(f"kubeconform refused the good manifest: {out.strip()[:300]}")
    with tempfile.TemporaryDirectory() as d:
        bad = pathlib.Path(d) / "broken.yaml"
        bad.write_text("apiVersion: apps/v1\nkind: Deployment\nmetadata: {name: x}\nspec:\n  replicas: two\n"
                       "  selector: {matchLabels: {app: x}}\n  template:\n    metadata: {labels: {app: x}}\n"
                       "    spec: {containers: [{name: x, image: x}]}\n", encoding="utf-8")
        code, out = sh(["docker", "run", "--rm", *vol(pathlib.Path(d), "/m"), IMG["kubeconform"], "-strict", "/m"])
        if code == 0:
            problems.append("kubeconform accepted a Deployment whose replicas is a string")
        else:
            findings.append(("KUBECONFORM-INVALID-MANIFEST", "validate:kubeconform"))
    for side in ("good", "bad"):
        code, out = sh(["docker", "run", "--rm", "-i", IMG["hadolint"], "hadolint", "-"],
                       input=(FIX / side / "docker" / "Dockerfile").read_text(encoding="utf-8"))
        if side == "good" and code:
            problems.append(f"hadolint refused the good Dockerfile: {out.strip()[:300]}")
        if side == "bad":
            codes = sorted({w for w in out.split() if w.startswith("DL")})
            if not codes:
                problems.append("hadolint found nothing in the planted Dockerfile")
            findings += [(c.rstrip(":"), "validate:hadolint") for c in codes]
    return problems, findings


def stage_plan(_control):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        work = pathlib.Path(d) / "tf"
        shutil.copytree(FIX / "good" / "terraform-plan", work)
        # As the calling user, so what terraform writes into the mounted folder can be cleaned up (measured
        # in CI: as root, the temp folder could not be removed and the run crashed).
        user = ["--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp"] if hasattr(os, "getuid") else []
        run = ["docker", "run", "--rm", *user, *vol(work, "/w", ro=False), "-w", "/w", IMG["terraform"]]
        for step in (["init", "-input=false", "-no-color"], ["validate", "-no-color"],
                     ["plan", "-input=false", "-no-color", "-out=plan.bin"]):
            code, out = sh(run + step)
            if code:
                return [f"terraform {step[0]} failed: {out.strip()[-400:]}"], []
        code, out = sh(run + ["show", "-json", "plan.bin"])
        try:
            plan = json.loads(out[out.index("{"):])
        except ValueError:
            return [f"terraform show -json gave no plan: {out[:200]}"], []
        changes = [c["address"] for c in plan.get("resource_changes", []) if c["change"]["actions"] == ["create"]]
        if changes != ["local_file.release_notes"]:
            return [f"the captured plan shows {changes}, not the one planned file"], []
        return [], [("TF-PLAN-CAPTURED", "plan")]


def stage_bicep(_control):
    problems = []
    for side in ("good", "bad"):
        code, out = sh(["docker", "run", "--rm", *vol(FIX / side / "bicep", "/b"), IMG["azcli"], "sh", "-c",
                        "az bicep install >/dev/null 2>&1; az bicep build --file /b/main.bicep --stdout"], timeout=900)
        if code or '"Microsoft.Storage/storageAccounts"' not in out:
            problems.append(f"az bicep build failed on the {side} fixture: {out.strip()[-300:]}")
    return problems, ([("BICEP-BUILT", "bicep")] if not problems else [])


def kubectl(*args, timeout=180, input=None):
    return sh(["docker", "exec", "-i", K3S, "kubectl", *args], timeout=timeout, input=input)


def probe(labels: str):
    return kubectl("run", f"probe-{int(time.time() * 1000) % 100000}", "-n", "sim", "--image", IMG["probe"],
                   "--image-pull-policy=IfNotPresent", f"--labels={labels}", "--restart=Never", "--rm", "-i",
                   "--quiet", "--command", "--", "wget", "-qO-", "-T", "5", "http://web:8080/", timeout=120)


def start_k3s():
    sh(["docker", "rm", "-f", K3S])
    code, out = sh(["docker", "run", "-d", "--privileged", "--name", K3S, IMG["k3s"], "server",
                    "--disable=traefik", "--disable=metrics-server"])
    if code:
        return f"k3s did not start: {out[:300]}"
    deadline = time.time() + 180
    while time.time() < deadline:
        code, out = kubectl("get", "nodes", timeout=30)
        if code == 0 and " Ready" in out:
            break
        time.sleep(3)
    else:
        return "the k3s node never became Ready"
    # The cluster pulls the pinned digests itself. Loading them from the host does not work where Docker's
    # image store saves a multi-platform index with only one platform's layers (measured: ctr reports
    # "content digest not found").
    for image in (IMG["app"], IMG["probe"]):
        code, out = sh(["docker", "exec", K3S, "crictl", "pull", image], timeout=300)
        if code:
            return f"the cluster could not pull {image}: {out[-200:]}"
    return None


def stage_deploy(_control):
    why = start_k3s()
    if why:
        return [why], []
    manifest = (FIX / "good" / "k8s" / "app.yaml").read_text(encoding="utf-8")
    code, out = kubectl("apply", "-f", "-", input=manifest)
    if code:
        return [f"apply failed: {out[:300]}"], []
    code, out = kubectl("-n", "sim", "rollout", "status", "deploy/web", "--timeout=180s", timeout=240)
    if code:
        return [f"the rollout did not finish: {out[-300:]}"], []
    code, out = kubectl("-n", "kube-system", "rollout", "status", "deploy/coredns", "--timeout=120s", timeout=180)
    if code:
        return [f"cluster DNS never became ready: {out[-200:]}"], []
    # CoreDNS reporting ready is not the service name resolving (measured: "bad address" once in two full
    # runs). The admitted probe is retried until it answers, for up to 60 s; it never answering fails.
    deadline = time.time() + 60
    while True:
        code, out = probe("role=probe")
        answered = code == 0 and ("<html" in out.lower() or "directory listing" in out.lower())
        if answered or time.time() > deadline:
            break
        time.sleep(3)
    if not answered:
        return [f"the running service did not answer the admitted probe within 60 s: {out[-300:]}"], []
    findings = [("K8S-SERVICE-VERIFIED", "deploy")]
    # The refusal counts only as a refused or timed-out connection, after the admitted probe has shown
    # DNS and the service work. Measured: right after start, DNS fails both probes with "bad address",
    # and a refusal read from that is red for the wrong reason (R-23); k3s's policy controller rejects,
    # so the refusal arrives as "connection refused" rather than a timeout.
    code, out = probe("role=stranger")
    if code == 0:
        return ["the NetworkPolicy let a pod it does not admit reach the service"], findings
    if not any(s in out.lower() for s in ("timed out", "connection refused")):
        return [f"the refused probe failed, but not by the policy (no timeout): {out[-200:]}"], findings
    # Positive control (U2): with the policy removed the same stranger gets through, so the refusal above
    # came from the policy and nothing else. The policy is put back for the stages after this one.
    kubectl("-n", "sim", "delete", "networkpolicy", "web-ingress")
    time.sleep(3)
    code, out = probe("role=stranger")
    kubectl("apply", "-f", "-", input=manifest)
    if code:
        return [f"even without the policy the stranger was refused, so the refusal proved nothing: {out[-200:]}"], \
            findings
    findings.append(("K8S-NETWORKPOLICY-ENFORCED", "deploy"))
    return [], findings


def stage_rollback(_control):
    code, out = kubectl("-n", "sim", "get", "deploy/web")
    if code:
        why = start_k3s() or None
        if why:
            return [why], []
        p, _ = stage_deploy(False)
        if p:
            return p, []
    patch = json.dumps({"spec": {"template": {"spec": {"containers": [
        {"name": "web", "command": ["sh", "-c", "exit 1"]}]}}}})
    code, out = kubectl("-n", "sim", "patch", "deploy/web", "-p", patch)
    if code:
        return [f"could not roll out the broken release: {out[:300]}"], []
    code, out = kubectl("-n", "sim", "rollout", "status", "deploy/web", "--timeout=45s", timeout=90)
    problems, findings = [], []
    if code == 0:
        return ["the broken release reported a successful rollout"], []
    findings.append(("K8S-BROKEN-RELEASE-DETECTED", "rollback"))
    code, out = kubectl("-n", "sim", "rollout", "undo", "deploy/web")
    if code:
        return [f"rollout undo failed: {out[:300]}"], findings
    code, out = kubectl("-n", "sim", "rollout", "status", "deploy/web", "--timeout=180s", timeout=240)
    if code:
        return [f"the undone release did not come back: {out[-300:]}"], findings
    code, out = probe("role=probe")
    if code:
        problems.append(f"after rollback the service did not answer: {out[-300:]}")
    else:
        findings.append(("K8S-ROLLBACK-VERIFIED", "rollback"))
    return problems, findings


def psql(sql: str):
    return sh(["docker", "exec", "-i", PG, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "sim", "-q"],
              input=sql, timeout=60)


def schema():
    return sh(["docker", "exec", PG, "pg_dump", "-U", "postgres", "-d", "sim", "--schema-only", "--no-owner"])[1]


def stage_migration(_control):
    sh(["docker", "rm", "-f", PG])
    code, out = sh(["docker", "run", "-d", "--name", PG, "-e", "POSTGRES_PASSWORD=sim", "-e", "POSTGRES_DB=sim",
                    IMG["postgres"]])
    if code:
        return [f"postgres did not start: {out[:300]}"], []
    deadline = time.time() + 90
    while time.time() < deadline and sh(["docker", "exec", PG, "pg_isready", "-U", "postgres", "-d", "sim"])[0]:
        time.sleep(1)
    time.sleep(2)
    up = (FIX / "good" / "migrations" / "001_up.sql").read_text(encoding="utf-8")
    down = (FIX / "good" / "migrations" / "001_down.sql").read_text(encoding="utf-8")
    empty = schema()
    problems, findings = [], []
    for label, sql in (("first up", up),):
        code, out = psql(sql)
        if code:
            return [f"{label} failed: {out[:300]}"], []
    after_up = schema()
    code, out = psql(up)
    if code:
        problems.append(f"the second up failed: {out[:300]}")
    elif schema() != after_up:
        problems.append("the second up changed the schema")
    code, out = psql(down)
    if code or schema() != empty:
        problems.append("down did not return the database to the empty schema")
    code, out = psql(up)
    if code or schema() != after_up:
        problems.append("up after down did not rebuild the same schema")
    if not problems:
        findings.append(("MIGRATION-UP-UP-DOWN-UP", "migration"))
    psql(down)
    bad = (FIX / "bad" / "migrations" / "001_up.sql").read_text(encoding="utf-8")
    psql(bad)
    code, _ = psql(bad)
    if code == 0:
        problems.append("the planted non-idempotent migration ran twice without error")
    else:
        findings.append(("MIGRATION-NOT-IDEMPOTENT", "migration"))
    return problems, findings


STAGES = {"policy": stage_policy, "validate": stage_validate, "plan": stage_plan, "bicep": stage_bicep,
          "deploy": stage_deploy, "rollback": stage_rollback, "migration": stage_migration}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--only", nargs="*", choices=sorted(STAGES))
    ap.add_argument("--control", action="store_true")
    ap.add_argument("--keep", action="store_true", help="leave the k3s and postgres containers running")
    args = ap.parse_args()
    if shutil.which("docker") is None or sh(["docker", "info"], timeout=60)[0]:
        print("SKIPPED: Docker is not available on this machine")
        return 3
    names = ["policy"] if args.control else (args.only or list(STAGES))
    failed = 0
    try:
        for name in names:
            start = time.time()
            try:
                problems, findings = STAGES[name](args.control)
            except subprocess.TimeoutExpired as e:
                problems, findings = [f"timed out: {e.cmd[:3]}"], []
            except Exception as e:  # a stage that raises is that stage's failure; the run goes on (U18)
                problems, findings = [f"raised {type(e).__name__}: {e}"], []
            for fid, where in findings:
                print(f"FINDING {fid} {where}")
            status = "PASS" if not problems else "FAIL"
            failed += bool(problems)
            print(f"{status}  {name} ({time.time() - start:.0f}s)")
            for p in problems:
                print(f"      {p}")
    finally:
        if not args.keep:
            sh(["docker", "rm", "-f", K3S, PG])
    print("RESULT:", "OK" if not failed else f"FAIL ({failed} stage(s))")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
