"""
Database connection and infrastructure management for Neo4j.

This module handles:
- Database driver creation and connection
- Constraints and indexes setup
- Database cleanup operations
"""

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
import os
import dotenv

from ..logging_utils import setup_logger, log_neo4j_query, log_database_stats
from ..config import SIMILARITY_FUNCTION

dotenv.load_dotenv()

# Setup logger
logger = setup_logger("roommate_db", "INFO")


def get_driver(uri=None, user=None, password=None):
    """
    Create and return a Neo4j driver instance.
    
    Args:
        uri: Database URI (defaults to NEO4J_URI env var)
        user: Database username (defaults to NEO4J_USERNAME env var)
        password: Database password (defaults to NEO4J_PASSWORD env var)
        
    Returns:
        Neo4j Driver instance
    """
    uri = uri or os.getenv('NEO4J_URI')
    user = user or os.getenv('NEO4J_USERNAME')
    password = password or os.getenv('NEO4J_PASSWORD')
    return GraphDatabase.driver(uri, auth=(user, password))


def ensure_constraints_and_index(session, dims):
    """Ensure required constraints and vector indexes exist for User and Group nodes."""
    logger.debug(f"Setting up database constraints and indexes for {dims}-dimensional vectors")
    
    try:
        # Ensure a unique id constraint for Users (proper Neo4j syntax)
        constraint_query = """
            CREATE CONSTRAINT user_id_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.id IS UNIQUE
        """
        log_neo4j_query(logger, constraint_query)
        session.run(constraint_query)
        logger.info("✓ User ID uniqueness constraint ensured")
        
        # Ensure a unique constraint for Parameter nodes per (userId, name)
        param_constraint_query = """
            CREATE CONSTRAINT parameter_unique IF NOT EXISTS
            FOR (p:Parameter) REQUIRE (p.userId, p.name) IS UNIQUE
        """
        log_neo4j_query(logger, param_constraint_query)
        session.run(param_constraint_query)
        logger.info("✓ Parameter uniqueness constraint ensured (userId, name)")

        # Ensure a unique id constraint for Groups
        group_constraint_query = """
            CREATE CONSTRAINT group_id_unique IF NOT EXISTS
            FOR (g:Group) REQUIRE g.id IS UNIQUE
        """
        log_neo4j_query(logger, group_constraint_query)
        session.run(group_constraint_query)
        logger.info("✓ Group ID uniqueness constraint ensured")

        # Ensure a unique constraint for GroupParameter (groupId, name)
        gparam_constraint_query = """
            CREATE CONSTRAINT group_parameter_unique IF NOT EXISTS
            FOR (p:GroupParameter) REQUIRE (p.groupId, p.name) IS UNIQUE
        """
        log_neo4j_query(logger, gparam_constraint_query)
        session.run(gparam_constraint_query)
        logger.info("✓ GroupParameter uniqueness constraint ensured (groupId, name)")
        
        # Check if vector index exists
        index_check_query = """
            SHOW INDEXES
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE type = 'VECTOR' AND entityType = 'NODE'
              AND 'User' IN labelsOrTypes AND 'embedding' IN properties
            RETURN name LIMIT 1
        """
        log_neo4j_query(logger, index_check_query)
        result = session.run(index_check_query)
        
        if result.peek() is None:
            # Create vector index for User.embedding using new syntax
            index_create_query = f"""
                CREATE VECTOR INDEX user_vec_index IF NOT EXISTS
                FOR (u:User) ON (u.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: $dims,
                    `vector.similarity_function`: '{SIMILARITY_FUNCTION}'
                }}}}
            """
            log_neo4j_query(logger, index_create_query, {"dims": dims})
            session.run(index_create_query, dims=dims)
            logger.info(f"✓ Vector index 'user_vec_index' created with {dims} dimensions")
        else:
            logger.info("✓ Vector index already exists")
            logger.debug("Skipping vector index creation - index already present")

        # Check if GROUP vector index exists
        gindex_check_query = """
            SHOW INDEXES
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE type = 'VECTOR' AND entityType = 'NODE'
              AND 'Group' IN labelsOrTypes AND 'embedding' IN properties
            RETURN name LIMIT 1
        """
        log_neo4j_query(logger, gindex_check_query)
        gresult = session.run(gindex_check_query)

        if gresult.peek() is None:
            gindex_create_query = f"""
                CREATE VECTOR INDEX group_vec_index IF NOT EXISTS
                FOR (g:Group) ON (g.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: $dims,
                    `vector.similarity_function`: '{SIMILARITY_FUNCTION}'
                }}}}
            """
            log_neo4j_query(logger, gindex_create_query, {"dims": dims})
            session.run(gindex_create_query, dims=dims)
            logger.info(f"✓ Vector index 'group_vec_index' created with {dims} dimensions")
        else:
            logger.info("✓ Group vector index already exists")
            logger.debug("Skipping group vector index creation - index already present")
            
    except Neo4jError as e:
        logger.warning(f"Could not ensure constraints/indexes: {e}")
        logger.debug("Continuing execution - constraints might already exist")
        # Continue execution - constraints might already exist


