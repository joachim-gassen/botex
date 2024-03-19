from otree.api import *

# This code is an adjusted variant of the oTree example code

doc = """
This is a standard 2-player trust game where the amount sent by player 1 gets
tripled. The trust game was first proposed by
<a href="https://doi.org/10.1006/game.1995.1027" target="_blank">
    Berg, Dickhaut, and McCabe (1995)
</a>.
"""

class C(BaseConstants):
    NAME_IN_URL = 'ftrust'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 10
    ENDOWMENT = cu(100)
    MULTIPLIER = 3

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    sent_amount = models.CurrencyField(
        min=0,
        max=C.ENDOWMENT,
        doc="""Amount to invest into the firm""",
        label="Please enter an amount from 0 to 100:",
    )
    sent_back_amount = models.CurrencyField(
        min=cu(0),
        max=sent_amount*C.MULTIPLIER,
        doc="""Dividend to be paid out to the investor""",
    )

class Player(BasePlayer):
    wealth = models.CurrencyField(initial = cu(0))
    comprehension_check = models.IntegerField(
        label="What is the role of the multiplier in this game?",
        blank=False,
        choices=[
            [1, 'It increases the private wealth of the investor'],
            [2, 'It increases the private wealth of the manager'],
            [3, 'It increases the invested amount, ' + 
            'potentially benefiting both the investor and the manager'],
        ],
    )
    manipulation_check = models.IntegerField(
        label="What was your role in this game?",
        blank=False,
        choices=[
            [1, 'Investor'],
            [2, 'Manager'],
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
    if subsession.round_number == 1:
        for p in subsession.get_players():
            p.participant.wealth = cu(0)
    
def sent_back_amount_max(group: Group):
    return group.sent_amount * C.MULTIPLIER

def set_payoffs(group: Group):
    p1 = group.get_player_by_id(1)
    p2 = group.get_player_by_id(2)
    p1.payoff = C.ENDOWMENT - group.sent_amount + group.sent_back_amount
    p2.payoff = group.sent_amount * C.MULTIPLIER - group.sent_back_amount
    p1.participant.wealth += p1.payoff
    p2.participant.wealth += p2.payoff


# --- Pages --------------------------------------------------------------------
    
class Introduction(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class Send(Page):
    """This page is only for P1
    P1 sends amount (all, some, or none) to P2
    This amount is tripled by experimenter,
    i.e if sent amount by P1 is 5, amount received by P2 is 15"""

    form_model = 'group'
    form_fields = ['sent_amount']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 1

class SendBackWaitPage(WaitPage):
    pass

class SendBack(Page):
    """This page is only for P2
    P2 sends back some amount (of the tripled amount received) to P1"""

    form_model = 'group'
    form_fields = ['sent_back_amount']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 2

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        tripled_amount = group.sent_amount * C.MULTIPLIER
        return dict(tripled_amount=tripled_amount)

class ResultsWaitPage(WaitPage):
    after_all_players_arrive = set_payoffs

class Results(Page):
    """This page displays the earnings of each player"""

    @staticmethod
    def vars_for_template(player: Player):
        group = player.group

        return dict(
            tripled_amount=group.sent_amount * C.MULTIPLIER,
            p1_wealth=group.get_player_by_id(1).participant.wealth,
            p2_wealth=group.get_player_by_id(2).participant.wealth
        )

class Checks(Page):
    """This page is displayed after the experimental run is complete."""
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS
    
    form_model = 'player'
    form_fields = ['comprehension_check', 'manipulation_check', 'human_check', 'feedback']

class Thanks(Page):
    """This page is displayed after the experimental run is complete."""
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS
    


page_sequence = [
    Introduction,
    Send,
    SendBackWaitPage,
    SendBack,
    ResultsWaitPage,
    Results,
    Checks,
    Thanks
]
