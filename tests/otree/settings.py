from os import environ

SESSION_CONFIGS = [
    dict(
        name='botex_test',
        app_sequence=['botex_test'],
        num_demo_participants=2,
    ),
]
SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=1.00, participation_fee=0.00, doc=""
)
PARTICIPANT_FIELDS = []
SESSION_FIELDS = []

# ISO-639 code
# for example: de, fr, ja, ko, zh-hans
LANGUAGE_CODE = 'en'

# Only relevant when OTREE_AUTH_LEVEL is set to "DEMO" or "STUDY"
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = environ.get('OTREE_ADMIN_PASSWORD')
SECRET_KEY = '12345'

DEMO_PAGE_INTRO_HTML = """ """
