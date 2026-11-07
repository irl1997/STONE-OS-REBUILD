#!/usr/bin/env bash
# Structure and configuration checks before any build (F0). Prints PASS, SKIP or FAIL per check.
#   scripts/validate.sh
#   PYTHON=python3.12 scripts/validate.sh     (an interpreter with tomllib and PyYAML)
# Tools: python3 (3.11+, PyYAML), shellcheck, ruff, systemd-analyze, actionlint.
# A missing tool is a FAIL when STONE_REQUIRE_ALL=1 (CI, dev container), a SKIP otherwise.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PY="${PYTHON:-python3}"
fails=0; skips=0
ok()   { echo "PASS  $*"; }
bad()  { echo "FAIL  $*"; fails=$((fails + 1)); }
skip() { if [[ "${STONE_REQUIRE_ALL:-0}" == 1 ]]; then bad "$* (tool missing)"; else echo "SKIP  $*"; skips=$((skips + 1)); fi; }
have() { command -v "$1" >/dev/null 2>&1; }

# 1. required files
missing=0
for f in VERSION LICENSE README.md pyproject.toml \
         image/Containerfile image/config/build.env image/disk_config/iso.toml \
         image/build_files/build.sh image/build_files/check-kernel.sh image/build_files/governor-config.py \
         image/build_files/governor-contract.sh image/build_files/cu40/build-amdgpu.sh image/build_files/cu40/patch-gfx10.py \
         image/build_files/cu40/verify/stone-cu-verify.c image/build_files/cu40/verify/stone-cu-verify.comp \
         system/usr/bin/stone-cu40 system/usr/lib/stone/stone_cu40.py system/usr/lib/systemd/system/stone-cu40-guard.service \
         system/usr/lib/systemd/sleep.conf.d/50-stone-no-sleep.conf \
         system/usr/share/plymouth/themes/stone/stone.plymouth system/usr/share/plymouth/themes/stone/stone.script \
         system/usr/share/plymouth/themes/stone/line.png \
         hardware/bc250.yaml hardware/validation/matrix.yaml \
         .github/workflows/ci.yml .github/workflows/build-image.yml .github/workflows/build-installer.yml \
         .github/workflows/release.yml dev/Containerfile dev/run-tests.sh \
         docs/DECISIONES_TECNICAS.md docs/ARQUITECTURA_STONE_MACHINE.md docs/fases/F0_PLAN.md docs/CONSTRUIR.md; do
    [[ -s "$f" ]] || { bad "missing or empty: $f"; missing=1; }
done
[[ $missing == 0 ]] && ok "required files present"

# 2. version: VERSION is the only source
v="$(tr -d '[:space:]' < VERSION)"
if [[ "$v" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$ ]]; then ok "VERSION $v"; else bad "VERSION '$v' is not X.Y.Z[-pre]"; fi
if grep -rqE 'STONE_VERSION="?[0-9]' system 2>/dev/null; then bad "a version is hard-coded under system/"; else ok "single version source"; fi
if out="$(bash -c 'set -euo pipefail; eval "$(scripts/release-info.sh "v$(tr -d "[:space:]" < VERSION)" 0123456789abcdef --shell)"; echo "${channel}|${tags}"' 2>&1)" \
        && [[ "${out}" == *"|"* && "${out}" != "|"* ]]; then ok "release-info for shells (${out})"; else bad "release-info --shell: ${out}"; fi

