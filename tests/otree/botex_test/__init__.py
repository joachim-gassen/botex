from otree.api import *

doc = """
A very simple oTree survey for testing the BotEx package.
"""

# Treatment 1
class C(BaseConstants):
    NAME_IN_URL = 'botex_test'
    PLAYERS_PER_GROUP = 2
    NUM_ROUNDS = 1

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    string_field = models.StringField(
        label="What is your favorite color?",
        blank=False
    )
    integer_field = models.IntegerField(
        label="What is your favorite number?",
        blank=False
    )
    boolean_field = models.BooleanField(
        label="Do you like ice cream?",
        blank=False
    )
    choice_integer_field = models.IntegerField(
        label="Which statement do you most agree with?",
        blank=False,
        choices=[
            [1, 'Humans are better than bots'],
            [2, 'Bots are better than humans']
        ],
    )
    radio_field = models.IntegerField(
        label="What do you enjoy doing most?",
        choices=[
            [1, 'Reading'],
            [2, 'Writing'],
            [3, 'Arithmetic'],
            [4, 'Singing']
        ],
        widget=widgets.RadioSelect
    )
    float_field = models.FloatField(
        label="How many people live on the earth currently (in billions)?",
        blank=False
    )
    feedback = models.LongStringField(
        label="Do you have any feedback that you want to share?",
        blank=True
    )


class Player(BasePlayer):
    pass

# --- Functions ----------------------------------------------------------------

def creating_session(subsession: Subsession):
    pass
    
# --- Pages --------------------------------------------------------------------


class Introduction(Page):
    """
    An Intro page so that the bot has something to summarize and to
    click next on
    """
    pass

class Questions1(Page):
    """
    Some Questions fpr Player 1
    """
    form_model = 'group'
    form_fields = [
        'string_field', 'integer_field', 'boolean_field',
        'choice_integer_field'
    ]

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 1

class Player1WaitPage(WaitPage):
    pass

class Questions2(Page):
    """
    Some Questions fpr Player 2
    """
    form_model = 'group'
    form_fields = ['radio_field', 'float_field', 'feedback']

    @staticmethod
    def is_displayed(player: Player):
        return player.id_in_group == 2


class Player2WaitPage(WaitPage):
    pass


class Thanks(Page):
    """This page is displayed after the experimental run is complete."""
    

page_sequence = [
    Introduction,
    Questions1,
    Player1WaitPage,
    Questions2,
    Player2WaitPage,
    Thanks
]
