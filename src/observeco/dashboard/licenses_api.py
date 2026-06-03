"""License API endpoints for the ObserveCo dashboard.

Registers:
  GET  /api/licenses/status        — current license state
  POST /api/licenses/activate      — activate a Pro key
  POST /api/licenses/trial         — start trial
  POST /api/licenses/validate      — ping validation server
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from observeco import license as lic

router = APIRouter(prefix="/api/licenses", tags=["licenses"])


class ActivateRequest(BaseModel):
    key: str
    email: str = ""
    plan: str = "solo"


class TrialRequest(BaseModel):
    confirm: bool = True


@router.get("/status")
async def license_status():
    """Return current license state."""
    return lic.status()


@router.get("/badge", response_class=HTMLResponse)
async def license_badge():
    """Return an HTML badge showing the current tier.
    Wire with: hx-get="/api/licenses/badge" hx-trigger="load, every 30s" hx-swap="outerHTML"
    """
    # Auto-consume expired trials on badge load
    lic.validate_cached()
    state = lic.load()
    is_pro = state.is_pro
    is_trial = state.license_type == "trial"
    is_consumed = state.trial_consumed
    days = state.remains_days
    plan = state.plan or "Solo"
    now_ts = int(time.time())

    if is_pro and is_trial:
        # Active trial
        label = f"TRIAL ({days}d)"
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1e1b4b;border:1px solid #3730a3;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🚀</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#c7d2fe;">{plan} plan — <span style="color:#a5b4fc;">{days}d left</span></span>
    <span style="font-size:10px;color:#64748b;">No charge until trial ends. Cancel anytime.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Subscribe $9/mo</a>
  <button onclick="showCancelTrialConfirm()" class="header-btn" style="background:transparent;border:1px solid #475569;color:#94a3b8;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;">Cancel Trial</button>
</div>""")
    elif is_pro and not is_trial:
        # Paid Pro subscriber
        stale_warn = ""
        if state.validation_stale:
            stale_warn = '<span style="font-size:10px;color:#f59e0b;">⚠️ Validation not refreshed in 24h</span>'
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#064e3b;border:1px solid #059669;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">✅</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#86efac;">Pro · {plan} plan</span>
    <span style="font-size:10px;color:#64748b;">Active subscription</span>
    {stale_warn}
  </div>
  <button onclick="showManageBilling()" class="header-btn" style="background:#059669;color:white;padding:5px 14px;border-radius:6px;border:none;cursor:pointer;font-weight:600;font-size:11px;">Manage Billing →</button>
</div>""")
    elif is_consumed:
        # Trial was cancelled or expired and consumed
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1c1917;border:1px solid #44403c;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🔓</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#a8a29e;">Free · Trial ended</span>
    <span style="font-size:10px;color:#78716c;">Your data is safe. Subscribe to unlock Pro.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Subscribe $9/mo</a>
</div>""")
    elif state.license_type == "free" and state.trial_end and state.trial_end < now_ts:
        # Trial expired but not yet consumed (grace period)
        return HTMLResponse(f"""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:#1c1917;border:1px solid #dc2626;border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">⚠️</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:#fca5a5;">Free · Trial expired</span>
    <span style="font-size:10px;color:#a8a29e;">Pro features are now locked.</span>
  </div>
  <a href="/api/checkout?plan={plan.lower()}&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Restart $9/mo</a>
</div>""")
    else:
        # Fresh free — no trial yet
        return HTMLResponse("""<div id="tierBadge" class="license-card" style="display:flex;align-items:center;gap:10px;padding:6px 12px;background:var(--surface);border:1px solid var(--border);border-radius:10px;font-size:12px;">
  <span style="font-size:16px;">🔓</span>
  <div style="display:flex;flex-direction:column;">
    <span style="font-weight:600;color:var(--fg);">Free</span>
    <span style="font-size:10px;color:var(--muted);">No trial started</span>
  </div>
  <a href="/api/checkout?plan=solo&trial=30" class="header-btn" style="background:#6366f1;color:white;padding:5px 14px;border-radius:6px;text-decoration:none;font-weight:600;font-size:11px;">Start Trial $9/mo</a>
</div>""")


