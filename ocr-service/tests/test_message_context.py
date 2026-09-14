from smishing_api.message_context import domain_context, encode_message


def test_same_bank_message_distinguishes_host_boundaries():
    body = "[국민은행] 안내 내용을 확인하세요. "
    assert "기관일치" in domain_context(body + "https://www.kbstar.com/")
    for link in ("https://kbstar.com.evil.example/", "https://kbstar.com@evil.example/",
                 "https://evil.example/kbstar.com"):
        assert "공식목록미확인" in domain_context(body + link)
        assert "기관일치" not in domain_context(body + link)


def test_other_official_brand_is_not_a_match():
    assert "다른기관도메인" in domain_context("[국민은행] 인증 https://www.shinhan.com/")


def test_url_path_does_not_invent_mentioned_brand():
    context = domain_context("안내입니다. https://www.kbstar.com/국민은행")
    assert "언급기관=미확인" in context
    assert "기관일치" not in context


def test_existing_app_without_url():
    assert "링크없음" in domain_context("[국민은행] 기존 앱을 직접 열어 확인해주세요.")


def test_unlisted_domain_is_not_claimed_malicious():
    context = domain_context("공지 https://unlisted.example")
    assert "공식목록미확인" in context
    assert "악성" not in context


def test_all_links_contribute_relationships():
    context = domain_context("[국민은행] https://kbstar.com https://other.example")
    assert "기관일치" in context and "공식목록미확인" in context


def test_encoding_reserves_context_budget_for_long_messages():
    class Tokenizer:
        def __call__(self, value, **kwargs):
            return {"input_ids": list(range(len(value)))}
        def num_special_tokens_to_add(self, pair):
            return 3
        def prepare_for_model(self, ids, pair_ids, **kwargs):
            return {"input_ids": ids, "pair_ids": pair_ids}
    encoded = encode_message(Tokenizer(), "[국민은행] " + "긴 안내문 " * 1000 + " https://evil.example")
    assert 0 < len(encoded["input_ids"]) <= 96
    assert len(encoded["input_ids"]) + len(encoded["pair_ids"]) + 3 == 256
