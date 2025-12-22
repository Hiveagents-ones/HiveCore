# API Documentation

## Overview

This document provides detailed information about the APIs used in the membership renewal system. The system supports multiple membership packages (monthly, quarterly, yearly) and processes payments through a secure gateway.

## Base URL

```
https://api.example.com/v1
```

## Authentication

All API requests must include a valid JWT token in the Authorization header:

```
Authorization: Bearer <your_jwt_token>
```

## Security Considerations

1. **Token Validation**: All requests are validated using JWT tokens. Tokens must be obtained from the authentication endpoint.
2. **Rate Limiting**: Payment endpoints are rate-limited to 5 requests per hour per user.
3. **HTTPS Only**: All API communications must be over HTTPS.
4. **Input Validation**: All inputs are validated and sanitized to prevent injection attacks.
5. **CORS**: Cross-Origin Resource Sharing is configured to allow only trusted domains.

## Performance Metrics

1. **Response Time**: All API endpoints are designed to respond within 200ms under normal load.
2. **Throughput**: The system can handle up to 1000 requests per second.
3. **Monitoring**: Prometheus metrics are collected for all API endpoints:
   - `payment_requests_total`: Total payment requests by method and status
   - `payment_request_duration_seconds`: Request duration histogram
4. **Caching**: Redis is used for caching frequently accessed data and rate limiting.

## Endpoints

### Payment Endpoints

#### Create Payment Order

**POST** `/payment/create`

Creates a new payment order for membership renewal.

**Headers:**
- `Authorization: Bearer <token>` (required)

**Request Body:**
```json
{
  "order_id": "string",
  "amount": "number",
  "currency": "string" (optional, default: "CNY"),
  "subject": "string" (optional, default: "Membership Renewal"),
  "return_url": "string" (optional),
  "notify_url": "string" (optional)
}
```

**Response:**
```json
{
  "success": "boolean",
  "transaction_id": "string",
  "payment_url": "string",
  "message": "string"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Payment gateway error

**Example Request:**
```bash
curl -X POST "https://api.example.com/v1/payment/create" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "ORD123456",
    "amount": 99.99,
    "currency": "CNY",
    "subject": "Annual Membership"
  }'
```

**Example Response:**
```json
{
  "success": true,
  "transaction_id": "TXN789012",
  "payment_url": "https://payment.gateway.com/pay/TXN789012",
  "message": "Payment order created successfully"
}
```

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": "object" (optional)
  }
}
```

Common error codes:
- `INVALID_TOKEN`: The provided JWT token is invalid
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `PAYMENT_FAILED`: Payment gateway error
- `VALIDATION_ERROR`: Invalid input parameters

## Monitoring

The system exposes Prometheus metrics at `/metrics` endpoint. Key metrics include:

1. **Request Count**: Total number of API requests
2. **Request Duration**: Histogram of request processing times
3. **Error Rate**: Number of failed requests
4. **Active Connections**: Current number of active connections

## Rate Limiting

Payment endpoints are rate-limited to prevent abuse:
- 5 requests per hour per user
- 100 requests per minute per IP
- 1000 requests per second globally

Rate limit status is returned in headers:
```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 4
X-RateLimit-Reset: 1640995200
```

## Webhooks

The system supports webhooks for payment notifications:

**POST** `/payment/notify`

Receives asynchronous payment notifications from the payment gateway.

**Security:**
- Webhook requests are signed using HMAC-SHA256
- Signature is verified using the shared secret

**Request Headers:**
- `X-Signature`: HMAC signature of the request body

**Request Body:**
```json
{
  "transaction_id": "string",
  "status": "string",
  "amount": "number",
  "currency": "string",
  "timestamp": "string"
}
```

## SDKs

Official SDKs are available for:
- JavaScript/TypeScript
- Python
- Java
- Go

## Support

For API support, contact:
- Email: api-support@example.com
- Documentation: https://docs.example.com
- Status Page: https://status.example.com