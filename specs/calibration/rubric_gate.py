"""rubric_gate.py — spec 095 section 5.3.1 step 4.

The promotion gate in promote_rubric.py protects the RUBRIC: it refuses to promote a bad file.
This module protects the REPORT: it refuses to SCORE with a rubric that was not promoted
through that gate, or that has been modified since promotion.

Why a hash and not just a version string
----------------------------------------
The version string is set BY HAND when a rubric is edited directly. This happened repeatedly:
rubric.json was edited in place with the version bumped manually, so the promotion script was
never run and its checks never applied. "The version says 1.16.1" therefore proves nothing
about whether 1.16.1 was ever promoted.

The sidecar `rubric.promoted.json` is written ONLY by promote_rubric.py. It records the version
and the SHA-256 of the promoted bytes. A rubric whose hash does not match its sidecar has been
edited after promotion and is refused, whatever its version claims.

Scope
-----
`rubric.json` (the LIVE rubric) may be scored only if it is stamped. Frozen references
(`rubric-v<X>.json`) are exempt: calibration legitimately scores against retired rubrics, and
the canary's frozen baseline is one of them.

Usage
-----
    from rubric_gate import require_promoted
    require_promoted(HERE / args.rubric)   # raises SystemExit on refusal
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

LIVE_NAME = "rubric.json"
# 1.19.0 (D54): the dimension formerly relative_strength is now position_strength. This module
# reads only version/hash and does not touch dimension keys, so no alias handling is needed here --
# noted so a future reader does not assume the rename was missed.
SIDECAR_NAME = "rubric.promoted.json"


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def sidecar_for(rubric_path) -> Path:
    return Path(rubric_path).resolve().parent / SIDECAR_NAME


def write_stamp(rubric_path) -> dict:
    """Called by promote_rubric.py ONLY, after a successful promotion.

    Written atomically: a crash mid-write must not leave a sidecar that half-describes the
    live rubric, because the gate would then either pass a bad file or refuse a good one.
    """
    rubric_path = Path(rubric_path).resolve()
    V = json.loads(rubric_path.read_text())
    stamp = {
        "version": V["_meta"]["version"],
        "sha256": sha256(rubric_path),
        "promoted_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "promoted_from": os.environ.get("PROMOTED_FROM", ""),
    }
    dst = sidecar_for(rubric_path)
    fd, tmp = tempfile.mkstemp(dir=str(dst.parent), prefix=".promoted-")
    with os.fdopen(fd, "w") as f:
        json.dump(stamp, f, indent=1)
    os.replace(tmp, dst)
    return stamp


def require_promoted(rubric_path) -> None:
    """Refuse to score with an unpromoted or post-promotion-modified LIVE rubric.

    Raises SystemExit (fail loud) -- never a warning. A scored report that came from a rubric
    nothing promoted is the exact failure 5.3.1 exists to prevent: it raises no error and
    produces no symptom until a client is shown a number from a retired instrument.
    """
    rubric_path = Path(rubric_path).resolve()
    if rubric_path.name != LIVE_NAME:
        return  # frozen reference -- calibration may legitimately score against a retired rubric

    if not rubric_path.exists():
        raise SystemExit("FATAL: live rubric %s does not exist" % rubric_path)

    sidecar = sidecar_for(rubric_path)
    if not sidecar.exists():
        raise SystemExit(
            "FATAL: refusing to score -- %s has NO promotion stamp.\n"
            "  Expected sidecar: %s\n"
            "  The live rubric may only be served if it was promoted through\n"
            "  `promote_rubric.py <candidate>`, which writes that stamp. Editing rubric.json\n"
            "  in place bypasses the gate; promote a candidate file instead." % (rubric_path.name, sidecar.name))

    stamp = json.loads(sidecar.read_text())
    actual = sha256(rubric_path)
    if actual != stamp.get("sha256"):
        raise SystemExit(
            "FATAL: refusing to score -- the live rubric was MODIFIED after promotion.\n"
            "  promoted version : %s\n"
            "  promoted sha256  : %s\n"
            "  current  sha256  : %s\n"
            "  `rubric.json` has been edited in place since it was promoted, so the checks in\n"
            "  promote_rubric.py were never applied to the current content. Re-promote it:\n"
            "    python3 promote_rubric.py <candidate-with-your-change>.json"
            % (stamp.get("version"), (stamp.get("sha256") or "")[:16], actual[:16]))

    V = json.loads(rubric_path.read_text())
    if V["_meta"]["version"] != stamp.get("version"):
        raise SystemExit(
            "FATAL: refusing to score -- version stamp disagrees with the promotion record.\n"
            "  rubric _meta.version : %s\n"
            "  promoted version     : %s" % (V["_meta"]["version"], stamp.get("version")))
