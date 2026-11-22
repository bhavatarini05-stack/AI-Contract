"""Self-contained, printable HTML risk report (use the browser's Print → Save as PDF)."""

from __future__ import annotations

from html import escape

from app.models import Contract

SEV_COLOR = {"critical": "#b42318", "high": "#c4320a", "medium": "#b54708", "low": "#475467"}


def render(contract: Contract) -> str:
    r = contract.report
    e = escape
    parties = (
        ", ".join(
            e(p["name"]) + (f" ({e(p['role'])})" if p.get("role") else "")
            for p in (contract.parties or [])
        )
        or "—"
    )
    terms_rows = "".join(
        f"<tr><th>{e(t.label)}</th><td>{e(t.display)}</td><td>{t.page or ''}</td></tr>"
        for t in contract.terms
    )
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    flags = sorted(contract.risk_flags, key=lambda f: order.get(f.severity, 9))
    flag_rows = (
        "".join(
            f"<li><span class='sev' style='background:{SEV_COLOR.get(f.severity, '#475467')}'>{e(f.severity)}</span> "
            f"<b>{e(f.message)}</b>{f' <small>(p. {f.page})</small>' if f.page else ''}"
            f"{f'<div class=sugg>→ {e(f.suggestion)}</div>' if f.suggestion else ''}</li>"
            for f in flags
        )
        or "<li>No risks flagged.</li>"
    )
    obl_rows = (
        "".join(
            f"<li>{e(o.description)}{f' <b>({o.due_date:%b %d, %Y})</b>' if o.due_date else ''}</li>"
            for o in sorted(contract.obligations, key=lambda o: (o.due_date is None, o.due_date))
        )
        or "<li>None identified.</li>"
    )
    points = "".join(f"<li>{e(p)}</li>" for p in (r.key_points or [])) if r else ""
    nego = "".join(f"<li>{e(n['suggestion'])}</li>" for n in (r.negotiation or [])) if r else ""
    warnings = "".join(f"<li>{e(w)}</li>" for w in (contract.warnings or []))

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Contract Report – {e(contract.filename)}</title>
<style>
body{{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:860px;margin:32px auto;padding:0 16px;color:#101828;line-height:1.5}}
h1{{font-size:24px;margin-bottom:4px}} h2{{font-size:18px;margin-top:28px;border-bottom:1px solid #eaecf0;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid #eaecf0;vertical-align:top}}
th{{width:35%;color:#475467;font-weight:600}} .meta{{color:#475467}} .score{{font-size:32px;font-weight:700}}
.sev{{color:#fff;border-radius:4px;padding:1px 6px;font-size:12px;text-transform:uppercase;margin-right:6px}}
.sugg{{color:#344054;margin:2px 0 8px 0}} li{{margin:4px 0}} .disc{{color:#667085;font-size:12px;margin-top:32px}}
.warn{{background:#fffaeb;border:1px solid #fedf89;padding:8px 16px;border-radius:6px}}
</style></head><body>
<h1>{e(contract.filename)}</h1>
<div class="meta">{contract.page_count or "?"} pages · {e(contract.contract_type or "Unknown type")} ·
Governing law: {e(contract.governing_law or "—")} · Parties: {parties}</div>
{f'<div class="warn"><ul>{warnings}</ul></div>' if warnings else ""}
<h2>Risk score</h2>
<div class="score" style="color:{SEV_COLOR.get(r.risk_level if r else "low", "#475467")}">{r.risk_score if r else "–"}/100 · {e((r.risk_level if r else "n/a").title())}</div>
<h2>Plain-language summary</h2><p>{e(r.summary) if r else ""}</p><ul>{points}</ul>
<h2>Key terms</h2><table><tr><th>Term</th><td><b>Value</b></td><td><b>Page</b></td></tr>{terms_rows}</table>
<h2>Risk flags</h2><ul>{flag_rows}</ul>
<h2>Obligations &amp; deadlines</h2><ul>{obl_rows}</ul>
<h2>Negotiation suggestions</h2><ul>{nego or "<li>None.</li>"}</ul>
<p class="disc">Generated {f"{r.generated_at:%Y-%m-%d %H:%M} UTC" if r else "—"}{f" with local model {e(r.llm_model)}" if r and r.llm_model else " (rule-based)"}.
AI-generated analysis — not legal advice. Have a qualified lawyer review important contracts.</p>
</body></html>"""
