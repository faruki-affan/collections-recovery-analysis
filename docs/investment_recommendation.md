# Investment recommendation — ₹10 Cr

**Recommended area: Better borrower targeting**  
**Financial impact: not reliably estimable from this dataset**  
**In-sample expected incremental recovery: ₹0 (no detectable targeting lift)**

---

## Decision

Leadership can fund only one of six options. Observational performance is **flat** across vendors, hours, risk, loan type, snapshot status, geography, and PTP source. The one **structural** failure we can prove is that **targeting logic is incoherent**: campaign names, channels, and target definitions do not match, and recommended channel disagrees with campaign channel on 80% of rows.

That is a reason to invest in **targeting instrumentation and policy** (and the experiment to measure it). It is **not** a reason to book incremental recovery in a financial model.

The 11% MoM “win” is a **calendar artifact**, not evidence that any of the six levers recently worked.

## Scorecard (data-backed)

| Option | What the data show | Invest ₹10 Cr? |
| --- | --- | --- |
| 1. Better telephony | Answer rate 19.5–20.7% by vendor; schema v1/v2/v3 coexist; no outage signature | No — lift not distinguishable from noise |
| 2. More collection agents | 1,000 agent_ids; ~10.5–11.2k hours/month; ₹ recovery / hour ~16–17k, stable. Agent attributes unusable. No capacity constraint observed | No — cannot identify good vs bad humans |
| 3. AI voice automation | No IVR vs agentic vs human flag on calls (only INBOUND/OUTBOUND) | No — treatment not in the data |
| 4. Better borrower targeting | Campaign labels contradict definitions; 80% channel mismatch; mix is uniform | **Yes — as a measurement and policy program, not as a booked ROI** |
| 5. WhatsApp/digital | Event types uniform; last-touch 7d leaves most cash unattributed; PTP kept ~25% all sources | No — conversion not identified |
| 6. Field operations | Outcomes uniform (~16% each including PAID); no cost/visit | No — unit economics missing |

## Financials (honest)

| Item | Value | Source |
| --- | --- | --- |
| Cost | **₹10 Cr** | Given budget, not in the dataset |
| Expected incremental recovery | **Not estimable** | Outcomes flat across targeting dimensions; no RCT |
| Working in-sample estimate | **₹0** | DiD on v2/v3 vs legacy around April = **+₹95 per targeted account-month** vs ~₹6,000 mean (noise; identification invalid) |
| ROI | **Not estimable** | Missing increment and missing operating cost |
| Break-even | **Not estimable** | Would require a measured lift and a cost-to-collect |
| Downside | **₹10 Cr spent, ₹0 incremental cash** | Consistent with in-sample flatness |
| Upside (illustrative only, **not estimated**) | Unknown | Do not use in the decision pack as a forecast |
| Confidence on *which* lever is least-wrong | **Medium** (targeting broken as a system) | FACT: label incoherence |
| Confidence on *rupees* | **Very low** | No experiment, no costs |

## Assumptions

1. SUCCESS unique `payment_id` is the cash definition.
2. No material true targeting policy change is visible in monthly mix (strategy_version share is stable).
3. Flat segment rates may be **synthetic uniformity** in this challenge dataset; a live book could differ.
4. ₹10 Cr is spent in one year; no discounting.

## What would make a ₹ number defensible

1. **4–6 week randomized targeting pilot:** 10% holdout on current policy vs new policy (DPD/risk/promise-broken rules that actually match campaign names). Primary endpoint: SUCCESS ₹ per account-day.
2. **Channel experiment** (not last-touch): assign recommended channel, persist `campaign_id` and `target_id` onto payments.
3. **Cost instrumentation:** agent fully-loaded cost, vendor per-connect, WA/SMS tariffs, field visit cost.
4. **Fix identity:** one row per human agent with SCD2; one borrower golden record.
5. **Stop reporting MoM total ₹** without day-count and duplicate-payment controls.

Until those exist, **do not claim** that ₹10 Cr in targeting (or any other lever) returns a multiple.
