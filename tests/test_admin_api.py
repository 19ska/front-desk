from tests.conftest import as_user

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"


def test_admin_sees_allow_list_and_who_signed_up(client):
    as_user(client, SAM)
    admin = as_user(client, DANA)
    users = client.get("/api/admin/users", headers=admin).json()["users"]
    assert len(users) == 8
    assert [u["role"] for u in users] == ["admin"] * 3 + ["viewer"] * 5
    signed = {u["email"] for u in users if u["signed_up"]}
    assert signed == {SAM, DANA}
    assert set(users[0]) == {"email", "name", "role", "signed_up"}


def test_viewer_is_refused_by_the_api(client):
    r = client.get("/api/admin/users", headers=as_user(client, SAM))
    assert r.status_code == 403 and r.json() == {"error": "You don't have access to this."}


def test_admin_users_needs_a_session(client):
    assert client.get("/api/admin/users").status_code == 401
