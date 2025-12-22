# Security Configuration

This document outlines the security measures and configurations for the Course Booking System.

## Authentication

### Password Hashing
- Passwords are hashed using `bcrypt` via the `get_password_hash` function in `backend/app/core/security.py`.
- Password verification is performed using the `verify_password` function.

### JWT Tokens
- Access tokens are created using the `create_access_token` function.
- Tokens are verified using the `verify_token` function.
- Tokens must be included in the `Authorization` header as `Bearer <token>` for protected endpoints.

## Authorization

### Protected Endpoints
- All API endpoints under `/api/v1/` are protected and require a valid JWT token.
- Unauthorized access attempts will result in a `401 Unauthorized` response.

### Role-Based Access Control
- Currently, all authenticated users have the same level of access.
- Future enhancements may include role-based access control for different user types (e.g., admin, member).

## Data Protection

### Database Security
- The database connection is configured using SQLAlchemy with secure connection strings.
- Sensitive data, such as passwords, are never stored in plain text.

### API Security
- Input validation is performed using Pydantic models to prevent injection attacks.
- CORS is configured to allow only specified origins.

## Testing

### Security Tests
- Security tests are located in `tests/security/security_test.py`.
- Tests cover password hashing, token creation/verification, and protected endpoint access.

### Example Test Cases
- `test_password_hashing`: Verifies that passwords are correctly hashed and verified.
- `test_token_creation_and_verification`: Ensures JWT tokens are created and verified correctly.
- `test_protected_endpoint_without_token`: Confirms that accessing protected endpoints without a token returns `401`.
- `test_protected_endpoint_with_valid_token`: Validates that valid tokens grant access to protected endpoints.
- `test_protected_endpoint_with_invalid_token`: Ensures invalid tokens are rejected with a `401` response.

## Best Practices

- Regularly update dependencies to mitigate vulnerabilities.
- Use environment variables for sensitive configuration (e.g., secret keys).
- Enable HTTPS in production to protect data in transit.
- Implement rate limiting to prevent brute-force attacks.
- Log and monitor security events for suspicious activity.

## References
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)