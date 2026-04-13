"""Résolution stricte Person → pe_client et routes custody canoniques."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from auth import get_password_hash
from database import AdminUser, Person
from services.custody.identity_resolution import (
    AmbiguousPhoneResolutionError,
    CustodyIdentityResolutionError,
    MultipleResolutionInputsError,
    NoResolutionInputError,
    resolve_person_and_pe_client_for_custody,
)
from tests.conftest import make_linked_client
from tests.test_custody import ADMIN_HEADERS, _create_provider


def _headers(db):
    from tests.conftest import make_admin_headers

    return {**ADMIN_HEADERS, **make_admin_headers(db)}


def test_resolve_person_id_success(db):
    c = make_linked_client(db)
    r = resolve_person_and_pe_client_for_custody(db, person_id=c.person_id)
    assert r.pe_client_id == c.id
    assert r.source == "person_id"


def test_resolve_pe_client_id_success(db):
    c = make_linked_client(db)
    r = resolve_person_and_pe_client_for_custody(db, pe_client_id=c.id)
    assert r.person_id == c.person_id
    assert r.source == "pe_client_id"


def test_resolve_phone_via_admin_user_mobile(db):
    c = make_linked_client(db)
    phone = "+33699887766"
    u = AdminUser(
        email=None,
        hashed_password=get_password_hash("x"),
        mobile_e164=phone,
        person_id=c.person_id,
    )
    db.add(u)
    db.flush()

    r = resolve_person_and_pe_client_for_custody(db, phone_e164=phone)
    assert r.pe_client_id == c.id
    assert r.source == "phone_e164"


def test_resolve_phone_via_profile_collected(db):
    c = make_linked_client(db)
    phone = "+33611223344"
    person = db.query(Person).filter(Person.id == c.person_id).first()
    assert person is not None
    pj = dict(person.profile_json or {})
    coll = dict(pj.get("collected") or {})
    coll["phone_e164"] = phone
    pj["collected"] = coll
    person.profile_json = pj
    db.flush()

    r = resolve_person_and_pe_client_for_custody(db, phone_e164=phone)
    assert r.pe_client_id == c.id


def test_resolve_phone_ambiguous_raises(db):
    phone = "+33600000099"
    c1 = make_linked_client(db)
    c2 = make_linked_client(db)
    for c in (c1, c2):
        person = db.query(Person).filter(Person.id == c.person_id).first()
        pj = dict(person.profile_json or {})
        coll = dict(pj.get("collected") or {})
        coll["phone_e164"] = phone
        pj["collected"] = coll
        person.profile_json = pj
    db.flush()

    with pytest.raises(AmbiguousPhoneResolutionError):
        resolve_person_and_pe_client_for_custody(db, phone_e164=phone)


def test_resolve_multiple_inputs_raises(db):
    c = make_linked_client(db)
    with pytest.raises(MultipleResolutionInputsError):
        resolve_person_and_pe_client_for_custody(db, person_id=c.person_id, pe_client_id=c.id)


def test_resolve_none_raises(db):
    with pytest.raises(NoResolutionInputError):
        resolve_person_and_pe_client_for_custody(db)


def test_resolve_person_without_pe_raises(db):
    person = Person(
        status="active",
        profile_json={"collected": {}},
    )
    db.add(person)
    db.flush()
    with pytest.raises(CustodyIdentityResolutionError):
        resolve_person_and_pe_client_for_custody(db, person_id=person.id)


def test_http_identity_resolve(client: TestClient, db):
    c = make_linked_client(db)
    res = client.post(
        "/api/admin/custody/identity/resolve",
        json={"person_id": str(c.person_id)},
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["pe_client_id"] == str(c.id)
    assert data["resolution_source"] == "person_id"


def test_http_canonical_create_client_account(client: TestClient, db):
    c = make_linked_client(db)
    prov = _create_provider(client, f"Canon-{uuid.uuid4().hex[:6]}")
    res = client.post(
        "/api/admin/custody/accounts/client/canonical",
        json={
            "provider_id": prov["id"],
            "currency": "EUR",
            "account_holder_name": "Holder",
            "iban": f"FR76{uuid.uuid4().hex[:18].upper()}",
            "bic": "AGFBFRCC",
            "person_id": str(c.person_id),
        },
        headers=_headers(db),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["client_id"] == str(c.id)
    assert body["person_id"] == str(c.person_id)


def test_http_simple_create_euro_account(client: TestClient, db):
    c = make_linked_client(db)
    _create_provider(client, f"Simple-{uuid.uuid4().hex[:6]}")
    res = client.post(
        "/api/admin/custody/accounts/client/simple-create",
        json={"person_id": str(c.person_id)},
        headers=_headers(db),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "message" in body
    assert body["account"]["currency"] == "EUR"
    assert body["account"]["iban"]
    assert body["account"]["client_id"] == str(c.id)

    res2 = client.post(
        "/api/admin/custody/accounts/client/simple-create",
        json={"person_id": str(c.person_id)},
        headers=_headers(db),
    )
    assert res2.status_code == 409


def test_account_list_enriches_person_fields(client: TestClient, db):
    c = make_linked_client(db)
    person = db.query(Person).filter(Person.id == c.person_id).first()
    pj = dict(person.profile_json or {})
    coll = dict(pj.get("collected") or {})
    coll["email"] = "biz@customer.example"
    pj["collected"] = coll
    person.profile_json = pj
    db.flush()

    prov = _create_provider(client, f"Enr-{uuid.uuid4().hex[:6]}")
    client.post(
        "/api/admin/custody/accounts/client",
        json={
            "provider_id": prov["id"],
            "account_type": "client_deposit_account",
            "currency": "EUR",
            "account_holder_name": "H",
            "client_id": str(c.id),
            "iban": f"FR76{uuid.uuid4().hex[:18].upper()}",
        },
        headers=_headers(db),
    )
    lst = client.get("/api/admin/custody/accounts", headers=ADMIN_HEADERS).json()
    row = next(x for x in lst["items"] if x.get("client_id") == str(c.id))
    assert row.get("person_id") == str(c.person_id)
    assert row.get("person_email_collected") == "biz@customer.example"