@router.post("/activate")
async def activate_license(req: ActivateRequest):
    """Activate a Pro license key."""
    result = lic.activate_key(req.key, email=req.email, plan=req.plan)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/trial")
async def start_trial(req: TrialRequest):
    """Start 30-day trial."""
    if not req.confirm:
        raise HTTPException(400, "Must confirm trial start")
    result = lic.start_trial()
    return result


@router.post("/validate")
async def revalidate():
    """Force re-validation of the current license key."""
    state = lic.load()
    if not state.key:
        raise HTTPException(400, "No license key configured")
    from observeco.license import _validate_online
    result = _validate_online(state.key)
    if result.get("valid"):
        state.validated_at = int(time.time())
        lic.save(state)
        return {"status": "validated", "plan": result.get("plan", state.plan)}
    return {"status": "error", "message": result.get("error", "Validation failed")}


# ── Cancel Trial ──────────────────────────────────────────────

@router.post("/cancel-trial")
async def cancel_trial():
    """Cancel the current trial. Pro features lock, data preserved."""
    result = lic.cancel_trial()
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ── Admin: License Key Management ─────────────────────────────

class GenerateKeyRequest(BaseModel):
    issued_to: str = ""
    plan: str = "solo"


class RevokeKeyRequest(BaseModel):
    key: str


@router.post("/admin/generate")
async def admin_generate_key(
    req: GenerateKeyRequest,
    x_admin_key: str | None = Header(None),
):
    """Generate a new Pro license key. Admin auth required."""
    from observeco.billing import generate_key, _get_admin_key
    expected = _get_admin_key()
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = generate_key(issued_to=req.issued_to, plan=req.plan)
    return result


@router.post("/admin/revoke")
async def admin_revoke_key(
    req: RevokeKeyRequest,
    x_admin_key: str | None = Header(None),
):
    """Revoke a license key. Admin auth required."""
    from observeco.billing import revoke_key, _get_admin_key
    expected = _get_admin_key()
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return revoke_key(req.key)


@router.get("/admin/keys")
async def admin_list_keys(
    x_admin_key: str | None = Header(None),
):
    """List all issued license keys. Admin auth required."""
    from observeco.billing import list_keys, _get_admin_key
    expected = _get_admin_key()
    if not x_admin_key or x_admin_key != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return list_keys()


