import stat

from ai_drama_web.secrets import LocalSecretStore


def test_local_secret_store_masks_key_and_uses_private_file_mode(tmp_path):
    secret_store = LocalSecretStore(tmp_path / "runtime-data")
    api_key = "agnes-live-secret-1234"

    secret_store.set_agnes_api_key(api_key)

    secret_path = tmp_path / "runtime-data" / "secrets" / "agnes-api-key"
    assert secret_store.get_agnes_api_key() == api_key
    assert secret_store.agnes_status() == {"configured": True, "masked_suffix": "1234"}
    assert stat.S_IMODE(secret_path.stat().st_mode) == 0o600
    assert api_key not in repr(secret_store.agnes_status())

    secret_store.delete_agnes_api_key()

    assert secret_store.get_agnes_api_key() == ""
    assert secret_store.agnes_status() == {"configured": False, "masked_suffix": ""}
    assert not secret_path.exists()


def test_local_secret_store_never_returns_short_key_as_masked_suffix(tmp_path):
    secret_store = LocalSecretStore(tmp_path / "runtime-data")
    short_key = "abcd"

    secret_store.set_agnes_api_key(short_key)

    assert secret_store.get_agnes_api_key() == short_key
    assert secret_store.agnes_status() == {"configured": True, "masked_suffix": ""}
    assert short_key not in repr(secret_store.agnes_status())


def test_agnes_settings_api_never_echoes_full_key(client):
    api_key = "agnes-live-secret-5678"

    initial = client.get("/api/settings/agnes")
    assert initial.status_code == 200, initial.text
    assert initial.json() == {"configured": False, "masked_suffix": ""}

    put_response = client.put("/api/settings/agnes", json={"api_key": api_key})
    assert put_response.status_code == 200, put_response.text
    assert put_response.json() == {"configured": True, "masked_suffix": "5678"}

    get_response = client.get("/api/settings/agnes")
    assert get_response.status_code == 200, get_response.text
    assert get_response.json() == {"configured": True, "masked_suffix": "5678"}

    delete_response = client.delete("/api/settings/agnes")
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json() == {"configured": False, "masked_suffix": ""}

    blank_response = client.put("/api/settings/agnes", json={"api_key": "   "})
    assert blank_response.status_code == 422

    returned_text = "\n".join(
        [
            initial.text,
            put_response.text,
            get_response.text,
            delete_response.text,
            blank_response.text,
        ]
    )
    assert api_key not in returned_text


def test_agnes_settings_rejects_short_and_malformed_keys_without_echoing_secret(client):
    short_key = "abcd"
    short_response = client.put("/api/settings/agnes", json={"api_key": short_key})
    assert short_response.status_code == 422
    assert short_key not in short_response.text

    malformed_secret = "agnes-live-secret-9999"
    malformed_response = client.put("/api/settings/agnes", json={"api_key": [malformed_secret]})
    assert malformed_response.status_code == 422
    assert malformed_secret not in malformed_response.text
