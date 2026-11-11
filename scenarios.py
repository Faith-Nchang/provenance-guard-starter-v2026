"""
What my test runs (unit 8, Milestone 3). `run_eval.py` runs everything here
three times.

Criteria (see criteria.md):
  1. False positives    - 10 pieces I wrote myself      -> here, loaded from my_writing.txt
  2. Label coverage     - 12 valid submissions          -> here
  3. Score spread       - 10 AI passages vs my 10       -> here (the human set is criterion 1's)
  4. Appeal path        - needs submit THEN appeal      -> NOT here, see run_hand_criteria.py
  5. Bad input          - 9 invalid requests            -> NOT here, see run_hand_criteria.py
                          (malformed JSON and a JSON list can't be expressed as
                          a dict body, so run_eval.py can't send them)

my_writing.txt holds my ten pieces, separated by a line containing only `---`.
They must be things I actually wrote. The placeholder check below refuses to run
until they are real.
"""

from pathlib import Path

_WRITING_FILE = Path(__file__).parent / "my_writing.txt"


def _load_my_writing() -> list[str]:
    if not _WRITING_FILE.exists():
        return ["REPLACE ME: my_writing.txt is missing."]
    raw = _WRITING_FILE.read_text(encoding="utf-8")
    pieces = [p.strip() for p in raw.split("\n---\n")]
    # Lines starting with '#' are instructions in the template, not writing.
    pieces = ["\n".join(l for l in p.splitlines() if not l.startswith("#")).strip()
              for p in pieces]
    return [p for p in pieces if p] or ["REPLACE ME: my_writing.txt has no pieces."]


MY_WRITING = _load_my_writing()

# Ten passages written in the register of a typical chatbot answer: even
# sentence lengths, stock transitions, no particulars. Fixed before testing.
# Topics are generic on purpose; swap any so they line up with MY_WRITING's
# topics before the "before" run (criterion 3 says match by topic and length),
# and do NOT edit them after seeing results.
AI_PASSAGES = [
    "Remote work has transformed the modern workplace in significant ways. It offers employees greater flexibility, reduces commuting time, and can improve work-life balance. However, it also presents challenges such as isolation, communication barriers, and difficulty separating professional and personal life. Organizations that adopt clear communication practices and set realistic expectations are more likely to succeed in a remote environment.",
    "Sleep is essential for both physical and mental health. Adults generally need between seven and nine hours of sleep each night to function at their best. Consistent sleep schedules, limited screen time before bed, and a comfortable environment can all contribute to better rest. Prioritizing sleep is one of the most effective ways to improve overall well-being and productivity.",
    "Public libraries play a vital role in communities around the world. They provide free access to books, digital resources, and educational programs for people of all ages. Libraries also serve as safe gathering spaces that foster learning and connection. In an increasingly digital age, their importance continues to grow as they bridge the gap between information and access.",
    "Cooking at home offers numerous benefits for health and finances. By preparing meals from fresh ingredients, individuals can control portion sizes and avoid excessive sodium and sugar. Home cooking is also typically more affordable than dining out. Additionally, it provides an opportunity to share meals with family and develop valuable culinary skills over time.",
    "Climate change is one of the most pressing challenges facing humanity today. Rising global temperatures contribute to extreme weather events, sea level rise, and disruptions to ecosystems. Addressing this issue requires coordinated action from governments, businesses, and individuals. By adopting renewable energy and sustainable practices, society can reduce its environmental impact and build a more resilient future.",
    "Learning a second language is a rewarding endeavor with many cognitive and social advantages. Research suggests that bilingual individuals often demonstrate improved memory and problem-solving abilities. Furthermore, speaking another language opens doors to new cultures and career opportunities. Consistent practice, exposure, and patience are key factors in achieving fluency.",
    "Regular exercise is a cornerstone of a healthy lifestyle. Physical activity strengthens the cardiovascular system, builds muscle, and boosts mood through the release of endorphins. Experts recommend at least one hundred fifty minutes of moderate activity per week. Finding an enjoyable form of exercise makes it easier to maintain a consistent routine over the long term.",
    "Social media has changed the way people communicate and share information. It enables instant connection across great distances and gives individuals a platform to express their ideas. At the same time, it raises concerns about privacy, misinformation, and mental health. Using these platforms mindfully can help users enjoy the benefits while minimizing potential drawbacks.",
    "Urban green spaces provide important benefits to city residents. Parks and community gardens improve air quality, reduce heat, and offer places for recreation and relaxation. Studies have shown that access to nature can lower stress and improve mental well-being. City planners should therefore prioritize the creation and maintenance of green spaces as part of sustainable urban development.",
    "Effective time management is a skill that can significantly enhance productivity and reduce stress. Setting clear priorities, breaking large tasks into smaller steps, and minimizing distractions are widely recommended strategies. Tools such as calendars and to-do lists can provide helpful structure. With consistent effort, anyone can develop habits that make their time more productive.",
]

