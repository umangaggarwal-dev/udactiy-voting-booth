#
# This file contains classes that correspond to voters
#
import base64
from enum import Enum

import jsons
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from backend.main.store import secret_registry

SECRET_NAME_KEY = "SECRET_NAME_KEY"
SECRET_NATIONAL_ID_KEY = "SECRET_NATIONAL_ID_KEY"
EXPECTED_BYTES = 32


def obfuscate_national_id(national_id: str) -> str:
    """
    Minimizes a national ID. The minimization may be either irreversible or reversible, but one might make life easier
    that the other, depending on the use-cases.

    :param: national_id A real national ID that is sensitive and needs to be obfuscated in some manner.
    :return: An obfuscated version of the national_id.
    """
    sanitized_national_id = national_id.replace("-", "").replace(" ", "").strip()
    sym_key = secret_registry.get_secret_bytes(SECRET_NATIONAL_ID_KEY)
    if not sym_key:
        sym_key = get_random_bytes(EXPECTED_BYTES * 2)
        secret_registry.overwrite_secret_bytes(SECRET_NATIONAL_ID_KEY, sym_key)
    cipher = AES.new(sym_key, AES.MODE_SIV)
    cipher.update(b"")
    ciphertext, tag = cipher.encrypt_and_digest(sanitized_national_id.encode("utf-8"))
    return base64.b64encode(ciphertext).decode("utf-8")


def encrypt_name(name: str) -> str:
    """
    Encrypts a name, non-deterministically.

    :param: name A plaintext name that is sensitive and needs to encrypt.
    :return: The encrypted cipher text of the name.
    """
    stripped_name = name.strip()
    sym_key = secret_registry.get_secret_bytes(SECRET_NAME_KEY)
    if not sym_key:
        sym_key = get_random_bytes(EXPECTED_BYTES * 2)
        secret_registry.overwrite_secret_bytes(SECRET_NAME_KEY, sym_key)
    nonce = get_random_bytes(EXPECTED_BYTES)
    cipher = AES.new(sym_key, AES.MODE_SIV, nonce=nonce)
    cipher.update(b"")
    ciphertext, tag = cipher.encrypt_and_digest(stripped_name.encode("utf-8"))
    ciphertext_str = base64.b64encode(ciphertext).decode("utf-8")
    tag_str = base64.b64encode(tag).decode("utf-8")
    return jsons.dumps({'ciphertext': ciphertext_str, 'tag': tag_str, 'nonce': nonce})


def decrypt_name(encrypted_name: str) -> str:
    """
    Decrypts a name. This is the inverse of the encrypt_name method above.

    :param: encrypted_name The ciphertext of a name that is sensitive
    :return: The plaintext name
    """
    input_dict = jsons.loads(encrypted_name)
    ciphertext = base64.b64decode(input_dict["ciphertext"].encode("utf-8"))
    tag = base64.b64decode(input_dict["tag"].encode("utf-8"))
    nonce = base64.b64decode(input_dict["nonce"].encode("utf-8"))
    sym_key = secret_registry.get_secret_bytes(SECRET_NAME_KEY)
    cipher = AES.new(sym_key, AES.MODE_SIV, nonce=nonce)
    cipher.update(b"")
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")


class MinimalVoter:
    """
    Our representation of a voter, with the national id obfuscated (but still unique).
    This is the class that we want to be using in the majority of our codebase.
    """

    def __init__(self, obfuscated_first_name: str, obfuscated_last_name: str, obfuscated_national_id: str, status: str):
        self.obfuscated_national_id = obfuscated_national_id
        self.obfuscated_first_name = obfuscated_first_name
        self.obfuscated_last_name = obfuscated_last_name
        self.status = status


class Voter:
    """
    Our representation of a voter, including certain sensitive information.=
    This class should only be used in the initial stages when requests come in; in the rest of the
    codebase, we should be using the ObfuscatedVoter class
    """

    def __init__(self, first_name: str, last_name: str, national_id: str):
        self.national_id = national_id
        self.first_name = first_name
        self.last_name = last_name

    def get_minimal_voter(self) -> MinimalVoter:
        """
        Converts this object (self) into its obfuscated version
        """
        return MinimalVoter(
            encrypt_name(self.first_name.strip()),
            encrypt_name(self.last_name.strip()),
            obfuscate_national_id(self.national_id),
            VoterStatus.NOT_REGISTERED.value)


class VoterStatus(Enum):
    """
    An enum that represents the current status of a voter.
    """
    NOT_REGISTERED = "not registered"
    REGISTERED_NOT_VOTED = "registered, but no ballot received"
    BALLOT_COUNTED = "ballot counted"
    FRAUD_COMMITTED = "fraud committed"


class BallotStatus(Enum):
    """
    An enum that represents the current status of a voter.
    """
    VOTER_BALLOT_MISMATCH = "the ballot doesn't belong to the voter specified"
    INVALID_BALLOT = "the ballot given is invalid"
    FRAUD_COMMITTED = "fraud committed: the voter has already voted"
    VOTER_NOT_REGISTERED = "voter not registered"
    BALLOT_COUNTED = "ballot counted"
