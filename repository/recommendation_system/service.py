from dataclasses import dataclass
from typing import List, Tuple, Optional
from uuid import UUID
from db_management_utils import (
    get_driver,
    ensure_constraints_and_index,
    upsert_users,
    remove_user_from_group,
    get_user_form,
    delete_user_form,
    send_join_request,
    approve_join_request,
    get_group_with_status,
    find_similar_users,
    PARAMETERS,
)
from user_vector_utils import (
    group_parameter_weights,
)


@dataclass
class GroupMembers:
    """Represents a group member relationship."""
    group_id: UUID
    form_id: UUID


@dataclass
class Group:
    """Represents a group of roommates."""
    group_id: UUID
    roommates: int
    active: bool


@dataclass
class Form:
    """Represents a user's form/profile for matching."""
    user_id: str
    name: Optional[str] = None
    rooms: int = 0
    roommates: int = 0
    budget: int = 0
    months: int = 1


class RecommendationService:
    """Service for managing forms, groups, and recommendations."""

    def __init__(self, caps=None, use_weights=True, weights=None):
        """
        Initialize the recommendation service.
        
        Args:
            caps: Normalization caps for vector creation (default: {'budget': 200000, 'months': 36})
            use_weights: Whether to use weighted vectors for groups
            weights: Parameter weights for group vector creation
        """
        self.caps = caps or {'budget': 200000, 'months': 36}
        self.use_weights = use_weights
        self.weights = weights or group_parameter_weights
        self.driver = get_driver()
        
        # Ensure database schema is initialized
        with self.driver.session() as session:
            ensure_constraints_and_index(session, dims=len(PARAMETERS))

    # Form Management Methods
    
    def create_form(self, user_id: UUID, form: Form) -> None:
        """
        Create a new form for a user.
        
        Args:
            user_id: The user's unique identifier
            form: The form data to create
        """
        user_data = {
            'id': str(user_id),
            'name': form.name,
            'rooms': form.rooms,
            'roommates': form.roommates,
            'budget': form.budget,
            'months': form.months,
        }
        
        with self.driver.session() as session:
            upsert_users(
                session, 
                [user_data], 
                caps=self.caps, 
                use_weights=self.use_weights, 
                weights=self.weights
            )

    def get_form(self, user_id: UUID) -> Form:
        """
        Retrieve a user's form.
        
        Args:
            user_id: The user's unique identifier
            
        Returns:
            The user's form
        """
        with self.driver.session() as session:
            user_data = get_user_form(session, str(user_id))
            
            if not user_data:
                raise ValueError(f"User {user_id} not found")
            
            return Form(
                user_id=user_data['id'],
                name=user_data['name'],
                rooms=user_data.get('rooms', 0),
                roommates=user_data.get('roommates', 0),
                budget=user_data.get('budget', 0),
                months=user_data.get('months', 1),
            )

    def get_similar(self, user_id: UUID, top_k: int = 5) -> List[Tuple[Form, float]]:
        """
        Get similar forms/users based on matching algorithm.
        
        Args:
            user_id: The user's unique identifier
            top_k: Number of similar users to return
            
        Returns:
            List of tuples containing (form, similarity_score)
        """
        with self.driver.session() as session:
            similar_users = find_similar_users(
                session, 
                str(user_id), 
                top_k, 
                self.caps, 
                self.use_weights, 
                self.weights
            )
            
            results = []
            for user_data in similar_users:
                form = self.get_form(user_data['user_id'])
                results.append((form, user_data['score']))
            
            return results

    def update_form(self, user_id: UUID, form: Form) -> None:
        """
        Update an existing user's form.
        
        Args:
            user_id: The user's unique identifier
            form: The updated form data
        """
        # Upsert will update if exists
        user_data = {
            'id': str(user_id),
            'name': form.name,
            'rooms': form.rooms,
            'roommates': form.roommates,
            'budget': form.budget,
            'months': form.months,
        }
        
        with self.driver.session() as session:
            upsert_users(
                session, 
                [user_data], 
                caps=self.caps, 
                use_weights=self.use_weights, 
                weights=self.weights
            )

    def delete_form(self, user_id: UUID) -> None:
        """
        Delete a user's form.
        
        Args:
            user_id: The user's unique identifier
        """
        with self.driver.session() as session:
            delete_user_form(session, str(user_id))

    # Group Management Methods
    
    def send_request_to_group(self, user_id: UUID, group_id: UUID) -> None:
        """
        Send a request from a user to join a group.
        
        Args:
            user_id: The user who wants to join the group
            group_id: The target group identifier
        """
        with self.driver.session() as session:
            send_join_request(session, str(user_id), str(group_id))

    def approve_request(self, group_member_user_id: UUID, user_id: UUID, max_roommates: int = 4) -> None:
        """
        Approve a user's request to join the group.
        
        Args:
            group_member_user_id: The user who is already in the group and approves
            user_id: The user being approved to join
            max_roommates: Maximum number of roommates allowed in a group
            
        Note:
            When group reaches max_roommates, the group should become inactive
            for recommendations.
        """
        with self.driver.session() as session:
            success = approve_join_request(
                session,
                str(group_member_user_id),
                str(user_id),
                max_roommates,
                self.caps,
                self.use_weights,
                self.weights
            )
            
            if not success:
                raise RuntimeError(f"Failed to approve request for user {user_id}")

    def leave_from_group(self, user_id: UUID) -> None:
        """
        Remove a user from their current group.
        
        Args:
            user_id: The user leaving the group
        """
        with self.driver.session() as session:
            new_group_id = remove_user_from_group(
                session, 
                str(user_id), 
                caps=self.caps, 
                use_weights=self.use_weights, 
                weights=self.weights
            )
            
            if not new_group_id:
                raise RuntimeError(f"Failed to remove user {user_id} from group")

    def get_group(self, group_id: UUID) -> Tuple[Group, List[str]]:
        """
        Get group details and its members.
        
        Args:
            group_id: The group identifier
            
        Returns:
            Tuple containing (group details, list of member user IDs)
        """
        with self.driver.session() as session:
            group_data = get_group_with_status(session, str(group_id))
            
            if not group_data:
                raise ValueError(f"Group {group_id} not found")
            
            group = Group(
                group_id=group_data['id'],
                roommates=group_data['roommates'],
                active=group_data['active']
            )
            
            return (group, group_data['member_ids'])
    
    def close(self):
        """Close the database driver connection."""
        if self.driver:
            self.driver.close()
