import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app({"TESTING":True,"DATABASE":str(tmp_path/"test.db"),"SECRET_KEY":"test-secret-for-tests-only-123456789"})


@pytest.fixture
def client(app):
    return app.test_client()


def register_login(client, username="alice"):
    csrf = client.get("/api/session").json["csrf"]
    headers = {"X-CSRF-Token":csrf}
    payload = {"username":username,"password":"test-password-123"}
    assert client.post("/api/register",json=payload,headers=headers).status_code == 201
    response = client.post("/api/login",json=payload,headers=headers)
    assert response.status_code == 200
    return {"X-CSRF-Token":response.json["csrf"]}


def test_auth_csrf_and_password(client):
    assert client.post("/api/register",json={"username":"a","password":"password-long"}).status_code == 403
    token = client.get("/api/session").json["csrf"]
    assert client.post("/api/register",json={"username":"a","password":"short"},headers={"X-CSRF-Token":token}).status_code == 400
    h = register_login(client)
    assert client.get("/api/session").json["user"]["username"] == "alice"
    assert client.post("/api/logout",headers=h).status_code == 200
    assert client.get("/api/session").json["user"] is None


def transaction(**changes):
    return {"kind":"expense","amount":"12.34","category":"Food","note":"Lunch","occurred_on":"2026-11-01",**changes}


def test_crud_summary_pagination_and_ownership(app,client):
    assert client.get("/api/transactions").status_code == 401
    h = register_login(client)
    assert client.post("/api/transactions",json=transaction(),headers=h).status_code == 201
    assert client.post("/api/transactions",json=transaction(kind="income",amount="50.00"),headers=h).status_code == 201
    assert client.post("/api/transactions",json=transaction(amount="99",occurred_on="2026-10-31"),headers=h).status_code == 201
    r = client.get("/api/transactions?month=2026-11&limit=1").json
    assert r["total"] == 2 and len(r["items"]) == 1
    s = client.get("/api/summary?month=2026-11").json
    assert (s["income_cents"],s["expense_cents"],s["balance_cents"]) == (5000,1234,3766)
    tid = client.get("/api/transactions?month=2026-11").json["items"][0]["id"]
    other = app.test_client()
    other_headers = register_login(other,"bob")
    assert other.get("/api/transactions?month=2026-11").json["total"] == 0
    assert other.put(f"/api/transactions/{tid}",json=transaction(),headers=other_headers).status_code == 404
    assert other.delete(f"/api/transactions/{tid}",headers=other_headers).status_code == 404
    assert client.put(f"/api/transactions/{tid}",json=transaction(amount="1.01"),headers=h).status_code == 200
    assert client.delete(f"/api/transactions/{tid}",headers=h).status_code == 200


@pytest.mark.parametrize("amount",["0","-1","NaN","Infinity","1.001",True,None,"100000001"])
def test_reject_bad_amount(client,amount):
    h = register_login(client)
    assert client.post("/api/transactions",json=transaction(amount=amount),headers=h).status_code == 400


def test_bad_dates_and_pagination(client):
    h = register_login(client)
    assert client.post("/api/transactions",json=transaction(occurred_on="2026-02-30"),headers=h).status_code == 400
    for query in ["month=2026-13","month=bad","month=2026-11&page=0","month=2026-11&limit=101"]:
        assert client.get("/api/transactions?"+query).status_code == 400
