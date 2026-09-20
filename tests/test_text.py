from app.text import canonicalize_url, clean_html, stable_hash


def test_clean_html_removes_markup_and_compacts_space() -> None:
    assert clean_html("<p>Hello <strong>world</strong></p>\n<script>x()</script>") == (
        "Hello world x()"
    )


def test_hash_is_stable_and_case_insensitive() -> None:
    assert stable_hash("Hello", "WORLD") == stable_hash(" hello ", "world")


def test_remoteok_url_is_canonicalized() -> None:
    assert canonicalize_url("http://remoteOK.com/remote-jobs/1") == (
        "https://remoteok.com/remote-jobs/1"
    )
