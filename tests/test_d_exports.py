import csv
import json
from numbers import Number

import pytest
import botex

from tests.utils import *

@pytest.mark.dependency(
    name="export_part", depends=["conversations_complete"], scope='session'
)
def test_export_part():
    csv_file = 'tests/botex_participants.csv'
    botex.export_participant_data(csv_file, botex_db="tests/botex.db")
    assert os.path.exists(csv_file)
    try:
        with open(csv_file) as f:
            participants = list(csv.DictReader(f))
    except:
        assert False
    assert len(participants) % 2 == 0
    for p in participants:
        assert p.keys() == {
            'session_name', 'session_id', 'participant_id', 'is_human',
            'url', 'time_in', 'time_out'
        }

@pytest.mark.dependency(
    name="export_resp", depends=["conversations_complete"], scope='session'
)
def test_export_response():
    csv_file = 'tests/botex_response.csv'
    botex.export_response_data(csv_file, botex_db="tests/botex.db")
    assert os.path.exists(csv_file)
    try:
        with open(csv_file) as f:
            resp = list(csv.DictReader(f))
    except:
        assert False
    assert len(resp) % 9 == 0
    for r in resp:
        assert r.keys() == {
            'session_id', 'participant_id', 'round', 
            'question_id', 'answer', 'reason'
        }
        assert r['round'] == '1'

