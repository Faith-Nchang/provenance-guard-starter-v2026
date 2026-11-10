# Design notes: Milestone 1 trace

Written before any code. Draft for me to edit; the README sections come from this.

## 1. The path a submission takes

1. **Client** sends `POST /submit` with `{"text", "creator_id"}`.
2. **Validation** (`app.py::submit`) rejects missing, non-string, empty, or oversized (over 10,000 characters) `text` and a missing `creator_id` with a 400 and a JSON error. Nothing is scored or logged as a decision.
3. **Signal one** (`detector.model_signal`) runs the local GPT-2 model and adds `model_score` (0 = human-like, 1 = AI-like).
4. **Signal two** (`stylometry.style_signal`) measures the text's shape and adds `style_score` (same scale).
5. **Combining** (`scoring.combine_signals`) turns both into one `confidence` (0 to 1) and a `guess` (`ai` / `human` / `unsure`).
6. **Labeling** (`scoring.score_to_label`) maps the score to one of three full-sentence labels.
7. **Audit** (`audit.log_decision`) writes timestamp, `content_id`, `creator_id`, guess, `model_score`, `style_score`, `confidence`, and status `decided` to `logs/audit.jsonl`. The response returns `content_id`, `guess`, `confidence`, `label`, `model_score`, `style_score`.

Appeal path: `POST /appeal` looks up `content_id` in the log, calls `audit.log_appeal`, status becomes `under_review`, and the writer gets a confirmation.

## 2. The two signals

| | Signal one: model (`detector.py`) | Signal two: style (`stylometry.py`) |
|---|---|---|
| **Measures** | How predictable the text is to GPT-2 (perplexity) | Sentence-length spread, type-token ratio, punctuation density |
| **Why it might differ** | Generated text is made of likely next words, so models find it easy to predict. Humans make surprising choices. | AI prose tends toward even, mid-length sentences and a narrower vocabulary. Human writing is lumpier. |
| **Blind spots** | Formal, clichéd or heavily edited human writing is also predictable (false positives). Lightly paraphrased AI text becomes less predictable (misses). It can't tell who wrote it, only how likely the words are. Short text gives a noisy reading. It scores only the first ~400 tokens. | It can't read, so it can't tell meaning from shape. Typos, chopped sentences or pasted quotes shift it cheaply. Short texts have too few sentences for a spread. Poetry and lists break the sentence splitter. Careful formal human writing looks "even." |

## 3. The false positive, traced

A real writer submits a formal essay they wrote.
- **Score:** GPT-2 finds it predictable (`model_score` ~0.8) and the sentences are even (`style_score` ~0.7). The combined `confidence` is about 0.75, above `AI_THRESHOLD`, so the guess is `ai`.
- **What the label says:** the high-confidence-AI label. It must therefore be worded as a finding the system could be wrong about, not an accusation.
- **What they can do:** `POST /appeal` with their reasoning. The item moves to `under_review` and the appeal is logged next to the original decision. Nothing re-checks it automatically, so a person has to look.
- **Consequence for design:** the AI threshold sits high, so the wide "unsure" band absorbs formal human writing. The AI label should be hard to reach.

## 4. Endpoint contracts

### `POST /submit`

Request:
```json
{"text": "string, required, non-empty, max 10,000 chars", "creator_id": "string, required, non-empty"}
```
200 response:
```json
{
  "content_id": "string (uuid), use it for /appeal",
  "guess": "ai | human | unsure",
  "confidence": "float 0-1, higher = more likely AI",
  "label": "string, the full sentence shown to the reader",
  "model_score": "float 0-1",
  "style_score": "float 0-1"
}
```
400 response (bad input): `{"error": "<code>", "message": "<human-readable>"}`. Codes: `missing_text`, `empty_text`, `text_too_long`, `missing_creator_id`, `invalid_json`.

### `POST /appeal`

Request:
```json
{"content_id": "string, required, must exist in the log", "reasoning": "string, required, non-empty"}
```
200 response:
```json
{"content_id": "string", "status": "under_review", "message": "string confirming it was recorded"}
```
Errors: 400 for missing fields, 404 `unknown_content_id` if the id isn't in the log.

### Open decisions for me
- Whether `guess` is `unsure` or the nearer side when in the middle band.
