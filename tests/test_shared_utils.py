"""Tests for shared_utils module."""
import sys
sys.path.insert(0, "notebooks")
import shared_utils as utils


def test_load_jsonl():
    data = utils.load_jsonl("data/final/train.jsonl")
    assert len(data) > 0
    assert "input_text" in data[0]


def test_make_target_json():
    example = {
        "input_text": "test",
        "safe": True,
        "severity": "S0",
        "triggered_principles": [],
        "risk_labels": [],
        "reason": "safe",
        "rewrite_required": False,
        "suggested_rewrite": "",
    }
    result = utils.make_target_json(example)
    import json
    parsed = json.loads(result)
    assert parsed["safe"] is True
    assert parsed["severity"] == "S0"


def test_format_gemma():
    example = {
        "input_text": "Hello Malaysia",
        "safe": True,
        "severity": "S0",
        "triggered_principles": [],
        "risk_labels": [],
        "reason": "greeting",
        "rewrite_required": False,
        "suggested_rewrite": "",
    }
    result = utils.format_gemma(example)
    assert "<start_of_turn>user" in result
    assert "<start_of_turn>model" in result
    assert "<end_of_turn>" in result
    assert "Hello Malaysia" in result


def test_format_lfm2():
    example = {
        "input_text": "Hello Malaysia",
        "safe": True,
        "severity": "S0",
        "triggered_principles": [],
        "risk_labels": [],
        "reason": "greeting",
        "rewrite_required": False,
        "suggested_rewrite": "",
    }
    result = utils.format_lfm2(example)
    assert "<|im_start|>user" in result
    assert "<|im_start|>assistant" in result
    assert "<|im_end|>" in result


def test_inference_prompt_gemma():
    result = utils.inference_prompt_gemma("test input")
    assert result.endswith("<start_of_turn>model\n")
    assert "test input" in result


def test_inference_prompt_lfm2():
    result = utils.inference_prompt_lfm2("test input")
    assert result.endswith("<|im_start|>assistant\n")
    assert "test input" in result


def test_parse_model_output_valid():
    raw = '{"safe": true, "severity": "S0"}<end_of_turn>'
    result = utils.parse_model_output(raw)
    assert result is not None
    assert result["safe"] is True


def test_parse_model_output_invalid():
    result = utils.parse_model_output("not json at all")
    assert result is None


def test_parse_model_output_embedded():
    raw = 'Some text {"safe": false, "severity": "S1"} more text'
    result = utils.parse_model_output(raw)
    assert result is not None
    assert result["severity"] == "S1"


def test_safe_accuracy():
    preds = [{"safe": True}, {"safe": False}, {"safe": True}]
    golds = [{"safe": True}, {"safe": False}, {"safe": False}]
    assert utils.safe_accuracy(preds, golds) == 2 / 3


def test_severity_accuracy():
    preds = [{"severity": "S0"}, {"severity": "S1"}, {"severity": "S2"}]
    golds = [{"severity": "S0"}, {"severity": "S2"}, {"severity": "S2"}]
    assert utils.severity_accuracy(preds, golds) == 2 / 3


def test_severity_within_one():
    preds = [{"severity": "S0"}, {"severity": "S1"}, {"severity": "S3"}]
    golds = [{"severity": "S0"}, {"severity": "S2"}, {"severity": "S1"}]
    # S0==S0 ✓, |S1-S2|=1 ✓, |S3-S1|=2 ✗
    assert utils.severity_within_one(preds, golds) == 2 / 3


def test_multilabel_f1():
    preds = [{"labels": ["a", "b"]}, {"labels": ["a"]}]
    golds = [{"labels": ["a", "c"]}, {"labels": ["a", "b"]}]
    # tp=2(a,a), fp=1(b), fn=2(c,b) -> p=2/3, r=2/4=0.5 -> f1=2*(2/3*0.5)/(2/3+0.5)
    f1 = utils.multilabel_f1(preds, golds, "labels")
    assert 0.56 < f1 < 0.58


def test_valid_json_rate():
    outputs = [{"a": 1}, None, {"b": 2}, None, {"c": 3}]
    assert utils.valid_json_rate(outputs) == 3 / 5


def test_compute_all_metrics():
    preds = [{"safe": True, "severity": "S0", "triggered_principles": [], "risk_labels": []}]
    golds = [{"safe": True, "severity": "S0", "triggered_principles": [], "risk_labels": []}]
    raw = [{"safe": True}]
    metrics = utils.compute_all_metrics(preds, golds, raw)
    assert metrics["safe_accuracy"] == 1.0
    assert metrics["severity_accuracy"] == 1.0
    assert metrics["valid_json_rate"] == 1.0
