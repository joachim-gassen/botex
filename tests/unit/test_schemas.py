from enum import Enum
import pytest
from pydantic import ValidationError
from src.botex.schemas import StartSchema, SummarySchema, EndSchema, create_answers_response_model

schemas_data = {
    'StartSchema': {
        'class': StartSchema,
        'valid': {'task': 'Complete the assignment', 'understood': True},
    },
    'SummarySchema': {
        'class': SummarySchema,
        'valid': {'summary': 'This is a summary of the task.', 'confused': False},
    },
    'EndSchema': {
        'class': EndSchema,
        'valid': {'remarks': 'Good progress was made.', 'confused': True},
    }
}

response_data_sets = {
    'text': {
        'questions_json': [{'question_id': 'q1', 'question_type': 'text'}],
        'response_data': {
            'answers': {
                'q1': {'answer': 'This is an answer', 'reason': 'Because it is required'}
            },
            'summary': 'Test summary',
            'confused': False
        },
        'invalid_answer': 42,
        'error_log': "Input should be a valid string"
    },
    'radio': {
        'questions_json': [{'question_id': 'q1', 'question_type': 'radio', 'answer_choices': ['Yes', 'No', 'Maybe']}],
        'response_data': {
            'answers': {
                'q1': {'answer': 'Yes', 'reason': 'Because I agree'}
            },
            'summary': 'Test summary',
            'confused': False
        },
        'invalid_answer': 'Invalid',
        'error_log': "Input should be 'Yes', 'No' or 'Maybe'"
    },
    'integer': {
        'questions_json': [{'question_id': 'q1', 'question_type': 'number'}],
        'response_data': {
            'answers': {
                'q1': {'answer': 42, 'reason': 'Because it is the answer'}
            },
            'summary': 'Test summary',
            'confused': False
        },
        'invalid_answer': 'Not an integer',
        'error_log': "Input should be a valid integer"
    },
    'float': {
        'questions_json': [{'question_id': 'q1', 'question_type': 'float'}],
        'response_data': {
            'answers': {
                'q1': {'answer': 42.0, 'reason': 'Because it is the answer'}
            },
            'summary': 'Test summary',
            'confused': False
        },
        'invalid_answer': 'Not a float',
        'error_log': "Input should be a valid number"
    }
}


def generate_valid_test_data():
    return [
        {'schema_class': schema_data['class'], 'valid_data': schema_data['valid']}
        for schema_data in schemas_data.values()
    ]


def generate_missing_fields_test_data():
    test_data = []
    for valid_case in generate_valid_test_data():
        schema_class, valid_data = valid_case.values()
        
        for field in valid_data.keys():
            invalid_data = valid_data.copy()
            del invalid_data[field]
            test_data.append({
                'schema_class': schema_class, 
                'invalid_data': invalid_data, 
                'missing_field': field
            })
    return test_data

def generate_extra_fields_test_data():
    return [
        {
            'schema_class': valid_case['schema_class'],
            'invalid_data': {**valid_case['valid_data'], 'extra_field': 'Not allowed'}
        }
        for valid_case in generate_valid_test_data()
    ]

@pytest.mark.unit
@pytest.mark.parametrize("params", generate_valid_test_data())
def test_schema_valid(params):
    """Test valid input for schemas, checking all fields."""
    schema_class, valid_data = params.values()

    instance = schema_class(**valid_data)
    
    for field, expected_value in valid_data.items():
        assert getattr(instance, field) == expected_value

@pytest.mark.unit
@pytest.mark.parametrize("params", generate_missing_fields_test_data())
def test_schema_missing_fields(params):
    """Test schemas raise ValidationError when required fields are missing."""
    schema_class, invalid_data, missing_field = params.values()

    with pytest.raises(ValidationError) as excinfo:
        schema_class(**invalid_data)
    assert "Field required" in str(excinfo.value)
    assert missing_field in str(excinfo.value)

@pytest.mark.unit
@pytest.mark.parametrize("params", generate_extra_fields_test_data())
def test_schema_forbid_extra_fields(params):
    """Test schemas raise ValidationError when extra fields are included."""
    schema_class, invalid_data = params.values()
    
    with pytest.raises(ValidationError) as excinfo:
        schema_class(**invalid_data)
    assert "Extra inputs are not permitted" in str(excinfo.value)

@pytest.mark.unit
@pytest.mark.parametrize("params", response_data_sets.values())
def test_create_answers_response_model(params):
    """Test create_answers_response_model for multiple question types, checking all fields dynamically."""
    questions_json, response_data, _, _ = params.values()
    
    ResponseModel = create_answers_response_model(questions_json)
    response_instance = ResponseModel(**response_data)

    for question_id, expected_values in response_data['answers'].items():
        answer_value = getattr(response_instance.answers, question_id).answer
        reason_value = getattr(response_instance.answers, question_id).reason

        # Fix: Use `.value` for enum comparison in radio question types
        if isinstance(answer_value, Enum):
            answer_value = answer_value.value
        
        assert answer_value == expected_values['answer']
        assert reason_value == expected_values['reason']

    assert response_instance.summary == response_data['summary']
    assert response_instance.confused == response_data['confused']


@pytest.mark.unit
@pytest.mark.parametrize("params", response_data_sets.values())
def test_create_answers_response_model_invalid_input(params):
    """Test invalid input for multiple question types."""
    questions_json, response_data, invalid_answer, error_log = params.values()
    
    ResponseModel = create_answers_response_model(questions_json)
    response_data['answers']['q1']['answer'] = invalid_answer

    with pytest.raises(ValidationError) as excinfo:
        ResponseModel(**response_data)
    assert error_log in str(excinfo.value)
