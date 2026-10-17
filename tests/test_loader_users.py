from pathlib import Path

import pytest

from app.loader import AllowedUser, DataFileError, load_allowed_users, normalise_email

REAL = Path("data/allowed_users.csv")


def write(tmp_path, text, name="u.csv", bom=False):
    p = tmp_path / name
    p.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text.encode())
    return p


def test_normalise_email():
    assert normalise_email("  Marcus.Vitale@Brightline.example ") == "marcus.vitale@brightline.example"


def test_real_file_has_3_admins_5_viewers_all_normalised():
    users = load_allowed_users(REAL)
    assert len(users) == 8
    assert sum(u.role == "admin" for u in users) == 3
    assert all(u.email == u.email.strip().lower() for u in users)
    emails = {u.email for u in users}
    assert "marcus.vitale@brightline.example" in emails
    assert "ines.reyes@brightline.example" in emails


def test_crlf_and_bom_load_the_same(tmp_path):
    body = "email,name,role\r\nA@x.example,A,admin\r\n"
    assert load_allowed_users(write(tmp_path, body, bom=True)) == [AllowedUser("a@x.example", "A", "admin")]


def test_unknown_role_is_skipped(tmp_path):
    p = write(tmp_path, "email,name,role\na@x.example,A,editor\nb@x.example,B, Viewer \n")
    assert load_allowed_users(p) == [AllowedUser("b@x.example", "B", "viewer")]


def test_duplicate_email_gets_lower_role(tmp_path):
    p = write(tmp_path, "email,name,role\na@x.example,A,admin\n A@X.example ,A,viewer\n")
    assert load_allowed_users(p) == [AllowedUser("a@x.example", "A", "viewer")]


def test_blank_email_is_skipped(tmp_path):
    p = write(tmp_path, "email,name,role\n  ,Nobody,viewer\nb@x.example,B,viewer\n")
    assert load_allowed_users(p) == [AllowedUser("b@x.example", "B", "viewer")]


def test_missing_column_names_the_file(tmp_path):
    p = write(tmp_path, "email,name\na@x.example,A\n")
    with pytest.raises(DataFileError, match=r"u\.csv.*role"):
        load_allowed_users(p)
