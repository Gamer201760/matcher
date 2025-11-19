"""
Data Transfer Objects for converting between entity.Parameters and database representations.

This module provides centralized conversion functions for Parameters:
- PARAMETERS fields (rooms, roommates, budget, months) are stored as separate Parameter nodes
- All other Parameters fields are stored as metadata on User/Group nodes
"""

from uuid import UUID

from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from infrastructure.config import PARAMETERS


# Mapping between Parameters entity field names and database field names
PARAMETER_DB_MAPPING = {
    'room_count': 'rooms',
    'roommates_count': 'roommates',
    'budget': 'budget',
    'month': 'months',
}

# Reverse mapping for reading from database
DB_PARAMETER_MAPPING = {v: k for k, v in PARAMETER_DB_MAPPING.items()}


def parameters_to_db_dict(parameters: Parameters, include_id: str = None) -> dict:
    """
    Convert Parameters entity to database dictionary format.
    
    Converts Parameters fields to database format:
    - PARAMETERS fields: rooms, roommates, budget, months (stored as nodes)
    - Metadata fields: name, surname, geo, photos, age, smoking, alko, pet, sex, user_type, description
    
    Args:
        parameters: Parameters entity to convert
        include_id: Optional ID to include in the dict (user_id or group_id)
    
    Returns:
        dict: Database-compatible dictionary with all fields
    """
    db_dict = {}
    
    # Add ID if provided
    if include_id:
        db_dict['id'] = include_id
    
    # Map PARAMETERS fields (these become Parameter nodes)
    db_dict['rooms'] = parameters.room_count
    db_dict['roommates'] = parameters.roommates_count
    db_dict['budget'] = parameters.budget
    db_dict['months'] = parameters.month
    
    # Add metadata fields (these become properties on User/Group node)
    db_dict['name'] = parameters.name
    db_dict['surname'] = parameters.surname
    db_dict['geo_lat'] = parameters.geo.lat
    db_dict['geo_lon'] = parameters.geo.lon
    db_dict['photos'] = parameters.photos  # Will be stored as list/json
    db_dict['age'] = parameters.age
    db_dict['smoking'] = parameters.smoking
    db_dict['alko'] = parameters.alko
    db_dict['pet'] = parameters.pet
    db_dict['sex'] = parameters.sex.value  # Store enum value
    db_dict['user_type'] = parameters.user_type.value  # Store enum value
    db_dict['description'] = parameters.description
    
    return db_dict


def db_dict_to_parameters(db_dict: dict) -> Parameters:
    """
    Convert database dictionary to Parameters entity.
    
    Reads from:
    - PARAMETERS fields: rooms, roommates, budget, months
    - Metadata fields: name, surname, geo, photos, age, smoking, alko, pet, sex, user_type, description
    
    Provides sensible defaults for missing fields.
    Handles type conversions to ensure compatibility between database types and Python types.
    
    Args:
        db_dict: Dictionary from database with both node properties and parameters
    
    Returns:
        Parameters: Parameters entity with all fields populated
    """
    # Extract and convert PARAMETERS fields to int (Neo4j may return floats)
    room_count = int(db_dict.get('rooms', 0))
    roommates_count = int(db_dict.get('roommates', 0))
    budget = int(db_dict.get('budget', 0))
    month = int(db_dict.get('months', 0))
    geo_lat = float(db_dict.get('geo_lat', 0.0))
    geo_lon = float(db_dict.get('geo_lon', 0.0))
    geo = Point(geo_lat, geo_lon)
    age = int(db_dict.get('age', 0))

    name = str(db_dict.get('name', ''))
    surname = str(db_dict.get('surname', ''))
    photos = db_dict.get('photos', [])
    
    smoking = bool(db_dict.get('smoking', False))
    alko = bool(db_dict.get('alko', False))
    pet = bool(db_dict.get('pet', False))
    
    sex_value = db_dict.get('sex', Sex.MALE.value)
    try:
        sex = Sex(int(sex_value))
    except (ValueError, TypeError):
        sex = Sex.MALE
    
    user_type_value = db_dict.get('user_type', UserType.STUDENT.value)
    try:
        user_type = UserType(int(user_type_value))
    except (ValueError, TypeError):
        user_type = UserType.STUDENT
    
    description = str(db_dict.get('description', ''))
    
    return Parameters(
        name=name,
        surname=surname,
        geo=geo,
        photos=photos,
        budget=budget,
        room_count=room_count,
        roommates_count=roommates_count,
        month=month,
        age=age,
        smoking=smoking,
        alko=alko,
        pet=pet,
        sex=sex,
        user_type=user_type,
        description=description,
    )


def db_form_to_form(db_dict: dict, user_id: UUID) -> Form:
    """
    Convert database dictionary to Form entity.
    
    Args:
        db_dict: Dictionary from database
        user_id: User ID
    
    Returns:
        Form: Form entity
    """
    parameters = db_dict_to_parameters(db_dict)
    
    return Form(
        user_id=user_id,
        parameters=parameters,
        active=True,  # Assume active if exists
    )
