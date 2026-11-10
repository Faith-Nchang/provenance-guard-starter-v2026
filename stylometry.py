"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics

import config

TTR_WINDOW = 100  # words considered for type_token_ratio


def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────

def sentence_length_spread(text: str) -> float:
    """
    How much sentence length varies. ← TODO

    Returns:
        A float. Decide yourself what scale it's on and which direction means
        "more human" — then write that down, because your combining rule
        depends on knowing it.

    A hint on what you're reaching for: the standard deviation of sentence
    lengths, probably divided by the mean so a long text and a short one are
    comparable. `statistics.stdev` is imported for you.

    Watch the edge case: a one-sentence submission has no spread at all, and
    `stdev` raises on fewer than two values. Decide what that should return
    before the attack set decides for you.
    """
    lengths = [len(words(sent)) for sent in sentences(text)]
    lengths = [n for n in lengths if n > 0]
    # One sentence has no spread to measure. Return 0.0 ("no variation") and
    # let style_signal treat a lone sentence as uninformative instead of AI.
    if len(lengths) < 2:
        return 0.0
    # Coefficient of variation: stdev / mean. Higher means more human.
    return round(statistics.stdev(lengths) / statistics.mean(lengths), 4)


def type_token_ratio(text: str) -> float:
    """
    Unique words over total words. ← TODO

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    Worth knowing before you rely on it: this measure falls as text gets
    longer, because common words repeat. Two texts of different lengths aren't
    directly comparable on it, and if your test inputs vary a lot in length,
    that alone can look like a signal.
    """
    # Only the first TTR_WINDOW words count, so a long text isn't penalised
    # for repeating common words just by being long.
    tokens = words(text)[:TTR_WINDOW]
    if not tokens:
        return 0.0
    return round(len(set(tokens)) / len(tokens), 4)


def punctuation_density(text: str) -> float:
    """
    How much punctuation, relative to length. ← TODO

    Returns:
        A float. Whether you count all punctuation or only some kinds — commas,
        semicolons, dashes — is a real choice. Semicolons and em dashes are
        more interesting than full stops, because they vary more between
        writers.
    """
    n_words = len(words(text))
    if n_words == 0:
        return 0.0
    # Everything except the full stop that ends a sentence. Apostrophes are
    # part of words (words() keeps them), so they aren't counted here.
    marks = re.findall(r"[,;:!?()\"—–…-]", text)
    # Higher means more human. Variety of marks counts too: a text that only
    # ever uses commas is flatter than one that mixes commas, dashes and "?".
    return round(len(marks) / n_words + 0.01 * len(set(marks)), 4)


# ── Combining them ───────────────────────────────────────────────────────────

def style_signal(text: str) -> float:
    """
    The style signal as a 0–1 score. **Higher means more likely AI.** ← TODO

    Combine your three measures into one number. Same direction as
    `detector.model_signal`, so that `scoring.combine_signals` can treat them
    the same way — if one of your signals runs backwards, everything above it
    is wrong in a way that's hard to see.

    Two things to decide and write down:

      1. Which direction each measure points. Low spread means more AI-ish, so
         it needs flipping. Work out which of your three need that.
      2. How to get each onto a comparable scale. A raw type-token ratio sits
         between 0 and 1; a raw punctuation count doesn't. Adding them
         unscaled means whichever has the bigger numbers wins by default.

    Test it on the four calibration inputs from Milestone 4 — clearly AI,
    clearly human, plain conventional human writing, lightly-edited AI — before
    you trust it. Plain and ordinary, not formal: formal prose reads as *human*
    to signal one, and it is plain writing that gets accused.
    """
    if len(words(text)) < 2:
        return 0.5

    def clamp(x: float) -> float:
        return min(max(x, 0.0), 1.0)

    n_sentences = len(sentences(text))
    # Each measure becomes an "AI-ness" in 0-1 (higher = more AI-like):
    #   spread: CV 0.2 or less -> 1.0, CV 0.8 or more -> 0.0
    #   ttr:    0.50 or less   -> 1.0, 0.85 or more   -> 0.0
    #   punct:  0.00 -> 1.0,   0.20 or more per word  -> 0.0
    # A lone sentence has no spread, so that measure falls back to neutral.
    spread_ai = 0.5 if n_sentences < 2 else clamp(1 - (sentence_length_spread(text) - 0.2) / 0.6)
    ttr_ai = clamp((0.85 - type_token_ratio(text)) / 0.35)
    punct_ai = clamp(1 - punctuation_density(text) / 0.20)

    score = (
        config.STYLE_WEIGHT_SPREAD * spread_ai
        + config.STYLE_WEIGHT_TTR * ttr_ai
        + config.STYLE_WEIGHT_PUNCT * punct_ai
    )
    return round(clamp(score), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
    print("\nAll zeros? These are stubs — Milestone 4 is where you build them.")
