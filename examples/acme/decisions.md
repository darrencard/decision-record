# Decision log

<!-- decision-record log v1. Written by scripts/record.py. Change it through the scripts so every record stays valid. -->

## D-0001: Build quote drafting now, against its landing brief

- Status: decided
- Decision: The Quoting squad builds quote drafting now, against the landing brief as written, with a review on the brief's date.
- Options considered:
  - Build quote drafting now
  - Hold it until auto-match ships
- Chosen: Build quote drafting now
- Decided by: Head of Product, Quoting squad
- Date: 2026-07-27
- Owner: Quoting squad lead
- Review by: 2026-11-15
- Reversible: yes
- Success signal: Quote draft acceptance rate at 40% or higher by 2026-11-15, as the landing brief sets.
- Assumptions:
  - Tradespeople accept a draft they can edit
  - 9,000 tokens per task is enough for a full quote
- Opened: 2026-07-20
- Source: Acme decide call, 2026-07-27 (illustrative)
- Evidence: My call: we build quote drafting now, against the brief as written, and we review it on 15 November.

## D-0002: Quote drafts wait for the tradesperson's approval before they send

- Status: decided
- Decision: Every quote the assistant drafts waits for the tradesperson to approve it before it goes to the customer.
- Options considered:
  - Auto-send every draft
  - Approve before send
  - Auto-send under a value threshold
- Chosen: Approve before send
- Decided by: Head of Product, Quoting squad
- Date: 2026-07-27
- Owner: Quoting squad lead
- Review by: 2026-11-15
- Reversible: yes
- Success signal: Wrong-line-item complaints below 5 a month by 2026-11-15 (illustrative).
- Assumptions:
  - Most wrong line items are caught when the tradesperson reads the draft
- Opened: 2026-07-13
- Source: Acme decide call, 2026-07-27 (illustrative)
- Evidence: Decided: every drafted quote waits for the tradesperson to approve it before it sends.

## D-0003: Prices come from the price book, never the model

- Status: decided
- Decision: The model drafts the quote text only. Every price comes from the price book in fixed code.
- Options considered:
  - Prices from the price book
  - Model suggests prices
- Chosen: Prices from the price book
- Decided by: Quoting squad tech lead
- Date: 2026-07-27
- Owner: Quoting squad lead
- Review by: 2026-11-15
- Reversible: yes
- Success signal: No sent quote carries a price that differs from the price book, checked weekly to 2026-11-15 (illustrative).
- Opened: 2026-07-22
- Source: Acme decide call, 2026-07-27 (illustrative)
- Evidence: Prices come from the price book in fixed code. That is my call for v1.

## D-0004: Set the rollback trigger for quote drafting

- Status: open
- Decision: Which number rolls quote drafting back: wrong-price quotes over 2%, or rejected drafts over 30%?
- Options considered:
  - Roll back when wrong-price quotes pass 2%
  - Roll back when rejected drafts pass 30%
- Opened: 2026-07-13
- Waiting on: Quoting squad lead
- Decide by: 2026-08-03
- Recommendation: The Quoting squad product manager recommends the wrong-price trigger at 2%
- Source: Acme decide call, 2026-07-27 (illustrative)

## D-0005: Choose the model tier for quote drafts

- Status: open
- Decision: Which model drafts quotes in v1: vendor-a/xl, or vendor-a/m?
- Options considered:
  - vendor-a/xl
  - vendor-a/m
- Opened: 2026-07-20
- Waiting on: Quoting squad tech lead
- Decide by: 2026-08-03
- Recommendation: The Quoting squad lead recommends vendor-a/m, to stay inside the 9,000 token budget
- Source: Acme decide call, 2026-07-27 (illustrative)
