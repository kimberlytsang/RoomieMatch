"""The home page is public and renders."""


def test_home_page_renders(client, db):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res["Content-Type"]


def test_home_page_omits_removed_decorative_content(client, db):
    res = client.get("/")
    assert b"Make room for a better match." not in res.content
    assert b"plus-mark" not in res.content
    assert b"Roommates, matched around what matters." not in res.content


def test_unknown_page_is_404(client, db):
    assert client.get("/no-such-page/").status_code == 404
