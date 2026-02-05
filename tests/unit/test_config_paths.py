from epic_trips_crm.config.paths import env_file_path


def test_env_file_path_is_reasonable():
    p = env_file_path()
    # Just a sanity check: ends with .env
    assert p.name == ".env"