# Twelve valid submissions across the range, fixed before testing. Four I expect
# to read as AI-like, four human-like, four in between. These are my
# expectations, not labels the test checks; criterion 2 only asks that all three
# guesses appear at least once per trial.
COVERAGE_TEXTS = [
    # expected AI-like
    AI_PASSAGES[0],
    AI_PASSAGES[4],
    "In conclusion, it is important to note that artificial intelligence is a transformative technology that offers numerous benefits across a wide range of industries. By leveraging advanced algorithms, organizations can streamline processes, enhance decision-making, and drive innovation. As technology continues to evolve, it is essential to consider the ethical implications and ensure responsible development.",
    "Overall, there are several key factors to consider when choosing a career path. First, it is important to assess your interests and strengths. Second, researching industry trends can provide valuable insight into future opportunities. Finally, seeking mentorship and gaining practical experience can help you make an informed decision that aligns with your goals.",
    # expected human-like
    "Dad burned the toast again, third time this week, and Mum just laughed and opened the window. The smoke alarm went off anyway. Our dog, who's afraid of exactly one thing in this world, hid under the table until it stopped.",
    "ok so the bus was late AGAIN and I'm standing there in the rain with one earbud because the other one died on tuesday, and this guy next to me starts telling me about his cousin's goat. Honestly? Best part of my day.",
    "My grandmother never measured anything. A fistful of flour, a splash of whatever was open, and somehow it came out the same every Sunday. I tried writing her recipe down once. She watched me, shook her head, and said I was doing it wrong.",
    "Nobody told me that moving cities means losing the small stuff first: the guy at the corner shop who knew my order, the crack in the pavement I always stepped over. The big things you plan for. It's the pavement that gets you.",
    # expected in between
    "The committee met on Tuesday to review the proposed budget. Several members raised concerns about the allocation for facilities maintenance, noting that costs had risen sharply. After some discussion, it was agreed that a revised proposal would be circulated before the next meeting.",
    "Photosynthesis is the process by which plants convert light energy into chemical energy. Chlorophyll in the leaves absorbs sunlight, which drives the conversion of carbon dioxide and water into glucose and oxygen. This process is fundamental to life on Earth.",
    "I think the movie was good, though it dragged in the middle. The acting was strong and the ending surprised me, but a few scenes felt unnecessary. I would recommend it, with the caveat that you should be prepared for a long evening.",
    "Our team has been working on the new onboarding flow for about six weeks. We shipped the first version last Friday, and early feedback is mostly positive. There are a few rough edges around the password reset step that we plan to address next sprint.",
]

SCENARIOS = [
    {
        "name": "my own writing",
        "criterion": 1,
        "texts": MY_WRITING,
    },
    {
        "name": "label coverage",
        "criterion": 2,
        "texts": COVERAGE_TEXTS,
    },
    {
        "name": "score spread AI set",
        "criterion": 3,
        # Compared against the "my own writing" results from the same trial.
        "texts": AI_PASSAGES,
    },
    # Criteria 4 and 5: run_hand_criteria.py
]


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(f"scenario {i}, body {j} is not a dict")
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(f"scenario {i}, text {j} is empty")
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder — fill in my_writing.txt"
                )

        if scenario.get("criterion") == 1 and len(texts) != 10:
            problems.append(
                f"criterion 1 is defined on 10 pieces; my_writing.txt has {len(texts)}"
            )
    return problems
