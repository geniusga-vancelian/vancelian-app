from services.finance_strategy_chat.extraction import extract_patch
from services.finance_strategy_chat.schemas import ClientProfile, LastQuestion


def test_extract_patch_reroutes_monthly_when_text_mentions_per_month():
    profile = ClientProfile()
    last_question = LastQuestion(
        text="Tu peux mettre une somme au départ ?",
        expected_fields=["initial_contribution_amount"],
    )
    patch = extract_patch(profile, last_question, "100€/mois")
    assert patch.updates[0].path == "goal.monthly_contribution_amount"
    assert patch.updates[0].value == 100.0
