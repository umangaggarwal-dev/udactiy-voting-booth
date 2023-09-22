import base64
from typing import Set, Optional

import jsons

from backend.main.api.registry import get_voter_status
from backend.main.detection.pii_detection import redact_free_text
from backend.main.objects.ballot import Ballot, generate_ballot_number
from backend.main.objects.candidate import Candidate
from backend.main.objects.voter import BallotStatus, obfuscate_national_id, VoterStatus
from backend.main.store.data_registry import VotingStore


def issue_ballot(voter_national_id: str) -> Optional[str]:
    """
    Issues a new ballot to a given voter. The ballot number of the new ballot. This method should NOT invalidate any old
    ballots. If the voter isn't registered, should return None.

    :params: voter_national_id The sensitive ID of the voter to issue a new ballot to.
    :returns: The ballot number of the new ballot, or None if the voter isn't registered
    """
    store = VotingStore.get_instance()
    obfuscated_national_id = obfuscate_national_id(voter_national_id)
    try:
        voter = store.get_voter(obfuscated_national_id)
        if voter:
            ballot_number = generate_ballot_number(voter_national_id)
            store.add_ballot(ballot_number)
            return ballot_number
    except Exception as err:
        pass
    return None


def count_ballot(ballot: Ballot, voter_national_id: str) -> BallotStatus:
    """
    Validates and counts the ballot for the given voter. If the ballot contains a sensitive comment, this method will
    appropriately redact the sensitive comment.

    This method will return the following upon the completion:
    1. BallotStatus.FRAUD_COMMITTED - If the voter has already voted
    2. BallotStatus.VOTER_BALLOT_MISMATCH - The ballot does not belong to this voter
    3. BallotStatus.INVALID_BALLOT - The ballot has been invalidated, or does not exist
    4. BallotStatus.BALLOT_COUNTED - If the ballot submitted in this request was successfully counted
    5. BallotStatus.VOTER_NOT_REGISTERED - If the voter is not registered

    :param: ballot The Ballot to count
    :param: voter_national_id The sensitive ID of the voter who the ballot corresponds to.
    :returns: The Ballot Status after the ballot has been processed.
    """
    obfuscated_national_id = obfuscate_national_id(voter_national_id)
    voter_status = get_voter_status(obfuscated_national_id)
    if voter_status == VoterStatus.NOT_REGISTERED.value:
        return BallotStatus.VOTER_NOT_REGISTERED
    store = VotingStore.get_instance()
    existing_ballot, status = store.get_ballot(ballot.ballot_number)
    if not existing_ballot:
        return BallotStatus.INVALID_BALLOT
    is_matched_ballot = verify_ballot(voter_national_id, ballot.ballot_number)
    if not is_matched_ballot:
        return BallotStatus.VOTER_BALLOT_MISMATCH
    if voter_status != VoterStatus.REGISTERED_NOT_VOTED.value:
        # mark fraud
        store.update_voter_status(obfuscated_national_id, VoterStatus.FRAUD_COMMITTED.value)
        invalidate_ballot(ballot.ballot_number)
        return BallotStatus.FRAUD_COMMITTED
    ballot.voter_comments = redact_free_text(ballot.voter_comments)
    store.update_ballot(ballot.ballot_number,
                        ballot.chosen_candidate_id,
                        ballot.voter_comments,
                        BallotStatus.BALLOT_COUNTED.value)
    store.update_voter_status(obfuscated_national_id, VoterStatus.BALLOT_COUNTED.value)
    return BallotStatus.BALLOT_COUNTED


def invalidate_ballot(ballot_number: str) -> bool:
    """
    Marks a ballot as invalid so that it cannot be used. This should only work on ballots that have NOT been cast. If a
    ballot has already been cast, it cannot be invalidated.

    If the ballot does not exist or has already been cast, this method will return false.

    :returns: If the ballot does not exist or has already been cast, will return Boolean FALSE.
              Otherwise will return Boolean TRUE.
    """
    store = VotingStore.get_instance()
    try:
        ballot, status = store.get_ballot(ballot_number)
        if ballot and status and status == "" and ballot.voter_comments == "" and ballot.chosen_candidate_id == "":
            store.delete_ballot(ballot_number)
            return True
    except Exception as err:
        pass
    return False


def verify_ballot(voter_national_id: str, ballot_number: str) -> bool:
    """
    Verifies the following:

    1. That the ballot was specifically issued to the voter specified
    2. That the ballot is not invalid

    If all of the points above are true, then returns Boolean True. Otherwise returns Boolean False.

    :param: voter_national_id The id of the voter about to cast the ballot with the given ballot number
    :param: ballot_number The ballot number of the ballot that is about to be cast by the given voter
    :returns: Boolean True if the ballot was issued to the voter specified, and if the ballot has not been marked as
              invalid. Boolean False otherwise.
    """
    store = VotingStore.get_instance()
    try:
        ballot = store.get_ballot(ballot_number)
        if ballot:
            json_string = base64.b64decode(ballot_number.encode("utf-8")).decode("utf-8")
            ballot_dict = jsons.loads(json_string)
            salt = ballot_dict["salt"]
            generated_ballot = generate_ballot_number(voter_national_id, salt)
            if generated_ballot == ballot_number:
                return True
    except Exception as err:
        pass
    return False


#
# Aggregate API
#

def get_all_ballot_comments() -> Set[str]:
    """
    Returns a list of all the ballot comments that are non-empty.
    :returns: A list of all the ballot comments that are non-empty
    """
    store = VotingStore.get_instance()
    ballot_list = [ballot[0] for ballot in store.get_all_ballots()]
    return set(map(
        lambda ballot: ballot.voter_comments,
        filter(lambda ballot: ballot.voter_comments is not None and ballot.voter_comments != "", ballot_list)
    ))


def compute_election_winner() -> Candidate:
    """
    Computes the winner of the election - the candidate that gets the most votes (even if there is not a majority).
    :return: The winning Candidate
    """
    store = VotingStore.get_instance()
    ballot_tuple_list = store.get_all_ballots()
    ballot_list = list(map(lambda ballot: ballot[0],
                           filter(lambda ballot: ballot[1] == BallotStatus.BALLOT_COUNTED.value, ballot_tuple_list)))
    candidate_id_count = {}
    for ballot in ballot_list:
        candidate_id = ballot.chosen_candidate_id
        candidate_id_count.update({candidate_id: candidate_id_count.get(candidate_id, 0) + 1})
    return max(candidate_id_count, key=lambda id: candidate_id_count[id])


def get_all_fraudulent_voters() -> Set[str]:
    """
    Returns a complete list of voters who committed fraud. For example, if the following committed fraud:

    1. first: "John", last: "Smith"
    2. first: "Linda", last: "Navarro"

    Then this method would return {"John Smith", "Linda Navarro"} - with a space separating the first and last names.
    """
    # TODO: Implement this!
    raise NotImplementedError()
