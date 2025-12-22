# API Specification: Membership and Payment

This document outlines the API endpoints for managing membership plans, subscriptions, and processing payments.

## Base URL

```
/api/v1
```

## Authentication

Most endpoints require authentication. Include the authentication token in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

## Endpoints

### Membership Plans

#### Create a New Membership Plan

- **Endpoint:** `POST /members/plans/`
- **Description:** Creates a new membership plan.
- **Authentication:** Required (Admin role recommended).
- **Request Body:** `schemas.MembershipPlanCreate`
  ```json
  {
    "name": "string",
    "description": "string",
    "price": "number",
    "duration_months": "integer",
    "is_active": "boolean"
  }
  ```
- **Success Response (201 Created):** `schemas.MembershipPlan`
  ```json
  {
    "id": "integer",
    "name": "string",
    "description": "string",
    "price": "number",
    "duration_months": "integer",
    "is_active": "boolean",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```

#### Update a Membership Plan

- **Endpoint:** `PUT /members/plans/{plan_id}`
- **Description:** Updates an existing membership plan.
- **Authentication:** Required (Admin role recommended).
- **Path Parameters:**
  - `plan_id` (integer): The ID of the plan to update.
- **Request Body:** `schemas.MembershipPlanUpdate`
  ```json
  {
    "name": "string (optional)",
    "description": "string (optional)",
    "price": "number (optional)",
    "duration_months": "integer (optional)",
    "is_active": "boolean (optional)"
  }
  ```
- **Success Response (200 OK):** `schemas.MembershipPlan`
- **Error Response (404 Not Found):**
  ```json
  {
    "detail": "Membership plan not found"
  }
  ```

#### Delete a Membership Plan

- **Endpoint:** `DELETE /members/plans/{plan_id}`
- **Description:** Deletes a membership plan.
- **Authentication:** Required (Admin role recommended).
- **Path Parameters:**
  - `plan_id` (integer): The ID of the plan to delete.
- **Success Response (204 No Content):** No content.
- **Error Response (404 Not Found):**
  ```json
  {
    "detail": "Membership plan not found"
  }
  ```

#### Retrieve All Membership Plans

- **Endpoint:** `GET /members/plans/`
- **Description:** Retrieves a list of all active membership plans.
- **Authentication:** Not required.
- **Query Parameters:**
  - `skip` (integer, optional): Number of records to skip for pagination. Default: 0.
  - `limit` (integer, optional): Maximum number of records to return. Default: 100.
- **Success Response (200 OK):** List of `schemas.MembershipPlan`
  ```json
  [
    {
      "id": "integer",
      "name": "string",
      "description": "string",
      "price": "number",
      "duration_months": "integer",
      "is_active": "boolean",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ]
  ```

#### Retrieve a Specific Membership Plan

- **Endpoint:** `GET /members/plans/{plan_id}`
- **Description:** Retrieves details of a specific membership plan.
- **Authentication:** Not required.
- **Path Parameters:**
  - `plan_id` (integer): The ID of the plan to retrieve.
- **Success Response (200 OK):** `schemas.MembershipPlan`
- **Error Response (404 Not Found):**
  ```json
  {
    "detail": "Membership plan not found"
  }
  ```

### Subscriptions

#### Create a New Subscription Record

- **Endpoint:** `POST /members/subscribe/`
- **Description:** Creates a new subscription record for a user. This is typically called internally after a successful payment.
- **Authentication:** Required.
- **Request Body:** `schemas.SubscriptionRecordCreate`
  ```json
  {
    "user_id": "integer",
    "plan_id": "integer",
    "start_date": "date",
    "end_date": "date",
    "amount_paid": "number"
  }
  ```
- **Success Response (201 Created):** `schemas.SubscriptionRecord`
  ```json
  {
    "id": "integer",
    "user_id": "integer",
    "plan_id": "integer",
    "start_date": "date",
    "end_date": "date",
    "amount_paid": "number",
    "created_at": "datetime"
  }
  ```
- **Error Response (400 Bad Request):**
  ```json
  {
    "detail": "Error message from validation"
  }
  ```

#### Retrieve User Subscriptions

- **Endpoint:** `GET /members/subscriptions/{user_id}`
- **Description:** Retrieves all subscription records for a specific user.
- **Authentication:** Required.
- **Path Parameters:**
  - `user_id` (integer): The ID of the user.
- **Query Parameters:**
  - `skip` (integer, optional): Number of records to skip for pagination. Default: 0.
  - `limit` (integer, optional): Maximum number of records to return. Default: 100.