@router.get("/admin/keys-page", response_class=HTMLResponse)
async def admin_keys_page(
    x_admin_key: str | None = Header(None),
):
    """Admin page to manage license keys. Admin auth required."""
    from observeco.billing import list_keys, _get_admin_key
    admin_key = _get_admin_key()
    expected = admin_key
    if not x_admin_key or x_admin_key != expected:
        return HTMLResponse('<div style="color:#ef4444;padding:20px;">Unauthorized. Run: observeco dashboard --show-token</div>')

    keys = list_keys()
    rows_lines = []
    if keys:
        for k in keys:
            status_icon = "&#9989;" if not k["revoked"] else "&#10060;"
            revoke_col = "" if k["revoked"] else (
                '<button class="revoke-btn" data-key="' + k["key"] + '" '
                'style="background:transparent;border:1px solid #991b1b;color:#fca5a5;'
                'padding:2px 8px;border-radius:4px;cursor:pointer;font-size:10px;">Revoke</button>'
            )
            activated_by = k.get("activated_by", "") or "&mdash;"
            if k.get("activated_by"):
                activated_by = '<span style="color:#86efac;">' + k["activated_by"] + "</span>"
            rows_lines.append("<tr>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;font-family:monospace;font-size:11px;">' + k["key"] + "</td>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;">' + k["plan"] + "</td>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;">' + (k.get("issued_to", "") or "&mdash;") + "</td>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;">' + status_icon + "</td>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;font-size:11px;color:#64748b;">' + activated_by + "</td>")
            rows_lines.append('<td style="padding:6px 10px;border-bottom:1px solid #1e293b;">' + revoke_col + "</td>")
            rows_lines.append("</tr>")
    else:
        rows_lines.append('<tr><td colspan="6" style="padding:20px;text-align:center;color:#64748b;">No keys issued yet. Generate one above.</td></tr>')

    rows_html = "\n".join(rows_lines)

    html = """<div id="adminKeysPage" style="padding:16px;max-width:900px;margin:0 auto;">
  <h3 style="margin:0 0 4px;color:#f8fafc;font-size:15px;">&#128273; Pro License Keys</h3>
  <p style="color:#64748b;font-size:11px;margin:0 0 16px;">Generate keys for beta testers and contributors. Keys validate locally — no CRM needed.</p>

  <div style="display:flex;gap:8px;margin-bottom:16px;">
    <input id="keyIssueTo" placeholder="Who is this for? (optional)" style="flex:1;background:#0f172a;border:1px solid #334155;color:#e2e8f0;padding:8px 12px;border-radius:6px;font-size:12px;">
    <button onclick="generateKey()" style="background:#6366f1;border:none;color:white;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;">Generate Key</button>
    <button onclick="document.getElementById('keyResult').innerHTML=''" style="background:transparent;border:1px solid #475569;color:#94a3b8;padding:8px 12px;border-radius:6px;cursor:pointer;font-size:11px;">Clear</button>
  </div>

  <div id="keyResult" style="margin-bottom:16px;"></div>

  <div style="overflow-x:auto;">
    <table style="width:100%;border-collapse:collapse;font-size:12px;">
      <thead>
        <tr style="color:#64748b;text-align:left;border-bottom:2px solid #1e293b;">
          <th style="padding:6px 10px;">Key</th>
          <th style="padding:6px 10px;">Plan</th>
          <th style="padding:6px 10px;">Issued To</th>
          <th style="padding:6px 10px;">Active</th>
          <th style="padding:6px 10px;">Activated By</th>
          <th style="padding:6px 10px;"></th>
        </tr>
      </thead>
      <tbody>
""" + rows_html + """\
      </tbody>
    </table>
  </div>

<script>
const _adk = '""" + admin_key + """';
function generateKey() {
  const name = document.getElementById('keyIssueTo').value;
  const result = document.getElementById('keyResult');
  result.innerHTML = '<span style="color:#64748b;">Generating...</span>';
  fetch('/api/licenses/admin/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Admin-Key': _adk},
    body: JSON.stringify({issued_to: name}),
  })
    .then(r => r.json())
    .then(data => {
      if (data.key) {
        const key = data.key;
        result.innerHTML = '<div style="background:#064e3b;border:1px solid #059669;border-radius:8px;padding:12px;"><div style="font-size:11px;color:#86efac;margin-bottom:4px;">Key generated - click to copy:</div><div id="genKeyDisplay" style="font-family:monospace;font-size:14px;color:#e2e8f0;cursor:pointer;user-select:all;">' + key + '</div></div>';
        document.getElementById('genKeyDisplay').onclick = function() {
          navigator.clipboard.writeText(key);
          showToast('Copied!');
        };
        htmx.trigger('#adminKeysPage', 'load');
      } else {
        result.innerHTML = '<span style="color:#ef4444;">Error: ' + (data.detail || 'unknown') + '</span>';
      }
    })
    .catch(e => result.innerHTML = '<span style="color:#ef4444;">Failed: ' + e.message + '</span>');
}
document.addEventListener('click', function(e) {
  if (e.target.classList.contains('revoke-btn')) {
    var key = e.target.getAttribute('data-key');
    if (!confirm('Revoke this key? This will deactivate Pro for anyone using it.')) return;
    fetch('/api/licenses/admin/revoke', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Admin-Key': _adk},
      body: JSON.stringify({key: key}),
    })
      .then(function() { htmx.trigger('#adminKeysPage', 'load'); })
      .catch(function(e) { showToast('Failed: ' + e.message); });
  }
});
</script>
</div>"""

    return HTMLResponse(html)
