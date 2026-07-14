class AuthenticationError(Exception):
    """Base exception for authentication and authorization errors."""
    pass

class InvalidCredentialsError(AuthenticationError):
    """Raised when email or password is incorrect."""
    pass

class TokenValidationError(AuthenticationError):
    """Raised when a JWT is malformed, invalid, or blacklisted."""
    pass

class ExpiredTokenError(TokenValidationError):
    """Raised when a JWT has expired."""
    pass

class AuthorizationError(AuthenticationError):
    """Raised when a user lacks required permissions."""
    pass

class ExamManagementError(Exception):
    """Base exception for exam management errors."""
    pass

class ExamNotFoundError(ExamManagementError):
    """Raised when an exam is not found."""
    pass

class InvalidExamStateError(ExamManagementError):
    """Raised when an invalid state transition is attempted."""
    pass

class QuestionPaperError(ExamManagementError):
    """Raised when a question paper operation fails (e.g., file not found)."""
    pass

class ScheduleConflictError(ExamManagementError):
    """Raised when an exam schedule conflicts with another exam."""
    pass

class AISessionError(ExamManagementError):
    """Raised when AI Session orchestration fails."""
    pass

class MonitoringError(Exception):
    """Base exception for monitoring operations."""
    pass

class WebSocketError(MonitoringError):
    """Raised when a WebSocket operation fails."""
    pass

class ConnectionManagerError(MonitoringError):
    """Raised when a connection manager operation fails."""
    pass

class EvidenceNotFoundError(MonitoringError):
    """Raised when evidence is not found."""
    pass

class ViolationNotFoundError(MonitoringError):
    """Raised when a violation is not found."""
    pass

class StudentRegistrationError(Exception):
    """Base exception for student registration."""
    pass

class CredentialGenerationError(StudentRegistrationError):
    pass

class EmailDeliveryError(StudentRegistrationError):
    pass

class DuplicateStudentError(StudentRegistrationError):
    pass

class InvalidExamError(StudentRegistrationError):
    pass
