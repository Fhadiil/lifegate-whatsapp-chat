# Example EDIS logic for demonstration
TIER_QUESTIONS = {
    1: ["What symptoms are you currently experiencing?"],
    2: ["When did these symptoms start?", "Have you taken any medication recently?"],
    3: ["Do you have a history of chronic illness?", "Any recent changes in sleep or appetite?"],
    4: ["Gender?", "Age?"]
}

def get_next_question(session):
    """
    Returns the next question based on current tier
    """
    tier = session.current_tier
    if tier > 4:
        return None  # All tiers completed

    questions = TIER_QUESTIONS[tier]
    # Find unanswered question
    collected = session.symptoms_collected.get(str(tier), [])
    if len(collected) < len(questions):
        return questions[len(collected)]
    else:
        # Move to next tier
        session.current_tier += 1
        session.save()
        return get_next_question(session)

def save_answer(session, answer):
    tier = session.current_tier
    if str(tier) not in session.symptoms_collected:
        session.symptoms_collected[str(tier)] = []
    session.symptoms_collected[str(tier)].append(answer)
    session.save()
