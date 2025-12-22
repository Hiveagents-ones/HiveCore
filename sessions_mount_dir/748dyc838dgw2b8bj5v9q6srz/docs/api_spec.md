# API Specification

## Members API

### Register Member

**Endpoint**: `POST /api/v1/members/register`

**Description**: Registers a new member using phone number or email. Generates a membership card upon successful registration.

**Request Body**:
```json
{
  "email": "user@example.com",
  "phone": "+1234567890",
  "password": "securepassword"
}
```
*Note: At least one of `email` or `phone` must be provided.*

**Success Response**:
`HTTP 201 Created`
```json
{
  "id": "mbr_12345",
  "email": "user@example.com",
  "phone": "+1234567890",
  "membership_card": "CARD_987654"
}
```

**Error Responses**:
- `400 Bad Request`: Missing required fields or invalid format (e.g., invalid email format).
- `409 Conflict`: Email or phone already registered.

**Example Request**:
```bash
curl -X 'POST' \
  'http://api.example.com/api/v1/members/register' \
  -H 'Content-Type: application/json' \
  -d '{\"email\": \"user@example.com\", \"password\": \"securepassword\"}'
```