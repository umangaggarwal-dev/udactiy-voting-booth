import re

from backend.main.objects.voter import decrypt_name, decrypt_national_id
from backend.main.store.data_registry import VotingStore

REDACTED_PHONE_NUMBER = "[REDACTED PHONE NUMBER]"
REDACTED_NAME = "[REDACTED NAME]"
REDACTED_EMAIL = "[REDACTED EMAIL]"
REDACTED_NATIONAL_ID = "[REDACTED NATIONAL ID]"


def redact_free_text(free_text: str) -> str:
    """
    :param: free_text The free text to remove sensitive data from
    :returns: The redacted free text
    """
    redacted_text = free_text[:]
    store = VotingStore.get_instance()
    voter_list = store.get_all_voters()
    candidate_list = store.get_all_candidates()
    first_names = set(map(lambda voter: decrypt_name(voter.obfuscated_first_name), voter_list))
    last_names = set(map(lambda voter: decrypt_name(voter.obfuscated_last_name), voter_list))
    national_id_set = set(map(lambda voter: decrypt_national_id(voter.obfuscated_national_id), voter_list))
    candidate_names = set(map(lambda candidate: candidate.name, candidate_list))
    for name in first_names:
        redacted_text = redacted_text.replace(name, REDACTED_NAME)
    for name in last_names:
        redacted_text = redacted_text.replace(name, REDACTED_NAME)
    for name in candidate_names:
        redacted_text = redacted_text.replace(name, REDACTED_NAME)
    for national_id in national_id_set:
        redacted_text.replace(national_id, REDACTED_NATIONAL_ID)
    # phone_number_regex = r'(?:(?:\+?\d{1,3}\s?)?\d{10}|\+?\d{1,3}\s\d{3}-\d{3}-\d{4}|\d{3}\s\d{3}-\d{4})'
    phone_number_regex = r'\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}'
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
    # national_id_regex = r'\b(?:' + '|'.join(national_id_set) + r')\b|(\d+)'
    national_id_regex_0 = r'\b\d{9}\b'
    national_id_regex_1 = r'\d+-+\d+-+\d+'
    national_id_regex_2 = r'\d+\s+\d+\s+\d+'
    redacted_text = re.sub(phone_number_regex, lambda k: REDACTED_PHONE_NUMBER, redacted_text)
    redacted_text = re.sub(email_regex, lambda k: REDACTED_EMAIL, redacted_text)
    # redacted_text = re.sub(national_id_regex, lambda k: REDACTED_NATIONAL_ID, redacted_text)
    matches_0 = re.findall(national_id_regex_0, redacted_text)
    for match in matches_0:
        redacted_text = redacted_text.replace(match, REDACTED_NATIONAL_ID)
    matches_1 = re.findall(national_id_regex_1, redacted_text)
    for match in matches_1:
        redacted_text = redacted_text.replace(match, REDACTED_NATIONAL_ID)
    matches_2 = re.findall(national_id_regex_2, redacted_text)
    for match in matches_2:
        redacted_text = redacted_text.replace(match, REDACTED_NATIONAL_ID)
    return redacted_text
