from enum import Enum
from typing import Any

from pydantic import BaseModel, create_model, Field, field_validator,  ValidationError

def convert_string_to_boolean(value):
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower == 'true':
            return True
        elif value_lower == 'false':
            return False
    return value 

class Phase(Enum):
    start = 'start'
    middle = 'middle'
    end = 'end'

class BaseModelForbidExtra(BaseModel, extra='forbid'):
    pass

class StartSchema(BaseModelForbidExtra):
    task: str = Field(..., description="A concise summary of your task as you understand it.")
    understood: bool = Field(..., description="Whether you understood the task or not. Set to true if you understood the task, false otherwise.")

    @field_validator('understood',  mode='before')
    def validate_field1(cls, value):
        return convert_string_to_boolean(value)


class SummarySchema(BaseModelForbidExtra):
    summary: str = Field(..., description="Your summary of the content of the page and what you learn from it about the survey/experiment that you are participating in.")
    confused: bool = Field(..., description="Whether you are confused by your task or any part of the instructions. Set to true if you are confused, false otherwise.")

    @field_validator('summary')
    def summary_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Summary must not be empty")
        return v
    
    @field_validator('confused', mode='before')
    def validate_field1(cls, value):
        return convert_string_to_boolean(value)

class EndSchema(BaseModelForbidExtra):
    remarks: str = Field(..., description="Your final remarks")
    confused: bool = Field(..., description="Whether you are confused by your task or any part of the instructions. Set to true if you are confused, false otherwise.")

    @field_validator('confused', mode='before')
    def validate_field1(cls, value):
        return convert_string_to_boolean(value)


class AnswerBase(BaseModel):
    reason: str = Field(...)

    @field_validator('reason')
    def reason_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Reason must not be empty")
        return v

def create_answers_response_model(questions_json):
    answer_fields = {}
    for id_, question in questions_json.items():
        qlabel = question['question_label']
        qtype = question['question_type']
        
        if qtype in ['text', 'textarea', 'str']:
            answer_type = str
        elif qtype == 'float':
            answer_type = float
        elif qtype == 'number':
            answer_type = int
        elif qtype in ['radio', 'select-one', 'button-radio']:
            if not (answer_choices := question.get('answer_choices')):
                raise ValueError(f"Question ID {id_} has no answer options, even though it is a 'radio', 'select-one' or 'button-radio' question")
            enum_name = f"AnswerChoice_{id_}"
            options = {f"option_{i}": option for i, option in enumerate(answer_choices)}
            AnswerChoiceEnum = Enum(enum_name, options)
            answer_type = AnswerChoiceEnum
        else:
            raise ValueError(f"Unsupported question type: {qtype}. At the moment botex only supports 'text', 'textarea', 'float', 'number', 'radio', 'select-one', and 'button-radio' question types. Please consider raising an issue on the GitHub repository. https://github.com/joachim-gassen/botex/issues")
        
        field_type = create_model(
            f"Answer_{id_}",
            reason=(str, Field(
                ...,
                description=f"contains your reasoning or thought that leads you to a response or answer on the question: {qlabel}"
            )),
            answer=(answer_type, Field(
                ...,
                description=f"Your final answer to the question: {qlabel}"
            )),
            __base__=AnswerBase
        )

        answer_fields[id_] = (field_type, Field(..., description=f"Answer for question ID {id_}"))

    
    Answers = create_model(
        'Answers',
        **answer_fields,
        __base__=BaseModel
    )
    
    class Response(BaseModel):
        answers: Answers = Field(..., description="Your answers to all the questions")
        summary: str = Field(
            ...,
            description="Your summary of the content of the page, what you learn from it about the survey/experiment that you are participating in, all questions and your answers."
        )
        confused: bool = Field(..., description="Whether you are confused by your task or any part of the instructions. Set to true if you are confused, false otherwise.")

        @field_validator('summary')
        def summary_must_not_be_empty(cls, v):
            if not v.strip():
                raise ValueError("Summary must not be empty")
            return v

        @field_validator('confused', mode='before')
        def validate_field1(cls, value):
            return convert_string_to_boolean(value)


    return Response