# 3. executables
nonexec=0
for f in image/build_files/*.sh image/build_files/*.py image/build_files/cu40/*.sh image/build_files/cu40/*.py \
         scripts/*.sh system/usr/bin/* dev/run-tests.sh; do
    [[ -x "$f" ]] || { bad "not executable: $f"; nonexec=1; }
done
[[ $nonexec == 0 ]] && ok "executable bits"

# 4. shell
if have shellcheck; then
    # docs/diagnostico/stone-diag-readonly.sh is left out on purpose: it is the owner-approved file,
    # checked by its SHA-256, and any edit (even a shellcheck directive) would change that hash.
    if shellcheck -x image/build_files/*.sh image/build_files/cu40/*.sh scripts/*.sh dev/run-tests.sh; then
        ok "shellcheck"; else bad "shellcheck"; fi
else skip "shellcheck"; fi

# 5. python
# compiled in memory: nothing is written next to the sources (the dev container mounts them read only)
if $PY -c 'import sys; [compile(open(p, encoding="utf-8").read(), p, "exec") for p in sys.argv[1:]]' \
        system/usr/lib/stone/*.py image/build_files/*.py image/build_files/cu40/*.py tests/*.py; then
    ok "python compiles"; else bad "python compile"; fi
if have ruff; then
    if ruff check system/usr/lib/stone image/build_files tests; then ok "ruff"; else bad "ruff"; fi
else skip "ruff"; fi

# 6. TOML / YAML / JSON
if $PY - <<'PY'
import sys
try:
    import tomllib
except ImportError:
    print("tomllib missing (Python 3.11+)"); sys.exit(2)
for p in ("image/disk_config/iso.toml", "pyproject.toml"):
    tomllib.load(open(p, "rb"))
try:
    import yaml
except ImportError:
    print("PyYAML missing"); sys.exit(2)
for p in ("hardware/bc250.yaml", "hardware/validation/matrix.yaml", ".github/dependabot.yml", ".github/actionlint.yaml"):
    yaml.safe_load(open(p))
PY
then ok "toml and yaml"
else rc=$?; if [[ $rc == 2 ]]; then skip "toml/yaml (python 3.11+ with PyYAML needed)"; else bad "toml/yaml"; fi; fi

# 7. systemd units
if have systemd-analyze; then
    root="$(mktemp -d)"; mkdir -p "$root/usr/lib/systemd/system"
    cp -a /usr/lib/systemd/system/. "$root/usr/lib/systemd/system/" 2>/dev/null; cp -a /lib/systemd/system/. "$root/usr/lib/systemd/system/" 2>/dev/null
    cp -a system/. "$root/"
    if systemd-analyze verify --man=no --root="$root" "$root"/usr/lib/systemd/system/stone-cu40-guard.service; then
        ok "systemd-analyze verify"; else bad "systemd-analyze verify"; fi
    rm -rf "$root"
else skip "systemd-analyze"; fi
# test switches of the code must never be set by a shipped unit
if grep -rnE 'STONE_(SYSFS_ROOT|CMDLINE|RELEASE|CU40_STATE_DIR|CU_VERIFY|CU40_ALLOW_USER|POLKIT|BUS)' system/usr/lib/systemd; then
    bad "a shipped unit sets a test switch"; else ok "no test switches in shipped units"; fi

# 8. nothing simulated or unfinished in what the image ships
if grep -rnE "SimStoned|fake_governor|FAKE_GOV" system image; then bad "simulation code in the image"; else ok "no simulated hardware in the image"; fi
if grep -rnE "\b(TODO|FIXME|XXX)\b|CAMBIAR-POR|PLACEHOLDER" system image .github 2>/dev/null | grep -v '@IMAGE_REF@\|@UPDATE_REF@'; then
    bad "placeholders in shipped files"; else ok "no placeholders in shipped files"; fi

# 9. workflows
if have actionlint; then
    if actionlint -config-file .github/actionlint.yaml .github/workflows/*.yml; then ok "actionlint"; else bad "actionlint"; fi
else skip "actionlint"; fi
if grep -nE "uses: [^ ]+@(main|master|latest|v[0-9]+)\s*$" .github/workflows/*.yml; then bad "unpinned action (use a commit SHA)"; else ok "actions pinned by SHA"; fi
perm=0; for w in .github/workflows/*.yml; do grep -q "^permissions:" "$w" || { bad "$w: no top-level permissions"; perm=1; }; done
[[ $perm == 0 ]] && ok "workflow permissions declared"

# 10. Containerfile
if grep -q "^RUN bootc container lint" image/Containerfile; then ok "bootc lint step"; else bad "Containerfile without bootc container lint"; fi

echo
if [[ $fails -eq 0 ]]; then echo "VALIDATE: PASS (${skips} skipped)"; exit 0; fi
echo "VALIDATE: FAIL (${fails} failed, ${skips} skipped)"; exit 1
