# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

1. **Request.** A client sends `POST /submit` with `{"text", "creator_id"}`.
2. **Validation** (`app.py::submit`). Missing, empty, non-string or oversized (over 10,000 characters) `text`, a missing `creator_id`, or a body that isn't a JSON object gets a 400 with an error code. It is logged as a rejection, and neither signal runs.
3. **Signal one** (`detector.model_signal`). A local GPT-2 model measures how predictable the text is and adds `model_score`.
4. **Signal two** (`stylometry.style_signal`). It measures the text's shape (sentence-length spread, vocabulary variety, punctuation) and adds `style_score`.
5. **Combining** (`scoring.combine_signals`). Both scores become one `confidence` between 0 (human) and 1 (AI).
6. **Labeling** (`scoring.score_to_label`). The confidence maps to one of three labels. *(Not built yet: the response currently carries a placeholder label.)*
7. **Audit and response.** The decision is written to `logs/audit.jsonl` with a `content_id`, both signal scores and the combined score. The response returns the `content_id`, guess, confidence, label and both signal scores. A writer who disagrees can call `POST /appeal` with that `content_id`.



---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:** How predictable the text is to a local GPT-2 model, as perplexity squashed onto 0 to 1 (`detector.py::model_signal`). Higher means more AI-like.

**Why that might differ between human and AI writing:** A language model writes by picking likely next words, so its output is easy for another model to predict. Human writers make odd, specific choices that surprise it.

**What it can't see:** Authorship. It only sees how likely the words are. Plain, common-word human writing (a younger writer, someone writing in a second language, anyone writing simply) scores as machine-like, while ornate prose full of rare words scores as human. Lightly paraphrased AI text becomes less predictable and slips through. Only the first ~400 tokens are scored, and very short text gives a noisy reading. In my own run, a plain human paragraph about a trip to the market scored 0.759, close to the 0.809 of clearly-AI text.

### Signal two — the style signal

**What it measures:** The shape of the text, with no understanding of it (`stylometry.py::style_signal`). Three measures, each scaled to an "AI-ness" from 0 to 1 and combined with weights 0.5 / 0.3 / 0.2:
- sentence-length spread (stdev divided by mean): low spread is AI-like
- type-token ratio over the first 100 words: low vocabulary variety is AI-like
- punctuation density (all marks except the sentence-ending full stop, plus a small bonus for variety of marks): sparse, uniform punctuation is AI-like

**Why that might differ between human and AI writing:** Generated prose tends toward even, mid-length sentences and a narrower vocabulary. Human writing is lumpier: a three-word sentence next to a forty-word one, with dashes, question marks and asides.

**What it can't see:** Meaning. Anything that changes the shape without changing the substance moves it: adding typos, chopping sentences, pasting in a quotation. Short or one-sentence texts have almost no spread to measure (a lone sentence is scored as neutral on that measure). Poetry and lists confuse the sentence splitter, and careful, even-toned human writing can look "AI-like". In my run the plain human paragraph scored 0.603 here, partly because its sentences were similar in length.

### The combining rule

**The rule:** A weighted average of the two scores, favouring the model signal. If the two signals are far apart, the average is pulled halfway toward 0.5, because two methods disagreeing is uncertainty and I would rather return "unsure" than accuse a writer on one signal's word. A wrong accusation costs a writer more than a missed detection costs the site.

**The numbers** (all in `config.py`):
- `WEIGHT_MODEL_SIGNAL = 0.6`, `WEIGHT_STYLE_SIGNAL = 0.4`
- `DISAGREEMENT_GAP = 0.4`: signals at least this far apart count as disagreeing
- `DISAGREEMENT_PULL = 0.5`: on disagreement, the average moves this fraction of the way to 0.5
- Inside the style signal: `STYLE_WEIGHT_SPREAD = 0.5`, `STYLE_WEIGHT_TTR = 0.3`, `STYLE_WEIGHT_PUNCT = 0.2`
- Label thresholds: `HUMAN_THRESHOLD = 0.35`, `AI_THRESHOLD = 0.65`

**Where it lives:** `scoring.py::combine_signals`

**Calibration run** (`model_score`, `style_score`, combined):

| Input | model | style | combined |
|---|---|---|---|
| Clearly AI | 0.809 | 0.526 | 0.696 |
| Clearly human | 0.104 | 0.063 | 0.088 |
| Formal human | 0.334 | 0.321 | 0.329 |
| Lightly edited AI | 0.672 | 0.456 | 0.585 |
| Plain human | 0.759 | 0.603 | 0.697 |

