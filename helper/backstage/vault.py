"""Encrypted session records ([sessions] encrypt = true in config.toml).

When a session ends (after its summary), its folder is packed into one file,
encrypted with AES-256-GCM, and the plain folder is deleted:

    sessions/2026-11-20_1430_assistant_weekly-sync.backstage

The key is 32 random bytes kept in the GNOME keyring under the label
KEY_LABEL, so it is unlocked with your login and never stored in a file.
Losing the keyring entry means losing the records; it can be copied from
Passwords and Keys (Seahorse) for safe keeping.

A session that is still running is plain files (owner-only) until it ends.

Command line (tools/records.sh runs this):
    open <file.backstage>    decrypt into RUNTIME_FOLDER and open it there
    seal <session folder>    encrypt a folder by hand
"""

import base64
import io
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import gi

gi.require_version("Secret", "1")
from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: E402
from gi.repository import Secret  # noqa: E402

SUFFIX = ".backstage"
MAGIC = b"BACKSTAGE-RECORD-1\n"
NONCE_BYTES = 12
KEY_LABEL = "Backstage records key"
SCHEMA = Secret.Schema.new("io.github.saiftherehman.Backstage", Secret.SchemaFlags.NONE,
                           {"purpose": Secret.SchemaAttributeType.STRING})
ATTRIBUTES = {"purpose": "records"}
# Opened records go to a folder in memory that is emptied at logout.
RUNTIME_FOLDER = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "backstage-records"
USAGE = """Usage:
    tools/records.sh open <file.backstage>
    tools/records.sh seal <session folder>"""


def _key(create):
    stored = Secret.password_lookup_sync(SCHEMA, ATTRIBUTES, None)
    if stored:
        return base64.b64decode(stored)
    if not create:
        raise RuntimeError(f'No "{KEY_LABEL}" in the keyring, so the records cannot be opened')
    key = secrets.token_bytes(32)
    Secret.password_store_sync(SCHEMA, ATTRIBUTES, Secret.COLLECTION_DEFAULT, KEY_LABEL,
                               base64.b64encode(key).decode(), None)
    return key


def _decrypt(blob, key):
    if not blob.startswith(MAGIC):
        raise ValueError("Not a Backstage record")
    nonce = blob[len(MAGIC):len(MAGIC) + NONCE_BYTES]
    return AESGCM(key).decrypt(nonce, blob[len(MAGIC) + NONCE_BYTES:], MAGIC)


def seal(folder):
    """Encrypts a session folder into folder + SUFFIX and deletes the folder.
    The file is read back and checked before anything is deleted."""
    folder = Path(folder)
    key = _key(create=True)
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode="w:gz") as tar:
        tar.add(folder, arcname=folder.name)
    data = packed.getvalue()
    nonce = secrets.token_bytes(NONCE_BYTES)
    blob = MAGIC + nonce + AESGCM(key).encrypt(nonce, data, MAGIC)
    target = folder.with_name(folder.name + SUFFIX)
    partial = target.with_name(target.name + ".part")
    partial.write_bytes(blob)
    if _decrypt(partial.read_bytes(), key) != data:
        partial.unlink()
        raise RuntimeError(f"Encrypting {folder.name} failed its check; the folder was kept")
    partial.rename(target)
    shutil.rmtree(folder)
    return target


def seal_all(root):
    """Encrypts every plain session folder in root. Only called while no
    session runs, so any folder left is finished (or from a crash)."""
    sealed = []
    for folder in sorted(Path(root).iterdir()):
        if folder.is_dir() and (folder / "session.json").exists():
            sealed.append(seal(folder))
    return sealed


def unseal(file, destination):
    """Decrypts a record into destination; returns the session folder."""
    file = Path(file)
    data = _decrypt(file.read_bytes(), _key(create=False))
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(destination, filter="data")
    return destination / file.name.removesuffix(SUFFIX)


def main(args):
    if len(args) != 2 or args[0] not in ("open", "seal"):
        sys.exit(USAGE)
    os.umask(0o077)
    command, path = args
    if command == "seal":
        print(seal(path))
        return
    folder = unseal(path, RUNTIME_FOLDER)
    print(folder)
    subprocess.run(["gio", "open", str(folder)], check=False)


if __name__ == "__main__":
    main(sys.argv[1:])
