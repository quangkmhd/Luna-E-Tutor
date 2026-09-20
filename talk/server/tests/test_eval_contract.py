from pathlib import Path

import yaml


def test_eval_metadata_and_scenarios_cover_free_talk_contract():
    root = Path(__file__).resolve().parents[1]
    body = yaml.safe_load(root.joinpath("evals/runner-body.yaml").read_text())
    text = yaml.safe_load(root.joinpath("evals/starter_text.yaml").read_text())
    assert body == {"topic": "Animals"}
    scenario = text["scenarios"][0]
    assert scenario["name"] == "free_talk_conversation"
    utterances = [turn.get("user") for turn in scenario["turns"] if "user" in turn]
    assert utterances == [
        "I like dogs.",
        "Em chưa hiểu từ loyal.",
        "Can we talk about school instead?",
    ]
    assert all(turn["expect"] == [{"event": "response"}] for turn in scenario["turns"])