- **Success Response (200 OK):** List of `schemas.SubscriptionRecord`
  ```json
  [
    {
      "id": "integer",
      "user_id": "integer",
      "plan_id": "integer",
      "start_date": "date",
      "end_date": "date",
      "amount_paid": "number",
      "created_at": "datetime"
    }
  ]
  ```

### Payments

#### Create a Payment Order

- **Endpoint:** `POST /payments/create-payment`
- **Description:** Initiates a payment for a membership plan.
- **Authentication:** Required.
- **Request Body:** `application/x-www-form-urlencoded`
  - `plan_id` (integer): The ID of the membership plan to purchase.
  - `payment_method` (string): The payment method (e.g., 'alipay', 'wechat').
- **Success Response (200 OK):** `schemas.PaymentOrder`
  ```json
  {
    "order_id": "string",
    "user_id": "integer",
    "plan_id": "integer",
    "amount": "number",
    "status": "string",
    "payment_method": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```
- **Error Response (404 Not Found):**
  ```json
  {
    "detail": "Membership plan not found"
  }
  ```
- **Error Response (400 Bad Request):**
  ```json
  {
    "detail": "Error message from validation"
  }
  ```

#### Payment Callback

- **Endpoint:** `POST /payments/payment-callback`
- **Description:** Handles asynchronous callbacks from payment gateways to notify the system of a payment's status.
- **Authentication:** Not required (but should be secured by verifying the source of the callback).
- **Request Body:** `application/json`
  ```json
  {
    "order_id": "string",
    "transaction_id": "string",
    "status": "string"
  }
  ```
- **Success Response (200 OK):**
  ```json
  {
    "status": "success",
    "message": "Payment processed successfully"
  }
  ```
  or
  ```json
  {
    "status": "failed",
    "message": "Payment processing failed"
  }
  ```
- **Error Response (400 Bad Request):**
  ```json
  {
    "detail": "Missing required field: order_id"
  }
  ```
- **Error Response (500 Internal Server Error):**
  ```json
  {
    "detail": "Internal server error"
  }
  ```

#### Get Payment Status

- **Endpoint:** `GET /payments/payment-status/{order_id}`
- **Description:** Allows a user to check the status of their payment order.
- **Authentication:** Required.
- **Path Parameters:**
  - `order_id` (string): The unique ID of the payment order.
- **Success Response (200 OK):** `schemas.PaymentOrder`
  ```json
  {
    "order_id": "string",
    "user_id": "integer",
    "plan_id": "integer",
    "amount": "number",
    "status": "string",
    "payment_method": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
  ```
- **Error Response (404 Not Found):**
  ```json
  {
    "detail": "Payment order not found"
  }
  ```

## Data Models (Schemas)

### MembershipPlan

| Field            | Type      | Description                     |
|------------------|-----------|---------------------------------|
| id               | integer   | Unique identifier for the plan. |
| name             | string    | Name of the plan (e.g., '月卡'). |
| description      | string    | Detailed description of the plan.|
| price            | number    | Cost of the plan.               |
| duration_months  | integer   | Duration of the plan in months. |
| is_active        | boolean   | Whether the plan is currently active. |
| created_at       | datetime  | Timestamp when the plan was created. |
| updated_at       | datetime  | Timestamp when the plan was last updated. |

### SubscriptionRecord

| Field            | Type      | Description                     |
|------------------|-----------|---------------------------------|
| id               | integer   | Unique identifier for the record.|
| user_id          | integer   | ID of the user who subscribed.  |
| plan_id          | integer   | ID of the plan subscribed to.   |
| start_date       | date      | Start date of the subscription period. |
| end_date         | date      | End date of the subscription period. |
| amount_paid      | number    | Amount paid for this subscription. |
| created_at       | datetime  | Timestamp when the record was created. |

### PaymentOrder

| Field            | Type      | Description                     |
|------------------|-----------|---------------------------------|
| order_id         | string    | Unique identifier for the payment order. |
| user_id          | integer   | ID of the user making the payment. |
| plan_id          | integer   | ID of the plan being purchased. |
| amount           | number    | Total amount for the payment.   |
| status           | string    | Status of the payment (e.g., 'pending', 'paid', 'failed'). |
| payment_method   | string    | Method used for payment (e.g., 'alipay'). |
| created_at       | datetime  | Timestamp when the order was created. |
| updated_at       | datetime  | Timestamp when the order was last updated. |
