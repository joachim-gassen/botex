import os
import logging
import json
import sqlite3

import pandas as pd
from dotenv import load_dotenv

load_dotenv('secrets.env')

BOT_DB_SQLITE = os.environ.get('BOT_DB_SQLITE')
OTREE_DATA = 'data/external/all_apps_wide_2024-03-18.csv'

conn = sqlite3.connect(BOT_DB_SQLITE)
cursor = conn.cursor()
cursor.execute("SELECT * FROM conversations")
conversations = cursor.fetchall()
cursor.execute("SELECT * FROM sessions")
sessions = cursor.fetchall()
cursor.close()
conn.close()

otree_raw = pd.read_csv(OTREE_DATA, index_col= False)




def extract_participant_data(otree_raw, exp):
    wide = otree_raw.loc[
        otree_raw[f'{exp}.10.player.feedback'].notna()
    ].reset_index()
    if wide.shape[0] == 0: return None
    long = pd.melt(
        wide, id_vars='participant.code', ignore_index=False
    ).reset_index()
        
    vars = [
        'participant.time_started_utc', 'participant.payoff', 'session.code',
        f'{exp}.1.group.id_in_subsession', f'{exp}.1.player.id_in_group',
        f'{exp}.10.player.comprehension_check', f'{exp}.10.player.manipulation_check',
        f'{exp}.10.player.human_check', f'{exp}.10.player.feedback'
    ]

    participants = long.loc[
        long['variable'].isin(vars)
    ].pivot_table(
        index = 'participant.code', columns = 'variable', values = 'value',
        aggfunc = 'first'
    ).reset_index().rename(columns = {
        'participant.code': 'participant_code',
        'session.code': 'session_code',
        'participant.payoff': 'payoff',
        'participant.time_started_utc': 'time_started',
        f'{exp}.1.group.id_in_subsession': 'group_id',
        f'{exp}.1.player.id_in_group': 'role_in_group',
        f'{exp}.10.player.comprehension_check': 'comprehension_check',
        f'{exp}.10.player.manipulation_check': 'manipulation_check',
        f'{exp}.10.player.human_check': 'human_check',
        f'{exp}.10.player.feedback': 'feedback'
    })
    participants['experiment'] = exp
    participants['group_id'] = participants['group_id'].astype(int)
    participants['role_in_group'] = participants['role_in_group'].astype(int)
    participants['payoff'] = participants['payoff'].astype(int)
    participants['comprehension_check'] = participants['comprehension_check'].astype(int)
    participants['manipulation_check'] = participants['manipulation_check'].astype(int)
    participants['human_check'] = participants['human_check'].astype(int)   

    ordered_columns = [
        'experiment', 'session_code', 'participant_code', 'time_started', 
        'group_id', 'role_in_group', 'payoff', 
        'comprehension_check', 'manipulation_check',
        'human_check', 'feedback'
    ]

    return participants[ordered_columns]

def extract_round_data(otree_raw, exp):
    wide = otree_raw.loc[
        otree_raw[f'{exp}.10.player.feedback'].notna()
    ].reset_index()
    if wide.shape[0] == 0: return None
    long = pd.melt(
        wide, id_vars=['session.code', f'{exp}.1.group.id_in_subsession'], 
        ignore_index=False
    ).reset_index().rename(columns = {
        'session.code': 'session_code',
        f'{exp}.1.group.id_in_subsession': 'group_id'
    })
        
    vars = [
        [f'{exp}.{r}.group.sent_amount', f'{exp}.{r}.group.sent_back_amount']
        for r in range(1, 11)
    ]  
    vars = [item for sublist in vars for item in sublist]

    rounds = long.loc[
        long['variable'].isin(vars)
    ].copy()
    rounds['group_id'] = rounds['group_id'].astype(int)
    rounds['round'] = rounds['variable'].str.extract(r'(\d+)').astype(int)
    rounds['var'] = rounds['variable'].str.extract(rf'{exp}\.\d+\.group\.(\w+)')
    rounds['experiment'] = exp
    rounds = rounds.pivot_table(
        index = ['experiment', 'session_code', 'group_id', 'round'], 
        columns = 'var', values = 'value', aggfunc = 'first'
    ).sort_index().reset_index()
    rounds['sent_amount'] = rounds['sent_amount'].astype(int)
    rounds['sent_back_amount'] = rounds['sent_back_amount'].astype(int)
    return rounds 

def extract_rationales(participant_code):
    reason = []        
    c = pd.DataFrame(conversations)        
    conv = json.loads(c.loc[c[0] == participant_code, 2].item())
    check_for_error = False
    for message in conv:
        if message['role'] == 'assistant':
                try:
                    cont = json.loads(message['content'])
                    if 'questions' in cont:
                        for q in cont['questions']: 
                            if q['id'] == "id_sent_amount" or q['id'] == "id_sent_back_amount": 
                                reason.append(q['reason'])
                                check_for_error = True
                except:
                    logging.info(
                        f"message :'{message['content']}' failed to load as json"
                    )
                    continue
        else:
            if message['content'][:7] != 'Perfect' and check_for_error:
                reason.pop()
            check_for_error = False
    if len(reason) != 10: 
        logging.warning(f"""
            Error parsing bot conversation for participant {participant_code} 
            (delivers reasons for {len(reason)} responses)
        """)
        return None

    return reason

participants = pd.concat([
    extract_participant_data(otree_raw, 'trust'),
    extract_participant_data(otree_raw, 'ftrust')
])
rounds = pd.concat([
    extract_round_data(otree_raw, 'trust'),
    extract_round_data(otree_raw, 'ftrust')
])

rounds['sent_reason'] = ""
rounds['sent_back_reason'] = ""
for s in participants.session_code.unique():
    ps = participants.loc[
        participants.session_code == s, 'participant_code'
    ].tolist()
    for p in ps:
        g = participants.loc[
            participants.participant_code == p, 'group_id'
        ].item()
        r = participants.loc[
            participants.participant_code == p, 'role_in_group'
        ].item()
        if int(r) == 1:
            rounds.loc[
                (rounds.session_code == s) & (rounds.group_id == g),
                ['sent_reason']
            ] = extract_rationales(p)
        else:
            rounds.loc[
                (rounds.session_code == s) & (rounds.group_id == g),
                'sent_back_reason'
            ] = extract_rationales(p)
     
participants.to_csv('data/generated/participants.csv', index = False)
rounds.to_csv('data/generated/rounds.csv', index = False)