def clean_db():
    """Clean the entire database after user confirmation."""
    logger.warning("Database cleaning requested - this will delete ALL data")
    confirmation = input("⚠️  This will delete ALL data in the database. Are you sure? (type 'YES' to confirm): ")
    
    if confirmation != 'YES':
        logger.info("Database cleaning cancelled by user")
        return False
        
    logger.info("Starting complete database cleanup...")
    
    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Delete all nodes and relationships
                delete_query = "MATCH (n) DETACH DELETE n"
                log_neo4j_query(logger, delete_query)
                session.run(delete_query)
                logger.info("✓ All nodes and relationships deleted")
                
                # Drop all indexes (except built-in ones)
                indexes_query = """
                    SHOW INDEXES
                    YIELD name, type
                    WHERE type = 'VECTOR'
                    RETURN name
                """
                log_neo4j_query(logger, indexes_query)
                indexes_result = session.run(indexes_query)
                
                dropped_indexes = 0
                for record in indexes_result:
                    index_name = record['name']
                    try:
                        drop_index_query = f"DROP INDEX {index_name}"
                        log_neo4j_query(logger, drop_index_query)
                        session.run(drop_index_query)
                        logger.info(f"✓ Dropped index: {index_name}")
                        dropped_indexes += 1
                    except Neo4jError as e:
                        logger.debug(f"Could not drop index {index_name}: {e}")
                
                # Drop all constraints
                constraints_query = """
                    SHOW CONSTRAINTS
                    YIELD name
                    RETURN name
                """
                log_neo4j_query(logger, constraints_query)
                constraints_result = session.run(constraints_query)
                
                dropped_constraints = 0
                for record in constraints_result:
                    constraint_name = record['name']
                    try:
                        drop_constraint_query = f"DROP CONSTRAINT {constraint_name}"
                        log_neo4j_query(logger, drop_constraint_query)
                        session.run(drop_constraint_query)
                        logger.info(f"✓ Dropped constraint: {constraint_name}")
                        dropped_constraints += 1
                    except Neo4jError as e:
                        logger.debug(f"Could not drop constraint {constraint_name}: {e}")
                        
                logger.info("✅ Database cleaned successfully!")
                log_database_stats(logger, {
                    "indexes_dropped": dropped_indexes,
                    "constraints_dropped": dropped_constraints
                })
                return True
                
    except Exception as e:
        logger.error(f"Error cleaning database: {e}")
        return False


def check_neo4j_connection():
    """
    Check if Neo4j database is running and accessible.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Simple query to test connection
                result = session.run("RETURN 'Neo4j is running' as message")
                record = result.single()
                if record and record['message'] == 'Neo4j is running':
                    logger.info("✅ Neo4j database connection verified")
                    return True
    except Exception as e:
        logger.error(f"❌ Neo4j database connection failed: {e}")
        return False

    logger.error("❌ Neo4j database connection failed: Unknown error")
    return False

