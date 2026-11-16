# Decision Record: UI De-AI-ification (Eliminating Emoji Overuse)

> **Decision ID:** `DEC-2026-11-15-01`  
> **Date:** 15 November 2026  
> **Status:** APPROVED  
> **Proposers:** Alok Ae, Dr. Ishaan Wadhwa  
> **Source:** Team Demo Review (`ijt-mtka-pgm`)  

---

## 1. Context & Problem Statement

During the live team demo on 15 November 2026, reviewer Alok Ae highlighted a noticeable design issue in the user interface:
> *"I think emojis is very AI-like... It's clean and nice, but the emojis is very AI-like apart from that."*
Dr. Ishaan Wadhwa confirmed:
> *"I'll remove all emojis again."*

The current Streamlit UI and early component drafts made heavy use of decorative emojis in high-visibility regions:
- Headers: `🪙 Godown Cash Drawer Balancing Cockpit`, `👑 Owner (मालिक)`
- Status Pills: `🔴 🔒 Vault Locked`, `🟢 🔓 Vault Unlocked`
- Download Buttons: `📥 Download Tally XML`, `📊 Download CA Excel Workbook`
- Action Links: `📲 Draft WhatsApp`

While intended to add visual interest, this pattern creates several negative outcomes:
1. **Perception of "AI Slop":** Modern users associate excessive emoji usage with low-effort, uncurated LLM code generators.
2. **Loss of Institutional Trust:** For an enterprise product dealing with Chartered Accountants, MCA Rule 11(g) compliance, and banking overdrafts, emojis diminish seriousness and perceived audit readiness.
3. **Cross-Platform Rendering Inconsistency:** Standard emojis render unpredictably across macOS, Windows, Linux, Android, and iOS, occasionally causing line-height clipping and color clashes.

---

## 2. Decision

1. **Mandate Complete Emoji Removal:** Remove all unicode decorative emojis from headers, button labels, and system status indicators.
2. **Adopt Institutional SVG Iconography:**
   - Standardize on clean, monochrome 16px/20px geometric SVG icons (based on Lucide / Feather icon sets).
   - Use semantic fill/stroke colors conforming to the established design system palette (`#0F172A` Slate Dark, `#64748B` Slate Muted, `#16A34A` Emerald, `#DC2626` Crimson).
3. **Typographic Status Pills:** Replace colored emoji dots with clean typographic pills (e.g. `<span class="status-pill status-locked">Vault Locked</span>`).
4. **Preserve Strategic Action Clarity:** Retain clean WhatsApp brand icon on debtor recovery actions, but remove superfluous decorative sparkles.

---

## 3. Implementation Targets
- Python Streamlit UI: `app/streamlit_app.py`
- Next.js 15+ App Router Components: `apps/web/components/`
- Documentation & Design Guidelines: `docs/audits/ui-ux-pro-max.md`, `docs/specs/02-view-components.md`
