from enum import Enum
from typing import Any

from pydantic import BaseModel, create_model, Field


class Phase(Enum):
    start = 'start'
    middle = 'middle'
    end = 'end'

class BaseModelForbidExtra(BaseModel, extra='forbid'):
    pass

class StartSchema(BaseModelForbidExtra):
    task: str
    understood: bool

class SummarySchema(BaseModelForbidExtra):
    summary: str
    confused: bool

class EndSchema(BaseModelForbidExtra):
    remarks: str
    confused: bool

def create_answers_response_model(questions_json):
    answer_fields = {}
    for question in questions_json:
        qid = question['question_id']
        qtype = question['question_type']
        qoptions = question.get('answer_choices', [])
        
        if qtype in ['text', 'textarea', 'str']:
            answer_type = str
        elif qtype == 'float':
            answer_type = float
        elif qtype == 'number':
            answer_type = int
        elif qtype in ['radio', 'select-one']:
            if not qoptions:
                raise ValueError(f"Question ID {qid} has no answer options, even though it is a 'radio' or 'select-one' question")
            enum_name = f"AnswerChoice_{qid}"
            options = {f"option_{i}": option for i, option in enumerate(qoptions)}
            AnswerChoiceEnum = Enum(enum_name, options)
            answer_type = AnswerChoiceEnum
        else:
            answer_type = Any
        
        field_type = create_model(
            f"Answer_{qid}",
            reason=(str, ...),
            answer=(answer_type, ...),
            __base__=BaseModel
        )
        answer_fields[qid] = (field_type, Field(..., description=f"Answer for question ID {qid}"))
    
    Answers = create_model(
        'Answers',
        **answer_fields,
        __base__=BaseModel
    )
    
    class Response(BaseModel):
        answers: Answers 
        summary: str
        confused: bool
    
    return Response