**A case where my two signals split, and what my rule does with it:** Lightly edited AI ("Honestly, communication matters a lot in relationships…") scored 0.672 on the model signal and 0.456 on the style signal, a gap of 0.21. That is below the 0.4 gap, so the plain weighted average applies and the combined score is 0.585, in the "unsure" band. The rule's pull toward 0.5 did not trigger on any of my five inputs, so it is untested. The clearest failure is the other direction: the plain human paragraph scored 0.697, above the 0.65 AI threshold, because both signals agreed and the rule has nothing to correct. I did not tune it away. It is the false-positive case my appeal path exists for.


---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | We think this was probably written by a person. |
| unsure | 0.35 – 0.65 | We can't tell whether this was written by a person or with the help of AI. That doesn't mean anything is wrong, and nothing has been decided against you. |
| high-confidence AI | 0.65 – 1.00 | Our automated check thinks this may have been written with AI. It can be wrong, especially with plain or formal writing. If you wrote it yourself, tell us and a person will take a look. |

A score of exactly 0.35 or below is "human", and 0.65 or above is "AI"; every score in between is "unsure", so there is no gap. All three were reached through `/submit` (scores 0.097, 0.522 and 0.696).

**Why I worded the "unsure" one this way:**
<!-- It's the hardest of the three. It has to admit uncertainty without
     sounding like an accusation, because the person reading it may well have
     written every word themselves. -->

It says "we can't tell" instead of hinting at a verdict, and it adds that nothing has been decided against the writer, because the person reading it may well have written every word themselves. It states no number, since "0.52" would mean nothing to a writer. The AI label says it "may" have been written with AI, admits it can be wrong, and tells the writer what to do next.




---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->

**A submission**

```bash
$ curl -X POST http://127.0.0.1:5000/submit   -H "Content-Type: application/json"   -d '{"text": "ok so my dog ate my homework again, third time this week, and honestly? mom just laughed. we are all doomed. Anyway, I stayed up till 2 finishing it (again!) and now I am wrecked; coffee helps, barely.", "creator_id": "w1"}'
```

```json
{"confidence": 0.0972, "content_id": "e17f4933-16f8-4299-b0e4-36dabd446154", "guess": "human", "label": "We think this was probably written by a person.", "model_score": 0.1296, "style_score": 0.0485}
```

**An appeal**

```bash
$ curl -X POST http://127.0.0.1:5000/appeal   -H "Content-Type: application/json"   -d '{"content_id": "e17f4933-16f8-4299-b0e4-36dabd446154", "reasoning": "I wrote this myself about my dog."}'
```

```json
{"content_id": "e17f4933-16f8-4299-b0e4-36dabd446154", "message": "Thanks. Your appeal has been recorded and this item is now under review.", "status": "under_review"}
```

An appeal for an id that doesn't exist, and one with no reasoning:

```json
{"error": "unknown_content_id", "message": "No submission found with content_id 'nope'."}
{"error": "missing_reasoning", "message": "'reasoning' is required: tell us why you think this is wrong."}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=2"
```

```json
{"count": 2, "entries": [
  {"combined_score": 0.0972, "content_id": "e17f4933-16f8-4299-b0e4-36dabd446154", "creator_id": "w1", "guess": "human", "label": "We think this was probably written by a person.", "model_score": 0.1296, "status": "decided", "style_score": 0.0485, "timestamp": "2026-11-10T21:21:26+00:00"},
  {"content_id": "e17f4933-16f8-4299-b0e4-36dabd446154", "creator_id": "w1", "event": "appeal", "reasoning": "I wrote this myself about my dog.", "status": "under_review", "timestamp": "2026-11-10T21:21:26+00:00"}
]}
```

The original decision stays in the log unchanged; the appeal is appended after it.

---

## How I Used AI

**Moment 1: the design trace and the criteria**

- *What I asked for:* I asked Claude Code to break the project into five phases and then to implement Phase 1, the Milestone 1 trace. I told it up front that the five acceptance criteria had to be mine, so I wrote `criteria.md` myself and asked it only to check whether the work was complete.
- *What came back:* `DESIGN.md`: the seven-step path, both signals with their blind spots, the false-positive trace and the field-by-field `/submit` and `/appeal` contracts. It left max text length as an open decision. When it checked `criteria.md` it noticed that my criterion 5 set a 10,000-character limit that the design notes didn't mention.
- *What I changed:* I had it update `DESIGN.md` so both documents say 10,000 characters, and I committed the design and criteria together before building anything.

