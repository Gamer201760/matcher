"""
Integration tests for CLI with UUID conversion.

Tests that the CLI properly handles UUID objects throughout the system.
"""

import unittest
from uuid import UUID, uuid4
from unittest.mock import Mock, patch, MagicMock


class TestCLIUUIDIntegration(unittest.TestCase):
    """Test CLI UUID handling."""

    def test_uuid_str_round_trip(self):
        """Test that UUID can be converted to string and back."""
        original_uuid = uuid4()
        uuid_str = str(original_uuid)
        recovered_uuid = UUID(uuid_str)
        
        self.assertEqual(original_uuid, recovered_uuid)
        self.assertEqual(str(original_uuid), uuid_str)
    
    def test_uuid_parsing_from_database(self):
        """Test parsing UUID strings from database."""
        # Simulate database returning string IDs
        db_ids = [str(uuid4()) for _ in range(5)]
        
        # Convert to UUID objects
        uuid_objects = [UUID(id_str) for id_str in db_ids]
        
        # Verify conversion works
        self.assertEqual(len(uuid_objects), 5)
        for uuid_obj in uuid_objects:
            self.assertIsInstance(uuid_obj, UUID)
        
        # Verify can convert back
        back_to_strings = [str(uuid_obj) for uuid_obj in uuid_objects]
        self.assertEqual(db_ids, back_to_strings)
    
    def test_uuid_in_dictionary(self):
        """Test using UUID in dictionaries (like user data)."""
        user_id = uuid4()
        user_data = {
            'id': user_id,
            'name': 'Test User',
            'rooms': 2,
            'roommates': 1,
            'budget': 15000,
            'months': 12
        }
        
        # Verify UUID is stored correctly
        self.assertIsInstance(user_data['id'], UUID)
        self.assertEqual(user_data['id'], user_id)
        
        # Verify can convert to string for database
        user_data_for_db = {**user_data, 'id': str(user_data['id'])}
        self.assertIsInstance(user_data_for_db['id'], str)


class TestUsecaseUUIDCompatibility(unittest.TestCase):
    """Test that usecases work with UUID objects."""
    
    def test_usecase_accepts_uuid(self):
        """Test that usecases accept UUID parameters."""
        from usecase.form import FormService
        from entity.parameters import Parameters, Sex, UserType
        from entity.point import Point
        from unittest.mock import Mock
        
        # Setup
        mock_form_repo = Mock()
        mock_group_repo = Mock()
        service = FormService(mock_form_repo, mock_group_repo)
        
        test_uuid = uuid4()
        test_params = Parameters(
            name='Test', surname='User', geo=Point(lat=55.7558, lon=37.6173),
            address='Test Address', photos=[], budget=15000, room_count=2, roommates_count=1, month=12,
            age=25, smoking=False, alko=False, pet=False, sex=Sex.MALE,
            user_type=UserType.WORKER, description='Test'
        )
        
        # Execute - should not raise type error
        service.create(test_uuid, test_params)
        
        # Verify called with UUID
        mock_form_repo.create.assert_called_once()
        call_args = mock_form_repo.create.call_args[0][0]
        self.assertIsInstance(call_args.user_id, UUID)
        self.assertEqual(call_args.user_id, test_uuid)


if __name__ == '__main__':
    unittest.main()

