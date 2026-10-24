"""The home page is public and renders."""


def test_home_page_renders(client, db):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Find a roommate who actually fits." in res.content


def test_unknown_page_is_404(client, db):
    assert client.get("/no-such-page/").status_code == 404
