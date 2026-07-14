class RepositoryError(Exception):
    """Base exception for all repository errors."""
    pass

class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found in the database."""
    pass

class DatabaseOperationError(RepositoryError):
    """Raised when a generic database operation fails."""
    pass

class TransactionError(RepositoryError):
    """Raised when a database transaction fails to commit or rollback."""
    pass
