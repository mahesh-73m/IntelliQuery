"""Answers clarification questions from the dataset's ground truth (what a real user would pick)."""


def answer(item: dict, candidate_id: str, option_ids: list[str]) -> tuple[str, bool]:
    """Returns (option_id, matched_ground_truth). Questions the dataset has no intent for
    (e.g. LLM-invented ones) are answered with the first option and flagged as unmatched."""
    if item.get("term_id") == candidate_id and item.get("intended_option") in option_ids:
        return item["intended_option"], True
    return option_ids[0], False
