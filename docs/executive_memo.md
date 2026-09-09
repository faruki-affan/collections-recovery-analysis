# Executive memo — collections recovery claim

**To:** Leadership  
**From:** Independent analytics  
**Subject:** The 11% recovery improvement is a calendar effect, not an operational win  
**Window:** 1 Jan 2026 – 8 Aug 2026 (7.3 months of events, 30,000-account closed book)

## What happened?

Reported: *“Recovery has improved by 11% month-on-month.”*

Independently, **SUCCESS cash after removing duplicate `payment_id`s** is ₹1,315.6 Cr in the window.

February → March total rupees rose **+11.03%** (₹17.01 Cr/day-month → ₹18.89 Cr). That is the only comparison that matches the claim.

March has 31 days, February 28 (**+10.71%** more days). Recovery **per day** rose **+0.29%**. Recovery per paying account was **slightly down**. RPC stayed ~20%. PTP kept stayed ~25%. Recovery per agent-hour stayed ~₹16–17k.

**Fact:** headline MoM is almost entirely extra calendar days, not better collections.

Other months: January→February **−9.1%** rupees (also a day-count story). April **−4.2%** per day (largest complete-month operational dip). August looks like **−75%** if compared to July on totals — it is an 8-day month.

Duplicates in raw payments inflate SUCCESS by **₹2.59 Cr (~1.9%)**. They do not create the 11%.

## Why did it happen?

| Driver | Classification | Evidence |
| --- | --- | --- |
| Calendar length (28 vs 31 days) | **Fact** | Per-day series is flat; 31/28 ≈ 10.7% vs observed 11.0% |
| Duplicate payment ingestion | **Fact** | 500 extra `payment_id` rows; exact copies |
| Last-touch / latest-campaign attribution | **Hypothesis** if used in the report; **not used** in ours | Payments have no campaign id; 7-day last-touch misses most cash |
| Portfolio mix shift | **Not supported** | Targeted risk mix ~25/25/25/25 all months; snapshot DPD not a history |
| Better agents / vendors / hours | **Not supported** | Connect rates and recovery rates are essentially uniform |
| Targeting strategy upgrade | **Not supported as a sharp change** | legacy/v1/v2/v3 mix stable; campaign labels contradict definitions (**Fact** of incoherence) |

Simpson’s paradox: using only paying accounts, intensity did not improve; using totals, it “did.” Survivorship: snapshot `PAID`/`CLOSED`/`WRITEOFF` still show ~44% ever-paid — snapshot status is not the live book (**Fact:** 12% agreement with last history status). Selection: only 23k of 30k accounts ever appear in targeting; we still keep 30k in the denominator.

## How confident are we?

- **High** that Feb–Mar +11% is not operational improvement.
- **High** that payment duplicates and broken identity tables exist.
- **Medium** that “better targeting” is the least-wrong ₹10 Cr *theme*, because targeting metadata is internally false.
- **Very low** on any rupee ROI for the six investment options. Segment outcomes are flat; that may be real or synthetic. We do not invent a lift.

Data the CEO should not ignore: borrower and agent masters are not usable as people; geography is majority-vote at best; there are **no cost fields**.

## What should we do?

**Invest the ₹10 Cr in better borrower targeting — as a measurement and policy rebuild, not as a booked collections machine.**

Do not buy more dialer capacity, more agents, AI voice, WhatsApp, or field scale on this evidence. Those channels are indistinguishable in-sample, and we cannot see human vs bot.

Immediate reporting changes (cheap, high value):

1. Publish recovery **per day** and **per account**, never only total ₹ MoM.
2. Deduplicate `payment_id` before dashboards. Never dedupe on `payment_reference` (it collides across accounts).
3. Never attribute cash to the latest call by default.
4. Freeze a 30,000-account (or true eligible) denominator.

## Expected financial impact of the ₹10 Cr

| | |
| --- | --- |
| Incremental recovery | **Not estimable.** In-sample DiD ≈ **₹95 / targeted account-month** (noise; design not causal) → treat expected lift as **₹0** until a pilot. |
| Cost | ₹10 Cr (budget) |
| ROI / break-even | **Not estimable** without a measured lift and cost-to-collect |
| Downside | ₹10 Cr in, ₹0 extra cash |
| Range | We refuse a fake confidence interval around a fake lift |

**Pilot that would unlock a number:** 4–6 week RCT of a *real* DPD/promise-broken policy vs current random-like targeting; stamp `target_id` on payments; collect channel costs.

Until then, the honest story for the board: **collections did not improve by 11%. The calendar did.**
