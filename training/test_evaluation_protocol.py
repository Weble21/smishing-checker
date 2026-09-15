import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ocr-service"))
from evaluation_protocol import near_duplicate_groups, assert_split_independence, mask_text, select_threshold, score_metrics, load_external


def test_names_numbers_and_urls_stay_in_one_group():
    texts = ["김철수 고객님 택배 123 https://one.example", "이영희 고객님 택배 456 https://two.example", "오늘 영화 보러 갈까요?"]
    groups = near_duplicate_groups(texts)
    assert groups[0] == groups[1] and groups[0] != groups[2]


def test_similar_but_not_identical_texts_are_grouped():
    common = "abcdefghijk" * 15
    groups = near_duplicate_groups([common + "a", common + "b"])
    assert groups[0] == groups[1]


def test_cross_split_duplicate_is_rejected():
    with pytest.raises(ValueError, match="crosses"):
        assert_split_independence({"train": pd.DataFrame({"text":["김철수 고객님 배송 완료"]}), "test":pd.DataFrame({"text":["이영희 고객님 배송 완료"]})})


def test_ablation_removes_url_features_and_is_deterministic():
    from smishing_api.message_context import domain_context
    masked = mask_text("[국민은행] 확인 https://evil.example/a", "url")
    assert "링크없음" in domain_context(masked)
    assert mask_text("a b c d e f", "shuffle") == mask_text("a b c d e f", "shuffle")
    assert mask_text("abc123", "digit") == "abc000"
    assert mask_text("x"*20+"keep", "prefix") == "keep"


def test_threshold_ties_obey_fpr_and_can_abstain():
    chosen = select_threshold([0,1],[1.,1.], max_fpr=0)
    assert chosen["abstain_all"] and chosen["validation"]["fp"] == 0
    chosen = select_threshold([0,0,1,1],[.2,.4,.4,.8],max_fpr=0)
    assert chosen["threshold"] == .8
    assert chosen["validation"]["risk_recall"] == .5


def test_threshold_requires_both_classes():
    with pytest.raises(ValueError): select_threshold([0,0],[.1,.2])


def test_hard_normal_only_reports_fpr_not_fake_auc():
    result=score_metrics([0,0],[.1,.8])
    assert result["normal_false_positive_rate"] == .5
    assert result["roc_auc"] is None and result["risk_recall"] is None


def test_external_missing_is_not_fake_success(tmp_path):
    assert load_external(tmp_path/"missing.csv", "hard") is None


def test_external_review_dates_and_labels(tmp_path):
    path=tmp_path/"external.csv"
    frame=pd.DataFrame([dict(id="one",text="예약 안내입니다",label=0,source="reviewed_collection",reviewed=True,collected_at="2026-09-01",category="reservation")])
    frame.to_csv(path,index=False)
    assert len(load_external(path,"hard"))==1
    with pytest.raises(ValueError,match="cutoff"):load_external(path,"temporal")
    with pytest.raises(ValueError,match="after"):load_external(path,"temporal","2026-09-02")
    assert len(load_external(path,"temporal","2026-08-01"))==1
    frame["label"]=frame["label"].astype(float);frame.loc[0,"label"]=.5;frame.to_csv(path,index=False)
    with pytest.raises(ValueError,match="labels"):load_external(path,"hard")


def test_conflicting_hard_negative_is_rejected():
    with pytest.raises(ValueError, match="Conflicting"):
        assert_split_independence({"train":pd.DataFrame({"text":["동일한 문장", "동일한 문장"], "label":[0,1]})})


def test_invalid_labels_cannot_silently_become_normal():
    with pytest.raises(ValueError, match="labels"):
        score_metrics([0,.5],[.1,.2])


def test_hard_validation_prevents_low_threshold_false_positives():
    result=select_threshold([0,0,1,1],[.001,.002,.9,.95],hard_probabilities=[.3,.4],hard_categories=["bank","subscription"])
    assert result["status"] == "selected"
    assert result["threshold"] > .4
    assert result["hard_validation"]["fp"] == 0


def test_impossible_constraints_do_not_silently_pass_all_normal():
    result=select_threshold([0,0,1,1],[.001,.002,.6,.7],hard_probabilities=[.99],min_recall=.95)
    assert result["status"] == "no_feasible_threshold"
    assert result["threshold"] is None


def test_public_source_cannot_cross_splits():
    with pytest.raises(ValueError,match="Source family"):
        assert_split_independence({"train":pd.DataFrame({"text":["가나다"],"source_family":["one"]}),"test":pd.DataFrame({"text":["라마바"],"source_family":["one"]})})