**Moment 2: the style signal and the combining rule**

- *What I asked for:* I asked Claude Code to implement  `stylometry.py`, `scoring.py::combine_signals`, and wiring both into `/submit`, then to run it on clearly-AI, clearly-human, formal-human and lightly-edited-AI inputs.
- *What came back:* A style signal built from sentence-length spread, type-token ratio and punctuation density, plus a 0.6/0.4 weighted average that pulls toward 0.5 when the signals differ by 0.4 or more. The calibration run separated AI from human (0.696 vs 0.088), but a plain human paragraph scored 0.697 on both signals.
- *What I changed:* I decided not to tune the weights to make that false positive disappear. It is documented in Signals and Scoring as a real blind spot. I also noticed the disagreement rule never triggered on any of my inputs, so I describe it as untested instead of claiming it works.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** 10 per minute, 200 per day

**Why those numbers and not others:**
A real writer submits a piece, reads the label, maybe edits and resubmits. That is a handful of submissions an hour, so 10 a minute never gets in their way, even when they paste several drafts in a row. A script mapping my thresholds needs hundreds or thousands of variations. At 10 a minute it manages 600 an hour, and the 200/day cap stops it after about 20 minutes of sustained sending and keeps it stopped until the window resets. The daily cap does the real work against threshold-mapping; the per-minute cap mostly stops bursts, and it protects the service because each submission runs GPT-2 inline and takes a second or two. I did not go lower because a false 429 on a real writer is a wrong accusation of a different kind.

**What a caller counts as:** the `creator_id` in the request body, falling back to the caller's IP address when `creator_id` is missing or not a string (`rate_limit_key` in `app.py`). One script using a different `creator_id` per request would get a fresh quota each time, so this limit is weak against that. The IP fallback only catches requests with no usable `creator_id`.

**The run of status codes when I pushed past it:**

`python run_attacks.py --flood 15` (full report in `results/flood_2026-11-10_1922.md`)

```
200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

The five rejections appear in `logs/audit.jsonl` as `event: rejected, reason: rate_limited, limit: "10 per 1 minute"`.

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. My own writing flagged as AI | ≤ 1 of 10 get `guess: "ai"` | 0/10 | 0/10 | 0/10 | MET |
| 2. All three labels reachable | `human`, `unsure`, `ai` each appear in 12 submissions | 3/3 (8 ai, 2 unsure, 2 human) | 3/3 (same) | 3/3 (same) | MET |
| 3. Score spread | mean(AI) − mean(human) ≥ 0.20 | 0.3095 (0.7047 vs 0.3952) | 0.3095 | 0.3095 | MET |
| 4. Appeal path | 5 of 5 appeals return 200 + `under_review`, logged, original preserved; unknown ID returns 404 and creates nothing | 5/5, unknown ID 404 | 5/5, unknown ID 404 | 5/5, unknown ID 404 | MET |
| 5. Bad input | 9 of 9 invalid requests return 400 with JSON error + message; no decision entry; no 500 | 9/9, 0 decision entries | 9/9, 0 decision entries | 9/9, 0 decision entries | MET |

Criteria 1-3 come from `run_eval.py::main` (`results/run_2026-11-10_1937_before.md`). All three trials were identical for every input, as expected, since neither signal is random.

**Caveats on the MET verdicts (not diagnoses of misses):**
- My ten pieces are one sentence each (about 10-20 tokens), while the AI passages are 3-4 sentences. Criterion 3 says to match length approximately, and I did not. A 0.31 gap might partly be length rather than authorship, and the detector reads short text less steadily. I'm not changing the sets after seeing results.
- Criterion 1 is met by a thin margin of safety. Six of my ten pieces landed in `unsure`, and two scored close to the 0.65 AI line (0.609 and 0.583). For the 0.583 piece the model signal alone was 0.895, so it was the style signal and the combining rule that kept it out of `ai`. A threshold or style change could flip it.
- Criterion 2 is met, but the "in-between" texts I wrote (a budget meeting, photosynthesis, a movie review, a team update) mostly landed as `ai` (3 of 4). Formal plain prose scores as AI-like, which is a false-positive risk for formal human writers that criterion 1's set does not cover.

Criteria 4 and 5 come from `run_hand_criteria.py::main` (`results/hand_criteria_2026-11-10_1927_before.md`). How I decided MET: every trial passed every check, so the target held in all three. Caveat on 5: "neither scoring signal runs" is inferred, not observed. Rejected responses carry no `model_score` or `style_score` and no decision entry is written. I did not instrument the signals to prove they were never called.

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
