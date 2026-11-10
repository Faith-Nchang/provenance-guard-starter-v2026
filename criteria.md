# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. False positives

In each of three trials, at most 1 of 10 pieces I wrote myself may receive
`guess: "ai"` (the high-confidence AI label). Use the same ten pieces in every
trial, including plain-language and formal writing.



**Why this target:**

An incorrect accusation can harm a real writer more than a missed AI submission
harms the site. A maximum of 10% is a concrete initial target for this small test
set, not evidence of a production-wide false-positive rate.


---

## 2. Label coverage

In each of three trials, a fixed set of 12 valid submissions must produce all
three guesses (`human`, `unsure`, and `ai`) at least once each. Every response
must include a non-placeholder, full-sentence label consistent with its guess
and the configured score thresholds.



**Why this target:**

Three labels are useful only if actual text can reach each one. Testing through
`/submit` catches a signal that stays constant or a combined score that cannot
reach a label, which checking threshold values alone would miss.


---

## 3. Score spread

In each of three trials, the mean combined `confidence` of 10 known AI-generated
passages must exceed the mean for the 10 human-written passages from criterion 1
by at least 0.20 on the 0-to-1 scale. Fix both sets before testing and match them
approximately by topic and length; every returned score must be finite and
between 0 and 1.



**Why this target:**

A 0.20 gap asks the combined signals to separate the groups meaningfully rather
than returning nearly the same score for everything. Matching topic and length
reduces obvious confounding, while the separate false-positive target protects
individual writers whom a group average could hide.


---

## 4. Appeal path

In each of three trials, submit five valid pieces, then appeal each returned
`content_id` with non-empty reasoning. All 5 appeals must return HTTP 200 and
`status: "under_review"`; each must append an audit entry containing the matching
ID, reasoning, and new status while preserving the original decision. An appeal
for an unknown ID must return HTTP 404 without creating an under-review item.



**Why this target:**

Every writer needs a reliable way to challenge a decision, so partial success
is not acceptable. Preserving the decision and recording the appeal makes the
case traceable for human review; rejecting unknown IDs prevents false confirmations.


---

## 5. Bad input

In each of three trials, all nine invalid `/submit` requests must return HTTP
400 with a JSON error code and readable message: missing `text`, empty `text`,
whitespace-only `text`, null `text`, numeric `text`, text of 10,001 characters,
missing `creator_id`, a JSON list instead of an object, and malformed JSON.
Set the intended text limit to 10,000 characters. None of these requests may
invoke either scoring signal, create a decision entry, or return HTTP 500.



**Why this target:**

Rejecting invalid input before scoring avoids crashes and unnecessary model
work. A 10,000-character limit bounds accepted input size, though it does not
remove the detector's separate 400-token truncation limit; rejection audit
entries may still be recorded without pretending a decision was made.


---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
