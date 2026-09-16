from smishing_api.url_features import model_document, url_structure_features


def test_url_structure_features_match_training_definition() -> None:
    assert url_structure_features("https://example.com/a/12345/b/67") == (6, 5)


def test_url_structure_features_handle_no_digits_or_slashes() -> None:
    assert url_structure_features("example.com") == (0, 0)


def test_model_document_contains_features_and_original_url() -> None:
    url = "https://example.com/order/20260916"
    assert model_document(url) == (
        "path_depth=4 max_numeric_sequence=8 "
        "url=https://example.com/order/20260916"
    )
