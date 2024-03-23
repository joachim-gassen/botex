from otree.api import *

doc = """
This is an almost word-identical version of the classic deception game
<a href="https://doi.org/10.1257/0002828053828662" target="_blank">
    (Gneezy, AER 2006)
</a>.
"""

# Treatment 1
class C(BaseConstants):
    NAME_IN_URL = 'experiment'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 1
    AMOUNT_A1=5
    AMOUNT_A2=6
    AMOUNT_B1=6
    AMOUNT_B2=5

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    message = models.IntegerField(
        label="Which message do you want to send to your counterpart?",
        blank=False,
        choices=[
            [1, 'Message 1: “Option A will earn you more money than option B.”'],
            [2, 'Message 2: “Option B will earn you more money than option A.”']
        ],
    )
    choice = models.IntegerField(
        label="Which option fo you want to choose?",
        blank=False,
        choices=[
            [1, 'Option A'],
            [2, 'Option B']
        ],
    )

class Player(BasePlayer):
    comprehension_check1 = models.IntegerField(
        label="Who decides on the payoffs in this game?",
        blank=False,
        choices=[
            [1, 'The other participant'],
            [2, 'Me']
        ],
    )
    comprehension_check2 = models.IntegerField(
        label="What was your role in this game?",
        blank=False,
        choices=[
            [1, 'I had to send a message to the other participant'],
            [2, 'I had to pick one of two options that decided the payoffs for both participants'],
        ]
    )
    human_check = models.IntegerField(
        label="Please characterize your personality",
        blank=False,
        choices=[
            [1, 'I am a Human'],
            [2, 'I am a Bot'],
        ]
    )
    feedback = models.LongStringField(
        label="Do you have any feedback that you want to share?",
        blank=True
    )


# --- Functions ----------------------------------------------------------------

def creating_session(subsession: Subsession):
    pass
    
def sent_back_amount_max(group: Group):
    return group.sent_amount * C.MULTIPLIER

def set_payoffs(group: Group):
    p1 = group.get_player_by_id(1)
    p2 = group.get_player_by_id(2)
    if group.choice == 1:
        p1.payoff = C.AMOUNT_A1
        p2.payoff = C.AMOUNT_A2
    else:
        p1.payoff = C.AMOUNT_B1
        p2.payoff = C.AMOUNT_B2


# --- Pages --------------------------------------------------------------------


class Choice1(Page):
    """
    This page is only for P1
    P1 has to decide on the message to send to P2
    """

    form_model = 'group'
    form_fields = ['message']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 1

class MessageWaitPage(WaitPage):
    pass

class Choice2(Page):
    """
    This page is only for P2
    P2 makes a decision based on the message received from P1
    """

    form_model = 'group'
    form_fields = ['choice']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 2

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        message = group.message
        return dict(message=message)

class ChoiceWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs


class Checks(Page):
    """This page is displayed after the experimental run is complete."""
    
    form_model = 'player'
    form_fields = [
        'comprehension_check1', 'comprehension_check2', 'human_check', 'feedback'
    ]

class PayoffThanks(Page):
    """This page is displayed after the experimental run is complete."""
    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        if group.choice==1: choice = 'A' 
        else: choice = 'B'
        return dict(choice=choice, payoff=player.payoff)
    

page_sequence = [
    Choice1,
    MessageWaitPage,
    Choice2,
    ChoiceWaitPage,
    Checks,
    PayoffThanks
]
