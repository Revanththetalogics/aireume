# Platform Admin Authentication Flow

<cite>
**Referenced Files in This Document**
- [auth.py](file://app/backend/middleware/auth.py)
- [auth.py](file://app/backend/routes/auth.py)
- [admin.py](file://app/backend/routes/admin.py)
- [db_models.py](file://app/backend/models/db_models.py)
- [AuthContext.jsx](file://app/frontend/src/contexts/AuthContext.jsx)
- [PlatformAdminRoute.jsx](file://app/frontend/src/components/PlatformAdminRoute.jsx)
- [AdminLayout.jsx](file://app/frontend/src/layouts/AdminLayout.jsx)
- [impersonation_service.py](file://app/backend/services/impersonation_service.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture Overview](#system-architecture-overview)
3. [Authentication Components](#authentication-components)
4. [Platform Admin Authentication Flow](#platform-admin-authentication-flow)
5. [Token Management](#token-management)
6. [Authorization and RBAC](#authorization-and-rbac)
7. [Frontend Authentication Integration](#frontend-authentication-integration)
8. [Security Features](#security-features)
9. [Error Handling and Validation](#error-handling-and-validation)
10. [Troubleshooting Guide](#troubleshooting-guide)

## Introduction

The Platform Admin Authentication Flow is a comprehensive security system designed for the Resume AI platform that manages authentication, authorization, and administrative access control. This system ensures secure access to platform-level administrative functions while maintaining robust security measures against unauthorized access attempts.

The authentication system implements industry-standard JWT (JSON Web Token) authentication with additional security layers including token revocation, rate limiting, impersonation capabilities, and comprehensive audit logging. The system supports both tenant-level and platform-level administrative functions with granular role-based access control.

## System Architecture Overview

The authentication system follows a layered architecture pattern with clear separation of concerns between frontend presentation, backend authentication middleware, and database persistence layers.

```mermaid
graph TB
subgraph "Frontend Layer"
FE1[React Frontend]
FE2[AuthContext]
FE3[PlatformAdminRoute]
FE4[AdminLayout]
end
subgraph "Backend Layer"
BE1[FastAPI Backend]
BE2[Auth Middleware]
BE3[Admin Routes]
BE4[Auth Routes]
end
subgraph "Database Layer"
DB1[PostgreSQL Database]
DB2[Users Table]
DB3[Tenants Table]
DB4[Revoked Tokens]
DB5[Audit Logs]
end
subgraph "External Services"
ES1[JWT Provider]
ES2[Email Service]
ES3[Security Events]
end
FE1 --> FE2
FE2 --> FE3
FE3 --> FE4
FE4 --> BE1
BE1 --> BE2
BE1 --> BE3
BE1 --> BE4
BE2 --> DB1
BE3 --> DB1
BE4 --> DB1
DB1 --> DB2
DB1 --> DB3
DB1 --> DB4
DB1 --> DB5
BE2 --> ES1
BE4 --> ES2
BE2 --> ES3
```

**Diagram sources**
- [auth.py:1-247](file://app/backend/middleware/auth.py#L1-L247)
- [auth.py:1-517](file://app/backend/routes/auth.py#L1-L517)
- [admin.py:1-800](file://app/backend/routes/admin.py#L1-L800)

## Authentication Components

### JWT Authentication Middleware

The authentication middleware provides centralized JWT token validation and user loading functionality. It supports both bearer token authentication for API clients and cookie-based authentication for browser clients.

```mermaid
classDiagram
class JWTAuthMiddleware {
+get_current_user() User
+require_platform_admin() User
+require_admin() User
+require_active_subscription() User
-_load_user_from_token() User
-_check_platform_role() User
}
class User {
+int id
+string email
+string role
+bool is_active
+bool is_platform_admin
+string platform_role
+Tenant tenant
}
class Tenant {
+int id
+string name
+string slug
+string subscription_status
+SubscriptionPlan plan
}
class RevokedToken {
+int id
+string jti
+datetime expires_at
}
JWTAuthMiddleware --> User : loads
User --> Tenant : belongs to
JWTAuthMiddleware --> RevokedToken : validates against
```

**Diagram sources**
- [auth.py:57-145](file://app/backend/middleware/auth.py#L57-L145)
- [db_models.py:77-99](file://app/backend/models/db_models.py#L77-L99)
- [db_models.py:33-75](file://app/backend/models/db_models.py#L33-L75)

**Section sources**
- [auth.py:1-247](file://app/backend/middleware/auth.py#L1-L247)
- [db_models.py:77-99](file://app/backend/models/db_models.py#L77-L99)

### Authentication Routes

The authentication routes handle user registration, login, token refresh, logout, and password management. These routes implement comprehensive security measures including rate limiting, email verification, and secure token generation.

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant AuthRoutes as "Auth Routes"
participant DB as "Database"
participant Email as "Email Service"
Client->>AuthRoutes : POST /api/auth/register
AuthRoutes->>DB : Create Tenant
AuthRoutes->>DB : Create User
AuthRoutes->>Email : Send Verification Email
AuthRoutes->>AuthRoutes : Generate Access Token
AuthRoutes->>AuthRoutes : Generate Refresh Token
AuthRoutes->>Client : Set HttpOnly Cookies
Client->>AuthRoutes : POST /api/auth/login
AuthRoutes->>DB : Verify Credentials
AuthRoutes->>DB : Check Email Verification
AuthRoutes->>AuthRoutes : Generate New Tokens
AuthRoutes->>Client : Set HttpOnly Cookies
```

**Diagram sources**
- [auth.py:175-314](file://app/backend/routes/auth.py#L175-L314)

**Section sources**
- [auth.py:1-517](file://app/backend/routes/auth.py#L1-L517)

## Platform Admin Authentication Flow

### Admin User Registration and Verification

The platform admin authentication flow begins with user registration and verification processes that establish secure administrative accounts.

```mermaid
flowchart TD
Start([Admin Registration]) --> ValidateInput["Validate Registration Input"]
ValidateInput --> CheckEmail["Check Email Uniqueness"]
CheckEmail --> HashPassword["Hash Password"]
HashPassword --> CreateTenant["Create Tenant Record"]
CreateTenant --> CreateAdminUser["Create Admin User"]
CreateAdminUser --> SendVerification["Send Email Verification"]
SendVerification --> GenerateTokens["Generate Access & Refresh Tokens"]
GenerateTokens --> SetCookies["Set HttpOnly Cookies"]
SetCookies --> Redirect["Redirect to Dashboard"]
Redirect --> End([Registration Complete])
```

**Diagram sources**
- [auth.py:175-250](file://app/backend/routes/auth.py#L175-L250)

### Login and Authentication Process

The login process implements multiple security layers including rate limiting, credential verification, and email verification checks.

```mermaid
sequenceDiagram
participant Client as "Client"
participant AuthRoutes as "Auth Routes"
participant Security as "Security Service"
participant DB as "Database"
participant Token as "JWT Service"
Client->>AuthRoutes : POST /api/auth/login
AuthRoutes->>Security : Rate Limit Check
Security-->>AuthRoutes : Allow/Deny
AuthRoutes->>DB : Verify Credentials
DB-->>AuthRoutes : User Found/Not Found
AuthRoutes->>DB : Check Email Verification
AuthRoutes->>DB : Check SSO Enforcement
AuthRoutes->>Token : Generate Access Token
Token-->>AuthRoutes : Access Token
AuthRoutes->>Token : Generate Refresh Token
Token-->>AuthRoutes : Refresh Token
AuthRoutes->>Client : Set HttpOnly Cookies
AuthRoutes->>Security : Record Successful Login
```

**Diagram sources**
- [auth.py:264-314](file://app/backend/routes/auth.py#L264-L314)

**Section sources**
- [auth.py:264-314](file://app/backend/routes/auth.py#L264-L314)

### Token Refresh and Rotation

The token refresh mechanism provides secure session management with proper token rotation and revocation handling.

```mermaid
flowchart TD
RefreshRequest[Refresh Request] --> ExtractToken["Extract Refresh Token"]
ExtractToken --> ValidateToken["Validate JWT Signature"]
ValidateToken --> CheckType{"Token Type = Refresh?"}
CheckType --> |No| InvalidToken[Return 401 Invalid Token]
CheckType --> |Yes| CheckRevoked["Check JTI in Revoked Tokens"]
CheckRevoked --> Revoked{"Revoked?"}
Revoked --> |Yes| ReturnRevoked[Return 401 Token Revoked]
Revoked --> |No| CheckUser["Check User Exists"]
CheckUser --> UserActive{"User Active?"}
UserActive --> |No| DeactivateUser[Return 401 User Deactivated]
UserActive --> |Yes| GenerateNewTokens["Generate New Access & Refresh Tokens"]
GenerateNewTokens --> ReturnTokens[Return New Tokens]
```

**Diagram sources**
- [auth.py:317-366](file://app/backend/routes/auth.py#L317-L366)

**Section sources**
- [auth.py:317-366](file://app/backend/routes/auth.py#L317-L366)

## Token Management

### JWT Token Structure and Claims

The authentication system uses JWT tokens with standardized claims for user identification, tenant association, and token type specification.

| Claim | Type | Description | Required |
|-------|------|-------------|----------|
| `sub` | String | User identifier (UUID) | Yes |
| `tenant_id` | String | Tenant identifier | Yes |
| `type` | String | Token type (access/refresh) | No |
| `jti` | String | JWT ID (unique) | Yes |
| `exp` | Number | Expiration timestamp | Yes |

### Token Storage and Security

Tokens are securely stored using HttpOnly cookies to prevent XSS attacks while supporting both browser and API client authentication scenarios.

```mermaid
graph LR
subgraph "Token Storage"
TS1[HttpOnly Cookies]
TS2[Secure Flag]
TS3[SameSite=Lax]
TS4[CSRF Protection]
end
subgraph "Token Types"
TT1[Access Token]
TT2[Refresh Token]
TT3[Impersonation Token]
end
subgraph "Security Measures"
SM1[JWT Secret Key]
SM2[Token Expiration]
SM3[Revocation List]
SM4[Rate Limiting]
end
TS1 --> TT1
TS1 --> TT2
TS1 --> TT3
TT1 --> SM1
TT2 --> SM1
TT3 --> SM1
```

**Diagram sources**
- [auth.py:124-170](file://app/backend/routes/auth.py#L124-L170)
- [auth.py:15-28](file://app/backend/middleware/auth.py#L15-L28)

**Section sources**
- [auth.py:124-170](file://app/backend/routes/auth.py#L124-L170)
- [auth.py:15-28](file://app/backend/middleware/auth.py#L15-L28)

## Authorization and RBAC

### Platform-Level Roles and Permissions

The platform implements a hierarchical role-based access control (RBAC) system with five distinct platform administrator roles, each with specific permissions and capabilities.

```mermaid
graph TD
subgraph "Platform Admin Roles"
RA[ReadOnly Admin]
SA[Support Admin]
BA[Billing Admin]
SEA[Security Admin]
SAA[Super Admin]
end
subgraph "Role Permissions"
RA --> R1[Read-only access]
SA --> S1[Support functions]
SA --> R1
BA --> B1[Billing operations]
BA --> R1
SEA --> SE1[Security monitoring]
SEA --> R1
SAA --> ALL[Full platform access]
SAA --> BA
SAA --> SA
SAA --> SEA
SAA --> RA
end
subgraph "Legacy Support"
LS[Legacy is_platform_admin]
LS --> SAA
end
```

**Diagram sources**
- [auth.py:32-52](file://app/backend/middleware/auth.py#L32-L52)
- [auth.py:184-228](file://app/backend/middleware/auth.py#L184-L228)

### Tenant-Level vs Platform-Level Access

The system distinguishes between tenant-level administrative functions and platform-level administrative functions, with platform admins having elevated privileges across all tenants.

| Access Level | Description | Scope | Examples |
|--------------|-------------|-------|----------|
| Tenant Admin | Standard tenant administrator | Single tenant | Manage users, plans, billing |
| Platform Admin | Platform-wide administrator | All tenants | Tenant management, system config |
| Super Admin | Highest platform privilege | Full system control | Create/delete tenants, system config |
| Support Admin | Customer support access | Limited platform functions | User assistance, ticket management |
| Billing Admin | Financial operations | Billing and payments | Payment processing, invoices |

**Section sources**
- [auth.py:32-52](file://app/backend/middleware/auth.py#L32-L52)
- [auth.py:184-228](file://app/backend/middleware/auth.py#L184-L228)

## Frontend Authentication Integration

### Authentication Context and State Management

The frontend implements comprehensive authentication state management through React Context, providing seamless authentication integration across the admin interface.

```mermaid
sequenceDiagram
participant App as "React App"
participant AuthCtx as "AuthContext"
participant API as "API Client"
participant AuthRoute as "PlatformAdminRoute"
participant AdminLayout as "AdminLayout"
App->>AuthCtx : Initialize Auth Context
AuthCtx->>API : GET /auth/me
API-->>AuthCtx : User Data
AuthCtx->>AuthRoute : Check Platform Admin
AuthRoute->>AuthRoute : Validate is_platform_admin
AuthRoute->>AdminLayout : Render Admin Interface
AdminLayout->>AuthRoute : Route Protected Content
AuthRoute->>App : Render Children
```

**Diagram sources**
- [AuthContext.jsx:14-49](file://app/frontend/src/contexts/AuthContext.jsx#L14-L49)
- [PlatformAdminRoute.jsx:4-19](file://app/frontend/src/components/PlatformAdminRoute.jsx#L4-L19)

### Protected Route Implementation

The platform admin route protection ensures that only authorized platform administrators can access sensitive administrative interfaces.

```mermaid
flowchart TD
RouteAccess[Route Access Attempt] --> CheckAuth[Check Authentication Status]
CheckAuth --> Authenticated{"User Authenticated?"}
Authenticated --> |No| RedirectHome[Redirect to Home]
Authenticated --> |Yes| CheckPlatformAdmin[Check Platform Admin]
CheckPlatformAdmin --> IsPlatformAdmin{"is_platform_admin?"}
IsPlatformAdmin --> |No| RedirectHome
IsPlatformAdmin --> |Yes| RenderChildren[Render Protected Content]
RedirectHome --> End[Access Denied]
RenderChildren --> End[Access Granted]
```

**Diagram sources**
- [PlatformAdminRoute.jsx:4-19](file://app/frontend/src/components/PlatformAdminRoute.jsx#L4-L19)

**Section sources**
- [AuthContext.jsx:1-112](file://app/frontend/src/contexts/AuthContext.jsx#L1-L112)
- [PlatformAdminRoute.jsx:1-20](file://app/frontend/src/components/PlatformAdminRoute.jsx#L1-L20)
- [AdminLayout.jsx:1-298](file://app/frontend/src/layouts/AdminLayout.jsx#L1-L298)

## Security Features

### Rate Limiting and Brute Force Protection

The authentication system implements comprehensive rate limiting mechanisms to prevent brute force attacks and abuse of authentication endpoints.

```mermaid
flowchart TD
Request[Authentication Request] --> RateLimit[Rate Limit Check]
RateLimit --> CheckAttempts{"Within Window?"}
CheckAttempts --> |No| AllowRequest[Allow Request]
CheckAttempts --> |Yes| CountAttempts[Count Attempts]
CountAttempts --> MaxReached{"Max Attempts Reached?"}
MaxReached --> |Yes| BlockRequest[Block Request - 429]
MaxReached --> |No| AllowRequest
BlockRequest --> WaitTime[Calculate Wait Time]
WaitTime --> RetryAfter[Return Retry-After Header]
AllowRequest --> ProcessRequest[Process Authentication]
```

**Diagram sources**
- [auth.py:45-74](file://app/backend/routes/auth.py#L45-L74)

### Token Revocation and Logout

The logout process implements proper token revocation by adding refresh tokens to a revocation list, preventing their reuse even after expiration.

```mermaid
sequenceDiagram
participant Client as "Client"
participant AuthRoutes as "Auth Routes"
participant DB as "Database"
participant Security as "Security Service"
Client->>AuthRoutes : POST /api/auth/logout
AuthRoutes->>AuthRoutes : Extract Refresh Token
AuthRoutes->>AuthRoutes : Decode JWT Payload
AuthRoutes->>DB : Check JTI in Revoked Tokens
DB-->>AuthRoutes : Not Found
AuthRoutes->>DB : Add JTI to Revoked Tokens
AuthRoutes->>DB : Clear HttpOnly Cookies
AuthRoutes->>Security : Record Logout Event
AuthRoutes->>Client : Success Response
```

**Diagram sources**
- [auth.py:378-421](file://app/backend/routes/auth.py#L378-L421)

**Section sources**
- [auth.py:45-74](file://app/backend/routes/auth.py#L45-L74)
- [auth.py:378-421](file://app/backend/routes/auth.py#L378-L421)

### Impersonation Capabilities

Platform administrators can impersonate tenant users for support and debugging purposes through secure impersonation sessions.

```mermaid
flowchart TD
AdminAction[Admin Action] --> CreateSession[Create Impersonation Session]
CreateSession --> GenerateToken[Generate Secure Token]
GenerateToken --> StoreHash[Store SHA-256 Hash]
StoreHash --> SetExpiry[Set Expiration Time]
SetExpiry --> NotifyAdmin[Notify Admin]
UserRequest[User Request] --> ValidateToken[Validate Impersonation Token]
ValidateToken --> CheckActive{"Active & Not Expired?"}
CheckActive --> |No| InvalidToken[Return 401]
CheckActive --> |Yes| LoadTargetUser[Load Target User]
LoadTargetUser --> SetImpersonation[Set Impersonation Context]
SetImpersonation --> ProcessRequest[Process Request as User]
AdminAction --> RevokeSession[Revoke Session]
RevokeSession --> SetRevoked[Set Revoked Timestamp]
SetRevoked --> PreventReuse[Prevent Future Use]
```

**Diagram sources**
- [impersonation_service.py:17-41](file://app/backend/services/impersonation_service.py#L17-L41)
- [auth.py:109-138](file://app/backend/middleware/auth.py#L109-L138)

**Section sources**
- [impersonation_service.py:1-109](file://app/backend/services/impersonation_service.py#L1-L109)
- [auth.py:109-138](file://app/backend/middleware/auth.py#L109-L138)

## Error Handling and Validation

### Comprehensive Error Responses

The authentication system provides detailed error responses with appropriate HTTP status codes and error messages for different failure scenarios.

| Error Scenario | HTTP Status | Error Code | Description |
|----------------|-------------|------------|-------------|
| Invalid Credentials | 401 | INVALID_CREDENTIALS | Username/password combination invalid |
| Email Not Verified | 403 | EMAIL_NOT_VERIFIED | User email requires verification |
| Account Suspended | 403 | ACCOUNT_SUSPENDED | Tenant account suspended |
| Invalid Token | 401 | INVALID_TOKEN | JWT token invalid or expired |
| Token Revoked | 401 | TOKEN_REVOKED | Token has been revoked |
| Too Many Requests | 429 | TOO_MANY_REQUESTS | Rate limit exceeded |
| Access Denied | 403 | ACCESS_DENIED | Insufficient permissions |

### Input Validation and Sanitization

The system implements comprehensive input validation and sanitization to prevent injection attacks and ensure data integrity.

**Section sources**
- [auth.py:264-314](file://app/backend/routes/auth.py#L264-L314)
- [auth.py:57-84](file://app/backend/middleware/auth.py#L57-L84)

## Troubleshooting Guide

### Common Authentication Issues

#### Issue: Users Cannot Login
**Symptoms**: Login returns 401 Unauthorized
**Possible Causes**:
- Invalid email/password combination
- Account deactivated or suspended
- Email verification required
- SSO enforced by tenant configuration

**Resolution Steps**:
1. Verify user credentials are correct
2. Check if account is active and not suspended
3. Ensure email verification is complete
4. Verify SSO configuration for tenant

#### Issue: Token Expires Too Soon
**Symptoms**: Frequent logout despite recent activity
**Possible Causes**:
- Access token expiration too short
- Network latency causing token validation failures
- Clock synchronization issues

**Resolution Steps**:
1. Check ACCESS_TOKEN_EXPIRE_MINUTES environment variable
2. Verify system clock synchronization
3. Review network latency affecting token validation

#### Issue: Admin Access Denied
**Symptoms**: Platform admin routes return 403 Forbidden
**Possible Causes**:
- User lacks platform admin privileges
- Legacy is_platform_admin flag not set
- Platform role not properly configured

**Resolution Steps**:
1. Verify user has is_platform_admin = true
2. Check platform_role field is set appropriately
3. Confirm user belongs to platform admin group

#### Issue: Impersonation Session Fails
**Symptoms**: Impersonation token returns 401
**Possible Causes**:
- Token expired or revoked
- Session not found in database
- Target user deactivated

**Resolution Steps**:
1. Generate new impersonation token
2. Verify session is not expired or revoked
3. Check target user account status

**Section sources**
- [auth.py:264-314](file://app/backend/routes/auth.py#L264-L314)
- [auth.py:109-145](file://app/backend/middleware/auth.py#L109-L145)
- [impersonation_service.py:44-56](file://app/backend/services/impersonation_service.py#L44-L56)