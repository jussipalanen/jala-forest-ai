from jalaforest.config import describe_database_url, is_local_database_url, normalize_database_url

NEON = "postgresql://neondb_owner:secret@ep-flat-truth-za9sbrze.c-2.eu-west-2.aws.neon.tech/neondb?sslmode=require"


def test_plain_urls_use_psycopg3():
    assert normalize_database_url(NEON).startswith("postgresql+psycopg://neondb_owner:secret@")
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_database_url("postgresql+psycopg://u:p@h/db") == "postgresql+psycopg://u:p@h/db"


def test_description_hides_password():
    text = describe_database_url(normalize_database_url(NEON))
    assert text == "ep-flat-truth-za9sbrze.c-2.eu-west-2.aws.neon.tech:5432/neondb"
    assert "secret" not in text


def test_local_detection():
    assert is_local_database_url("postgresql+psycopg://a:b@localhost:5433/jalaforest")
    assert not is_local_database_url(NEON)
