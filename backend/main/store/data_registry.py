#
# This file is the interface between the stores and the database
#

import sqlite3
from sqlite3 import Connection
from typing import List, Tuple

from backend.main.objects.ballot import Ballot
from backend.main.objects.candidate import Candidate
from backend.main.objects.voter import MinimalVoter, VoterStatus


class VotingStore:
    """
    A singleton class that encapsulates the interface between the stores and the databases.

    To use, simply do:

    >>> voting_store = VotingStore.get_instance()   # this will create the stores, if they haven't been created
    >>> voting_store.add_candidate(...)  # now, you can call methods that you need here
    """

    voting_store_instance = None

    @staticmethod
    def get_instance():
        if not VotingStore.voting_store_instance:
            VotingStore.voting_store_instance = VotingStore()

        return VotingStore.voting_store_instance

    @staticmethod
    def refresh_instance():
        """
        DO NOT MODIFY THIS METHOD
        Only to be used for testing. This will only work if the sqlite connection is :memory:
        """
        if VotingStore.voting_store_instance:
            VotingStore.voting_store_instance.connection.close()
        VotingStore.voting_store_instance = VotingStore()

    def __init__(self):
        """
        DO NOT MODIFY THIS METHOD
        DO NOT call this method directly - instead use the VotingStore.get_instance method above.
        """
        self.connection = VotingStore._get_sqlite_connection()
        self.create_tables()

    @staticmethod
    def _get_sqlite_connection() -> Connection:
        """
        DO NOT MODIFY THIS METHOD
        """
        return sqlite3.connect(":memory:", check_same_thread=False)

    def create_tables(self):
        """
        Creates Tables
        """
        self.connection.execute(
            """CREATE TABLE candidates (candidate_id integer primary key autoincrement, name text)""")
        self.connection.execute(
            """CREATE TABLE voters (obfuscated_national_id text primary key, 
            obfuscated_first_name text, obfuscated_last_name text, status text)""")
        self.connection.execute(
            """CREATE TABLE ballots (ballot_number text primary key, 
            chosen_candidate_id text, voter_comments text, status text)""")
        # TODO: Add additional tables here, as you see fit
        self.connection.commit()

    def add_candidate(self, candidate_name: str):
        """
        Adds a candidate into the candidate table, overwriting an existing entry if one exists
        """
        self.connection.execute("""INSERT INTO candidates (name) VALUES (?)""", (candidate_name,))
        self.connection.commit()

    def get_candidate(self, candidate_id: str) -> Candidate:
        """
        Returns the candidate specified, if that candidate is registered. Otherwise returns None.
        """
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM candidates WHERE candidate_id=?""", (candidate_id,))
        candidate_row = cursor.fetchone()
        candidate = Candidate(candidate_id, candidate_row[1]) if candidate_row else None
        self.connection.commit()

        return candidate

    def get_all_candidates(self) -> List[Candidate]:
        """
        Gets ALL the candidates from the database
        """
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM candidates""")
        all_candidate_rows = cursor.fetchall()
        all_candidates = [Candidate(str(candidate_row[0]), candidate_row[1]) for candidate_row in all_candidate_rows]
        self.connection.commit()

        return all_candidates

    def add_voter(self, obfuscated_national_id: str, obfuscated_first_name: str,
                  obfuscated_last_name: str, status: VoterStatus):
        self.connection.execute(
            """INSERT INTO voters (obfuscated_national_id , obfuscated_first_name , 
            obfuscated_last_name , status) VALUES (?, ?, ?, ?)""",
            (obfuscated_national_id, obfuscated_first_name, obfuscated_last_name, status.value))
        self.connection.commit()

    def get_voter(self, obfuscated_national_id: str) -> MinimalVoter:
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM voters WHERE obfuscated_national_id=?""",
                       (obfuscated_national_id,))
        voter_row = cursor.fetchone()
        voter = MinimalVoter(
            obfuscated_national_id,
            voter_row[1],
            voter_row[2],
            VoterStatus(voter_row[3])
        ) if voter_row else None
        self.connection.commit()
        return voter

    def update_voter_status(self, obfuscated_national_id: str, status: VoterStatus):
        self.connection.execute("""UPDATE voters SET status = ? 
        WHERE obfuscated_national_id = ?""", (status.value, obfuscated_national_id))
        self.connection.commit()

    def delete_voter(self, obfuscated_national_id: str):
        self.connection.execute(
            """DELETE FROM voters where obfuscated_national_id = ?""", (obfuscated_national_id,))
        self.connection.commit()

    def get_all_voters(self, status: VoterStatus = None) -> List[MinimalVoter]:
        cursor = self.connection.cursor()
        if status:
            query = """SELECT * FROM voters WHERE status = ?"""
            cursor.execute(query, (status.value,))
        else:
            query = """SELECT * FROM voters"""
            cursor.execute(query)
        all_voter_rows = cursor.fetchall()
        all_voters = [MinimalVoter(
            obfuscated_national_id=voter[0],
            obfuscated_first_name=voter[1],
            obfuscated_last_name=voter[2],
            status=VoterStatus(voter[3]))
            for voter in all_voter_rows]
        self.connection.commit()
        return all_voters

    def add_ballot(self, ballot_number: str):
        self.connection.execute("""INSERT INTO ballots (ballot_number) VALUES (?)""", (ballot_number,))
        self.connection.commit()

    def get_ballot(self, ballot_number: str) -> Tuple[Ballot, str]:
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM ballots WHERE ballot_number = ?""", (ballot_number,))
        ballot_row = cursor.fetchone()
        ballot = Ballot(
            ballot_number,
            ballot_row[1],
            ballot_row[2]
        )
        return ballot, ballot_row[3]

    def delete_ballot(self, ballot_number: str):
        self.connection.execute(
            """DELETE FROM ballots where ballot_number = ?""", (ballot_number,))
        self.connection.commit()

    def update_ballot(self, ballot_number: str, chosen_candidate_id: str, voter_comments: str, status: str):
        self.connection.execute("""UPDATE ballots SET chosen_candidate_id = ?, voter_comments = ?, status = ? 
        WHERE ballot_number=?""", (chosen_candidate_id, voter_comments, status, ballot_number))
        self.connection.commit()

    def get_all_ballots(self) -> List[Tuple[Ballot, str]]:
        """
        Gets ALL the ballots from the database
        """
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM ballots""")
        all_ballot_rows = cursor.fetchall()
        all_ballots = [(Ballot(str(ballot_row[0]), ballot_row[1], ballot_row[2]), ballot_row[3])
                       for ballot_row in all_ballot_rows]
        self.connection.commit()
        return all_ballots
    # TODO: If you create more tables in the create_tables method, feel free to add more methods here to make accessing
    #       data from those tables easier. See get_all_candidates, get_candidates and add_candidate for examples of how
    #       to do this.
