"""
Logging configuration for the Neo4j Roommate Recommendation System.

Provides structured logging with different levels:
- DEBUG: Technical details, query execution, vector operations
- INFO: User-facing messages, progress updates, results
- WARNING: Non-critical issues, fallbacks
- ERROR: Critical failures, connection issues
"""

import logging
import sys
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logger(name: str = "roommate_system", level: str = "INFO") -> logging.Logger:
    """
    Set up a logger with console output and optional file output.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Prevent duplicate handlers if logger is already configured
    if logger.handlers:
        return logger
    
    # Set level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    console_formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


def setup_file_logger(name: str = "roommate_system", 
                     filename: str = "roommate_system.log",
                     level: str = "DEBUG") -> logging.Logger:
    """
    Set up a logger with both console and file output.
    
    Args:
        name: Logger name
        filename: Log file name
        level: Logging level for file output
        
    Returns:
        Configured logger instance with file handler
    """
    logger = setup_logger(name)
    
    # Check if file handler already exists
    file_handler_exists = any(
        isinstance(handler, logging.FileHandler) for handler in logger.handlers
    )
    
    if not file_handler_exists:
        # Create file handler
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(getattr(logging, level.upper(), logging.DEBUG))
        
        # Create detailed formatter for file
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    return logger


def log_neo4j_query(logger: logging.Logger, query: str, parameters: Optional[dict] = None):
    """
    Log a Neo4j query with parameters at DEBUG level.
    
    Args:
        logger: Logger instance
        query: Cypher query string
        parameters: Query parameters dictionary
    """
    logger.debug("Executing Neo4j query:")
    logger.debug(f"Query: {query.strip()}")
    if parameters:
        # Mask sensitive data
        safe_params = {k: v if k not in ['password', 'auth'] else '***' for k, v in parameters.items()}
        logger.debug(f"Parameters: {safe_params}")


def log_vector_operation(logger: logging.Logger, operation: str, vector_size: int, user_id: str = None):
    """
    Log vector operations at DEBUG level.
    
    Args:
        logger: Logger instance
        operation: Description of the vector operation
        vector_size: Size of the vector
        user_id: Optional user ID for context
    """
    context = f" for user {user_id}" if user_id else ""
    logger.debug(f"Vector operation: {operation}{context} (vector size: {vector_size})")


def log_similarity_results(logger: logging.Logger, query_user: str, results: list, top_k: int):
    """
    Log similarity search results at DEBUG level.
    
    Args:
        logger: Logger instance
        query_user: ID of the query user
        results: List of similarity results
        top_k: Number of top results requested
    """
    logger.debug(f"Similarity search for user {query_user}:")
    logger.debug(f"Requested top-{top_k}, found {len(results)} results")
    for i, result in enumerate(results[:3]):  # Log first 3 for debugging
        score = result.get('score', 0)
        result_id = result.get('id', 'unknown')
        logger.debug(f"  {i+1}. {result_id}: {score:.4f}")


def log_database_stats(logger: logging.Logger, stats: dict):
    """
    Log database operation statistics at INFO level.
    
    Args:
        logger: Logger instance
        stats: Dictionary containing statistics (nodes_created, relationships_created, etc.)
    """
    if stats:
        logger.info("Database operation completed:")
        for key, value in stats.items():
            if value > 0:
                logger.info(f"  {key.replace('_', ' ').title()}: {value}")


# Global logger instance for easy access
default_logger = setup_logger()


if __name__ == "__main__":
    # Test the logging system
    logger = setup_logger("test_logger", "DEBUG")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test specialized logging functions
    log_neo4j_query(logger, "MATCH (n:User) RETURN n", {"limit": 10})
    log_vector_operation(logger, "Creating user vector", 4, "user123")
    log_similarity_results(logger, "user1", [
        {"id": "user2", "score": 0.85},
        {"id": "user3", "score": 0.72}
    ], 5)
    log_database_stats(logger, {"nodes_created": 5, "relationships_created": 3})
    
    print("\n✅ Logging system test completed!")
