# Decision log

Illustrative sample. Acme is an invented company and every person, figure and date here is made up.

<!-- decision-record log v1. Written by scripts/record.py. Change it through the scripts so every record stays valid. -->

## D-0001: Quote drafts use the trade's own price book

- Status: decided
- Decision: The assistant drafts quotes from each trade's own price book, not Acme's default rates.
- Options considered:
  - Acme default rates
  - The trade's own price book
- Chosen: The trade's own price book
- Decided by: Maya Ortiz
- Date: 2026-09-08
- Owner: Tom Okafor
- Review by: 2026-10-20
- Reversible: yes
- Success signal: Quote edit rate below 25% within six weeks (illustrative)
- Opened: 2026-09-01
- Source: Slack #quotes-squad (illustrative)
- Evidence: Maya Ortiz: Price book it is.
- Outcome: worked
- Outcome date: 2026-10-20
- Outcome evidence: Quote edit rate fell from 41% to 22% over six weeks (illustrative)

## D-0002: Chase reminders go by SMS as well as email

- Status: decided
- Decision: Invoice chase reminders send by SMS as well as email.
- Options considered:
  - Email only
  - Email and SMS
- Chosen: Email and SMS
- Decided by: Raj Mehta
- Date: 2026-09-26
- Owner: Sam Whitfield
- Review by: 2026-11-01
- Reversible: yes
- Success signal: Paid-within-14-days rate above 65% by 2026-11-01 (illustrative)
- Opened: 2026-09-15
- Source: Finance and product sync notes (illustrative)
- Evidence: Raj Mehta: Let's go with SMS too.
- Outcome: missed
- Outcome date: 2026-11-01
- Outcome evidence: Paid-within-14-days rate flat at 58% (illustrative)

## D-0003: Drafted quotes keep a full audit trail for seven years

- Status: decided
- Decision: Every drafted quote and each edit to it is kept for seven years.
- Options considered:
  - Keep 12 months
  - Keep seven years
- Chosen: Keep seven years
- Decided by: Priya Raman
- Date: 2026-10-10
- Owner: Lena Brandt
- Review by: 2026-11-10
- Reversible: no
- Success signal: Audit requests answered in under 1 day (illustrative)
- Opened: 2026-10-01
- Source: Data review meeting (illustrative)
- Evidence: Priya Raman: Seven years, decided.

## D-0004: The assistant writes chase messages in the trade's own tone

- Status: decided
- Decision: Chase messages copy the tone of the trade's past emails.
- Options considered:
  - One house tone
  - The trade's own tone
- Chosen: The trade's own tone
- Decided by: Maya Ortiz
- Date: 2026-10-23
- Owner: Sam Whitfield
- Review by: 2026-11-20
- Reversible: yes
- Success signal: Reply rate to chase messages up 5 points in four weeks (illustrative)
- Opened: 2026-10-20
- Source: Slack #invoices-squad (illustrative)
- Evidence: Maya Ortiz: Go ahead with their own tone.
- Outcome: pending
- Outcome date: 2026-11-20
- Outcome evidence: Reply rate up 3 points on 2 weeks of data (illustrative)

## D-0005: What replaces the day 7 invoice chase default?

- Status: open
- Decision: Keep day 7 for everyone, or let each trade pick with day 7 as the default.
- Options considered:
  - Keep day 7 for everyone
  - Per-trade setting, day 7 default
- Opened: 2026-11-18
- Waiting on: Raj Mehta
- Decide by: 2026-12-02
- Recommendation: Sam Whitfield recommends the per-trade setting
- Source: Meeting notes, invoice chasing cadence (illustrative)
- Evidence: Raj to come back with the cash numbers and we pick this up next week.

## D-0006: Does the assistant answer customer replies on its own?

- Status: open
- Opened: 2026-10-28
- Source: Slack #support (illustrative)

## D-0007: Which squad owns the quote accuracy metric?

- Status: open
- Options considered:
  - Quotes squad
  - Data platform squad
- Opened: 2026-11-13
- Waiting on: Lena Brandt
- Decide by: 2026-11-20
- Source: Squad leads sync (illustrative)

## D-0008: Do we charge for the assistant on the Starter plan?

- Status: open
- Waiting on: Head of Finance
- Source: Pricing review (illustrative)

## D-0009: Should quotes support three currencies at launch?

- Status: dropped
- Opened: 2026-09-20
- Source: Roadmap review (illustrative)
- Dropped because: Acme sells in one market until next year.
