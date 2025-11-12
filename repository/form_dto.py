from uuid import UUID

from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point


def db_form_to_form(db_dict: dict, user_id: UUID) -> Form:
    """
    Convert database dictionary to Form entity.

    Maps database fields to Parameters entity with defaults for missing fields.

    Args:
        db_dict: Dictionary from database
        user_id: User ID

    Returns:
        Form: Form entity
    """
    # Create Parameters with available data and defaults for missing fields
    parameters = Parameters(  # Вынести в отдельную общую функцию с group_dto
        name=db_dict.get('name', ''),
        surname='',  # Not stored in DB
        geo=Point(0.0, 0.0),  # Not stored in DB
        photos=[],  # Not stored in DB
        budget=db_dict.get('budget', 0),
        room_count=db_dict.get('rooms', 0),
        roommates_count=db_dict.get('roommates', 0),
        month=db_dict.get('month', 0),
        age=0,  # Not stored in DB
        smoking=False,  # Not stored in DB
        alko=False,  # Not stored in DB
        pet=False,  # Not stored in DB
        sex=Sex.MALE,  # Not stored in DB
        user_type=UserType.STUDENT,  # Not stored in DB
        description='',  # Not stored in DB
    )

    return Form(
        user_id=user_id,
        parameters=parameters,
        active=True,  # Assume active if exists
    )
