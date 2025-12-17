# whatsapp/edis.py
TIER_QUESTIONS = {
    1: ["What symptoms are you currently experiencing?"],
    2: ["When did these symptoms start?", "Have you taken any medication recently?"],
    3: ["Do you have a history of chronic illness?", "Any recent changes in sleep or appetite?"],
    4: ["Gender?", "Age?"]
}

def get_next_question(session):
    """
    Returns the next question based on current tier stored in session.current_tier.
    """
    tier = session.current_tier
    if tier > max(TIER_QUESTIONS.keys()):
        return None  # All tiers completed

    questions = TIER_QUESTIONS.get(tier, [])
    collected = session.symptoms_collected.get(str(tier), [])
    if len(collected) < len(questions):
        return questions[len(collected)]
    else:
        session.current_tier += 1
        session.save()
        return get_next_question(session)

def save_answer(session, answer):
    tier = session.current_tier
    key = str(tier)
    if key not in session.symptoms_collected:
        session.symptoms_collected[key] = []
    session.symptoms_collected[key].append(answer)
    session.save()
