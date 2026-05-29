# User Management

<cite>
**Referenced Files in This Document**
- [db_models.py](file://app/backend/models/db_models.py)
- [schemas.py](file://app/backend/models/schemas.py)
- [auth.py](file://app/backend/middleware/auth.py)
- [auth_routes.py](file://app/backend/routes/auth.py)
- [team_routes.py](file://app/backend/routes/team.py)
- [admin_routes.py](file://app/backend/routes/admin.py)
- [UsersPage.jsx](file://app/frontend/src/pages/admin/UsersPage.jsx)
- [AuthContext.jsx](file://app/frontend/src/contexts/AuthContext.jsx)
- [api.js](file://app/frontend/src/lib/api.js)
</cite>

## Update Summary
**Changes Made**
- Enhanced error handling documentation with extractApiError() utility function
- Updated pagination implementation details to reflect 100 items per page optimization
- Added comprehensive error handling patterns and user-friendly error messaging
- Updated frontend integration documentation with improved error handling practices

## Table of Contents
1. [Introduction](#introduction)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Authentication and Authorization](#authentication-and-authorization)
5. [User Management Features](#user-management-features)
6. [Advanced User Management Capabilities](#advanced-user-management-capabilities)
7. [Multi-Tenant Architecture](#multi-tenant-architecture)
8. [Security Implementation](#security-implementation)
9. [Frontend Integration](#frontend-integration)
10. [API Endpoints](#api-endpoints)
11. [Best Practices and Guidelines](#best-practices-and-guidelines)

## Introduction

The User Management system in Resume AI by ThetaLogics provides comprehensive user lifecycle management across a multi-tenant SaaS platform. This system handles user authentication, authorization, tenant membership management, and administrative oversight capabilities. The platform serves as an AI-powered resume analysis and candidate screening solution, requiring robust user management to support both individual users within organizations and platform administrators.

The system is built on a modern tech stack featuring FastAPI for the backend, React for the frontend, PostgreSQL for data persistence, and JWT-based authentication with comprehensive security measures including rate limiting, CSRF protection, and token revocation.

## System Architecture

The User Management system follows a layered architecture with clear separation of concerns:

```mermaid
graph TB
subgraph "Frontend Layer"
UI[React Frontend]
AuthCtx[Auth Context]
API[API Client]
UsersPage[Users Management Page]
end
subgraph "Backend Layer"
subgraph "Routes Layer"
AuthRoutes[Authentication Routes]
TeamRoutes[Team Routes]
AdminRoutes[Admin Routes]
end
subgraph "Middleware Layer"
AuthMW[Authentication Middleware]
RBAC[Role-Based Access Control]
Security[Security Middleware]
end
subgraph "Services Layer"
AuthSvc[Authentication Service]
TeamSvc[Team Service]
AdminSvc[Admin Service]
end
subgraph "Data Layer"
Models[Database Models]
DB[(PostgreSQL)]
end
end
UI --> AuthCtx
AuthCtx --> API
API --> UsersPage
API --> AuthRoutes
API --> TeamRoutes
API --> AdminRoutes
UsersPage --> AdminRoutes
AuthRoutes --> AuthMW
TeamRoutes --> AuthMW
AdminRoutes --> AuthMW
AuthMW --> RBAC
RBAC --> Security
AuthRoutes --> AuthSvc
TeamRoutes --> TeamSvc
AdminRoutes --> AdminSvc
AuthSvc --> Models
TeamSvc --> Models
AdminSvc --> Models
Models --> DB
```

**Diagram sources**
- [auth_routes.py:1-517](file://app/backend/routes/auth.py#L1-L517)
- [team_routes.py:1-295](file://app/backend/routes/team.py#L1-L295)
- [admin_routes.py:1-800](file://app/backend/routes/admin.py#L1-L800)

## Core Components

### Database Model Architecture

The user management system is built around several core database models that define the relationships and constraints:

```mermaid
classDiagram
class User {
+integer id
+integer tenant_id
+string email
+string hashed_password
+string role
+boolean is_active
+boolean is_platform_admin
+string platform_role
+datetime created_at
+boolean email_verified
+string email_verification_token
+datetime email_verification_sent_at
+tenant Tenant
+team_member TeamMember
+usage_logs UsageLog
}
class Tenant {
+integer id
+string name
+string slug
+integer plan_id
+string subscription_status
+datetime current_period_start
+datetime current_period_end
+integer analyses_count_this_month
+bigint storage_used_bytes
+datetime usage_reset_at
+string stripe_customer_id
+string stripe_subscription_id
+datetime subscription_updated_at
+datetime suspended_at
+string suspended_reason
+datetime deleted_at
+string scoring_weights
+boolean onboarding_completed
+datetime onboarding_completed_at
+subscription_plan SubscriptionPlan
+users User[]
+candidates Candidate[]
+templates RoleTemplate[]
+results ScreeningResult[]
+team_members TeamMember[]
+usage_logs UsageLog[]
+email_config TenantEmailConfig
+sso_config SSOConfig
}
class TeamMember {
+integer id
+integer tenant_id
+integer user_id
+string role
+tenant Tenant
+user User
}
class UsageLog {
+integer id
+integer tenant_id
+integer user_id
+string action
+integer quantity
+text details
+datetime created_at
+tenant Tenant
+user User
}
class RevokedToken {
+integer id
+string jti
+datetime revoked_at
+datetime expires_at
}
class PasswordResetToken {
+integer id
+integer user_id
+string token
+datetime created_at
+datetime expires_at
+user User
}
User --> Tenant : belongs to
TeamMember --> User : belongs to
TeamMember --> Tenant : belongs to
UsageLog --> User : belongs to
UsageLog --> Tenant : belongs to
RevokedToken --> User : user deactivation
PasswordResetToken --> User : belongs to
```

**Diagram sources**
- [db_models.py:77-124](file://app/backend/models/db_models.py#L77-L124)
- [db_models.py:33-75](file://app/backend/models/db_models.py#L33-L75)
- [db_models.py:267-277](file://app/backend/models/db_models.py#L267-L277)
- [db_models.py:110-124](file://app/backend/models/db_models.py#L110-L124)
- [db_models.py:396-415](file://app/backend/models/db_models.py#L396-L415)

### Authentication Schema Definitions

The system uses Pydantic models for request/response validation:

```mermaid
classDiagram
class RegisterRequest {
+string company_name
+string email
+string password
}
class LoginRequest {
+string email
+string password
}
class TokenResponse {
+string access_token
+string refresh_token
+string token_type
+dict user
+dict tenant
}
class RefreshRequest {
+string refresh_token
}
class UserOut {
+integer id
+string email
+string role
+integer tenant_id
}
RegisterRequest --> LoginRequest : related
TokenResponse --> UserOut : contains
```

**Diagram sources**
- [schemas.py:237-268](file://app/backend/models/schemas.py#L237-L268)
- [schemas.py:248-254](file://app/backend/models/schemas.py#L248-L254)

**Section sources**
- [db_models.py:77-124](file://app/backend/models/db_models.py#L77-L124)
- [schemas.py:237-268](file://app/backend/models/schemas.py#L237-L268)

## Authentication and Authorization

### JWT-Based Authentication Flow

The authentication system implements a comprehensive JWT-based security model with multiple layers of protection:

```mermaid
sequenceDiagram
participant Client as "Client Application"
participant AuthRoute as "Auth Routes"
participant AuthMW as "Auth Middleware"
participant DB as "Database"
participant Security as "Security Services"
Client->>AuthRoute : POST /api/auth/register
AuthRoute->>AuthRoute : Hash Password
AuthRoute->>DB : Create Tenant + Admin User
AuthRoute->>AuthRoute : Generate JWT Tokens
AuthRoute->>Client : Set httpOnly Cookies + Response
Client->>AuthRoute : POST /api/auth/login
AuthRoute->>DB : Verify Credentials
AuthRoute->>Security : Check Email Verification
AuthRoute->>Security : Check SSO Enforcement
AuthRoute->>AuthRoute : Generate Access/Refresh Tokens
AuthRoute->>Client : Set httpOnly Cookies + Response
Client->>AuthMW : Request with Access Token
AuthMW->>DB : Decode JWT + Load User
AuthMW->>Security : Check Revoked Tokens
AuthMW->>Security : Check Tenant Suspension
AuthMW->>Client : Authorized Access
Client->>AuthRoute : POST /api/auth/refresh
AuthRoute->>DB : Verify Refresh Token
AuthRoute->>Security : Check Token Revocation
AuthRoute->>AuthRoute : Issue New Access Token
AuthRoute->>Client : Set httpOnly Cookies + Response
```

**Diagram sources**
- [auth_routes.py:175-250](file://app/backend/routes/auth.py#L175-L250)
- [auth_routes.py:264-315](file://app/backend/routes/auth.py#L264-L315)
- [auth_routes.py:317-367](file://app/backend/routes/auth.py#L317-L367)
- [auth.py:57-145](file://app/backend/middleware/auth.py#L57-L145)

### Role-Based Access Control

The system implements a hierarchical role-based access control (RBAC) system:

```mermaid
graph TD
subgraph "Tenant-Level Roles"
Admin[Admin]
Recruiter[Recruiter]
Viewer[Viewer]
end
subgraph "Platform-Level Roles"
SuperAdmin[Super Admin]
BillingAdmin[Billing Admin]
Support[Support]
SecurityAdmin[Security Admin]
ReadOnly[Read-Only]
end
subgraph "Permissions Matrix"
Admin --> TeamOps[Team Operations]
Admin --> UserMgmt[User Management]
Admin --> Billing[Subscription Management]
Recruiter --> ViewOps[View Operations]
Recruiter --> BasicAnalysis[Basic Analysis]
Viewer --> ViewOps
end
SuperAdmin --> AllOps[All Operations]
BillingAdmin --> BillingOps[Billing Operations]
Support --> SupportOps[Support Operations]
SecurityAdmin --> SecurityOps[Security Operations]
ReadOnly --> ViewOps
```

**Diagram sources**
- [auth.py:176-229](file://app/backend/middleware/auth.py#L176-L229)
- [team_routes.py:68-94](file://app/backend/routes/team.py#L68-L94)

**Section sources**
- [auth_routes.py:175-367](file://app/backend/routes/auth.py#L175-L367)
- [auth.py:176-229](file://app/backend/middleware/auth.py#L176-L229)

## User Management Features

### Team Member Management

The system provides comprehensive team member management capabilities:

```mermaid
flowchart TD
Start([Team Member Management]) --> Invite[Invite Member]
Invite --> Validate[Validate Email Uniqueness]
Validate --> CreateTemp[Create Temporary User]
CreateTemp --> GeneratePassword[Generate Temporary Password]
GeneratePassword --> StoreHash[Store Hashed Password]
StoreHash --> Notify[Send Invitation Email]
Notify --> Success[Member Added]
Success --> List[List Team Members]
Success --> Remove[Remove Member]
Success --> Update[Update Member Role]
Remove --> Deactivate[Deactivate User Account]
Update --> RoleChange[Update Role]
List --> Success
Deactivate --> Success
RoleChange --> Success
```

**Diagram sources**
- [team_routes.py:68-114](file://app/backend/routes/team.py#L68-L114)
- [team_routes.py:52-65](file://app/backend/routes/team.py#L52-L65)

### Administrative User Management

Platform administrators have extensive capabilities for managing users across tenants:

```mermaid
graph LR
subgraph "Admin User Management"
AddUser[Add User to Tenant]
RemoveUser[Remove User from Tenant]
ChangeRole[Change User Role]
SuspendTenant[Suspend Tenant]
ReactivateTenant[Reactivate Tenant]
DeleteTenant[Delete Tenant]
end
subgraph "Tenant Operations"
ListTenants[List Tenants]
ViewTenant[View Tenant Details]
ChangePlan[Change Plan]
AdjustUsage[Adjust Usage]
end
subgraph "Audit & Monitoring"
AuditLogs[Audit Logs]
SecurityEvents[Security Events]
UsageHistory[Usage History]
end
AddUser --> ListTenants
RemoveUser --> ListTenants
ChangeRole --> ListTenants
SuspendTenant --> ListTenants
ReactivateTenant --> ListTenants
DeleteTenant --> ListTenants
ViewTenant --> AuditLogs
ViewTenant --> SecurityEvents
ViewTenant --> UsageHistory
```

**Diagram sources**
- [admin_routes.py:201-276](file://app/backend/routes/admin.py#L201-L276)
- [admin_routes.py:281-363](file://app/backend/routes/admin.py#L281-L363)
- [admin_routes.py:367-434](file://app/backend/routes/admin.py#L367-L434)

**Section sources**
- [team_routes.py:68-114](file://app/backend/routes/team.py#L68-L114)
- [admin_routes.py:201-434](file://app/backend/routes/admin.py#L201-L434)

## Advanced User Management Capabilities

### Comprehensive User Management Interface

The UsersPage.jsx component provides a sophisticated user management interface with advanced filtering, sorting, and bulk action capabilities:

```mermaid
graph TB
subgraph "User Management Interface"
UsersPage[UsersPage Component]
TenantSelector[Tenant Selector]
UserFilters[Advanced Filters]
UserTable[User Table with Sorting]
BulkActions[Bulk Action Controls]
end
subgraph "User Operations"
AddUser[Add User Modal]
ChangeRole[Change Role Modal]
RemoveUser[Remove User Action]
StatusToggle[Status Toggle]
end
subgraph "Data Management"
Pagination[Pagination Controls]
Search[Search Functionality]
Export[Export Capabilities]
end
UsersPage --> TenantSelector
UsersPage --> UserFilters
UsersPage --> UserTable
UsersPage --> BulkActions
UserTable --> AddUser
UserTable --> ChangeRole
UserTable --> RemoveUser
UserTable --> StatusToggle
UserFilters --> Search
UserFilters --> Pagination
BulkActions --> Export
```

**Diagram sources**
- [UsersPage.jsx:295-649](file://app/frontend/src/pages/admin/UsersPage.jsx#L295-L649)

### Cross-Tenant User Management

The enhanced UsersPage.jsx now supports sophisticated cross-tenant user management with comprehensive filtering and role assignment controls:

```mermaid
flowchart TD
CrossTenant[Cross-Tenant Management] --> TenantSelection[Tenant Selection]
TenantSelection --> UserListing[User Listing per Tenant]
UserListing --> CrossTenantMove[Cross-Tenant User Move]
CrossTenantMove --> SuperAdminCheck[Super Admin Privilege Check]
SuperAdminCheck --> AuditLog[Audit Trail Logging]
UserListing --> RoleAssignment[Role Assignment Controls]
RoleAssignment --> PlatformRoles[Platform-Level Roles]
RoleAssignment --> TenantRoles[Tenant-Level Roles]
PlatformRoles --> SuperAdmin[Super Admin]
PlatformRoles --> BillingAdmin[Billing Admin]
PlatformRoles --> Support[Support]
PlatformRoles --> SecurityAdmin[Security Admin]
TenantRoles --> Admin[Admin]
TenantRoles --> Recruiter[Recruiter]
TenantRoles --> Viewer[Viewer]
```

**Diagram sources**
- [UsersPage.jsx:26-32](file://app/frontend/src/pages/admin/UsersPage.jsx#L26-L32)
- [admin_routes.py:969-985](file://app/backend/routes/admin.py#L969-L985)

### Enhanced Error Handling with extractApiError()

The system now implements comprehensive error handling using the extractApiError() utility function:

```mermaid
flowchart TD
ErrorHandling[Error Handling Flow] --> ApiError[API Error Response]
ApiError --> ExtractError[extractApiError Utility]
ExtractError --> StringDetail[String Detail Check]
ExtractError --> ArrayDetail[Array Detail Check]
ExtractError --> Fallback[Fallback Message]
StringDetail --> UserFriendly[User-Friendly Message]
ArrayDetail --> JoinMessages[Join Multiple Messages]
Fallback --> DefaultMessage[Default Error Message]
JoinMessages --> UserFriendly
UserFriendly --> DisplayError[Display Error to User]
DefaultMessage --> DisplayError
```

**Diagram sources**
- [api.js:1077-1085](file://app/frontend/src/lib/api.js#L1077-L1085)

### Optimized Pagination Implementation

The system now implements optimized pagination with 100 items per page for improved performance:

```mermaid
flowchart TD
Pagination[Pagination System] --> PerPage[100 Items per Page]
PerPage --> FetchTenants[Fetch Tenants with 100 per page]
FetchTenants --> LocalPagination[Local Pagination Logic]
LocalPagination --> SliceUsers[Slice Users Array]
SliceUsers --> DisplayUsers[Display Current Page]
DisplayUsers --> Navigation[Navigation Controls]
Navigation --> PageButtons[Page Buttons]
PageButtons --> NextPage[Next Page]
PageButtons --> PreviousPage[Previous Page]
NextPage --> SliceUsers
PreviousPage --> SliceUsers
```

**Diagram sources**
- [UsersPage.jsx:25](file://app/frontend/src/pages/admin/UsersPage.jsx#L25)
- [UsersPage.jsx:324](file://app/frontend/src/pages/admin/UsersPage.jsx#L324)

### Advanced Filtering and Search

The system implements comprehensive filtering capabilities with sophisticated search functionality:

```mermaid
flowchart TD
FilterStart[Filter Initialization] --> SearchFilter[Search by Email/Name]
FilterStart --> RoleFilter[Filter by Role]
FilterStart --> StatusFilter[Filter by Status]
SearchFilter --> CombinedFilter[Combined Filters]
RoleFilter --> CombinedFilter
StatusFilter --> CombinedFilter
CombinedFilter --> ApplyFilter[Apply Filters]
ApplyFilter --> Paginate[Apply Pagination]
Paginate --> Display[Display Results]
```

**Diagram sources**
- [UsersPage.jsx:369-375](file://app/frontend/src/pages/admin/UsersPage.jsx#L369-L375)

### Role Assignment Controls

The system provides granular role assignment with platform-level and tenant-level permissions:

```mermaid
graph TD
RoleAssignment[Role Assignment] --> TenantRole[Tenant Role]
RoleAssignment --> PlatformRole[Platform Role]
TenantRole --> Admin[Admin]
TenantRole --> Recruiter[Recruiter]
TenantRole --> Viewer[Viewer]
PlatformRole --> SuperAdmin[Super Admin]
PlatformRole --> BillingAdmin[Billing Admin]
PlatformRole --> Support[Support]
PlatformRole --> SecurityAdmin[Security Admin]
PlatformRole --> ReadOnly[Read-Only]
```

**Diagram sources**
- [UsersPage.jsx:26-32](file://app/frontend/src/pages/admin/UsersPage.jsx#L26-L32)

### User Status Management

The system implements comprehensive user status management with activation/deactivation capabilities:

```mermaid
stateDiagram-v2
[*] --> Active
Active --> Inactive : Deactivate User
Inactive --> Active : Reactivate User
Active --> Suspended : Tenant Suspension
Suspended --> Active : Tenant Reactivation
```

**Diagram sources**
- [UsersPage.jsx:56-66](file://app/frontend/src/pages/admin/UsersPage.jsx#L56-L66)

**Section sources**
- [UsersPage.jsx:295-649](file://app/frontend/src/pages/admin/UsersPage.jsx#L295-L649)
- [api.js:1077-1085](file://app/frontend/src/lib/api.js#L1077-L1085)

## Multi-Tenant Architecture

### Tenant Isolation and Data Segregation

The multi-tenant architecture ensures complete isolation between organizations:

```mermaid
graph TB
subgraph "Platform Level"
AdminPortal[Admin Portal]
PlatformConfig[Platform Configuration]
GlobalUsers[Global Users]
end
subgraph "Tenant Level"
subgraph "Tenant A"
TAUsers[Tenant A Users]
TACandidates[Tenant A Candidates]
TAResults[Tenant A Results]
TATemplates[Tenant A Templates]
end
subgraph "Tenant B"
TBUsers[Tenant B Users]
TBCandidates[Tenant B Candidates]
TBResults[Tenant B Results]
TBTemplates[Tenant B Templates]
end
end
AdminPortal --> TAUsers
AdminPortal --> TBUsers
AdminPortal --> PlatformConfig
TAUsers --> TACandidates
TAUsers --> TAResults
TAUsers --> TATemplates
TBUsers --> TBCandidates
TBUsers --> TBResults
TBUsers --> TBTemplates
```

**Diagram sources**
- [db_models.py:33-75](file://app/backend/models/db_models.py#L33-L75)
- [db_models.py:77-124](file://app/backend/models/db_models.py#L77-L124)

### Tenant Subscription Management

The system manages tenant subscriptions with comprehensive billing and usage tracking:

```mermaid
stateDiagram-v2
[*] --> Active
Active --> Trialing : Start Trial
Active --> Suspended : Payment Failure
Active --> Cancelled : User Cancellation
Trialing --> Active : Payment Successful
Trialing --> Cancelled : Trial Expired
Suspended --> Active : Payment Successful
Suspended --> Cancelled : Payment Failed
Cancelled --> [*]
Active --> UsageCheck : Monthly Check
UsageCheck --> Active : Within Limits
UsageCheck --> PastDue : Exceeded Limits
PastDue --> Suspended : Payment Failure
PastDue --> Active : Payment Successful
```

**Diagram sources**
- [db_models.py:42-57](file://app/backend/models/db_models.py#L42-L57)
- [admin_routes.py:367-434](file://app/backend/routes/admin.py#L367-L434)

**Section sources**
- [db_models.py:33-75](file://app/backend/models/db_models.py#L33-L75)
- [admin_routes.py:367-434](file://app/backend/routes/admin.py#L367-L434)

## Security Implementation

### Comprehensive Security Measures

The system implements multiple layers of security:

```mermaid
graph TB
subgraph "Authentication Security"
JWT[JWT Tokens]
CSRF[CSRF Protection]
RateLimit[Rate Limiting]
TokenRevocation[Token Revocation]
end
subgraph "Data Security"
Encryption[Password Hashing]
SSL[HTTPS Only]
InputValidation[Input Validation]
SQLInjection[SQL Injection Prevention]
end
subgraph "Access Control"
RBAC[Role-Based Access Control]
TenantIsolation[Tenant Isolation]
PlatformAdmin[Platform Admin]
Impersonation[Impersonation Support]
end
subgraph "Audit & Monitoring"
AuditLogs[Audit Logging]
SecurityEvents[Security Events]
SuspiciousActivity[Suspicious Activity Detection]
end
JWT --> CSRF
CSRF --> RateLimit
RateLimit --> TokenRevocation
Encryption --> SSL
SSL --> InputValidation
InputValidation --> SQLInjection
RBAC --> TenantIsolation
TenantIsolation --> PlatformAdmin
PlatformAdmin --> Impersonation
AuditLogs --> SecurityEvents
SecurityEvents --> SuspiciousActivity
```

**Diagram sources**
- [auth_routes.py:43-75](file://app/backend/routes/auth.py#L43-L75)
- [auth_routes.py:264-315](file://app/backend/routes/auth.py#L264-L315)
- [auth.py:182-229](file://app/backend/middleware/auth.py#L182-L229)

### Security Event Tracking

The system maintains comprehensive security event logs:

```mermaid
sequenceDiagram
participant User as "User Action"
participant Security as "Security Service"
participant Audit as "Audit Service"
participant DB as "Database"
User->>Security : Login Attempt
Security->>Security : Validate Credentials
Security->>Security : Check Rate Limits
Security->>Security : Check Suspicious Activity
alt Valid Login
Security->>Audit : Record Login Success
Audit->>DB : Log Success Event
else Invalid Login
Security->>Audit : Record Login Failure
Audit->>DB : Log Failure Event
Security->>Security : Check Brute Force
Security->>Audit : Record Suspicious Activity
end
User->>Security : Token Refresh
Security->>Security : Verify Token
Security->>Security : Check Revoked Tokens
Security->>Audit : Log Refresh Event
```

**Diagram sources**
- [auth_routes.py:277-315](file://app/backend/routes/auth.py#L277-L315)
- [auth_routes.py:317-367](file://app/backend/routes/auth.py#L317-L367)

**Section sources**
- [auth_routes.py:43-75](file://app/backend/routes/auth.py#L43-L75)
- [auth_routes.py:264-367](file://app/backend/routes/auth.py#L264-L367)
- [auth.py:182-229](file://app/backend/middleware/auth.py#L182-L229)

## Frontend Integration

### React-Based User Interface

The frontend provides a comprehensive user management interface with advanced functionality:

```mermaid
graph TB
subgraph "Admin Interface"
UsersPage[Users Management Page]
TenantsPage[Tenants Management Page]
TeamPage[Team Management Page]
AdminLayout[Admin Layout]
end
subgraph "Components"
UserTable[User Table Component]
AddUserModal[Add User Modal]
ChangeRoleModal[Change Role Modal]
TenantSelector[Tenant Selector]
UserFilters[User Filters]
RoleBadge[Role Badge Component]
StatusBadge[Status Badge Component]
RowActions[Row Actions Dropdown]
Toast[Toast Notifications]
end
subgraph "State Management"
AuthContext[Auth Context]
ToastNotifications[Toast Notifications]
LoadingStates[Loading States]
PaginationStates[Pagination States]
FilterStates[Filter States]
end
UsersPage --> UserTable
UsersPage --> AddUserModal
UsersPage --> ChangeRoleModal
UsersPage --> UserFilters
UsersPage --> RoleBadge
UsersPage --> StatusBadge
UsersPage --> RowActions
TenantsPage --> TenantSelector
TeamPage --> UserTable
AuthContext --> UsersPage
AuthContext --> TenantsPage
AuthContext --> TeamPage
ToastNotifications --> UsersPage
LoadingStates --> UsersPage
PaginationStates --> UsersPage
FilterStates --> UsersPage
```

**Diagram sources**
- [UsersPage.jsx:295-649](file://app/frontend/src/pages/admin/UsersPage.jsx#L295-L649)
- [AuthContext.jsx:1-112](file://app/frontend/src/contexts/AuthContext.jsx#L1-L112)

### Advanced Component Architecture

The UsersPage component implements a sophisticated component architecture:

```mermaid
classDiagram
class UsersPage {
+tenants : array
+selectedTenantId : string
+users : array
+loading : boolean
+error : string
+filters : object
+pagination : object
+modals : object
+fetchTenants()
+fetchUsers()
+handleRowAction()
+handleSearchSubmit()
}
class AddUserModal {
+email : string
+role : string
+saving : boolean
+error : string
+handleSubmit()
}
class ChangeRoleModal {
+role : string
+saving : boolean
+error : string
+handleSubmit()
}
class RowActions {
+open : boolean
+handleAction()
}
class RoleBadge {
+role : string
+render()
}
class StatusBadge {
+isActive : boolean
+render()
}
UsersPage --> AddUserModal
UsersPage --> ChangeRoleModal
UsersPage --> RowActions
UsersPage --> RoleBadge
UsersPage --> StatusBadge
```

**Diagram sources**
- [UsersPage.jsx:85-166](file://app/frontend/src/pages/admin/UsersPage.jsx#L85-L166)
- [UsersPage.jsx:217-292](file://app/frontend/src/pages/admin/UsersPage.jsx#L217-L292)
- [UsersPage.jsx:169-214](file://app/frontend/src/pages/admin/UsersPage.jsx#L169-L214)
- [UsersPage.jsx:41-53](file://app/frontend/src/pages/admin/UsersPage.jsx#L41-L53)
- [UsersPage.jsx:56-66](file://app/frontend/src/pages/admin/UsersPage.jsx#L56-L66)

### Enhanced API Integration Patterns

The frontend integrates with backend APIs through a centralized API client with comprehensive error handling and optimized pagination:

```mermaid
sequenceDiagram
participant UI as "React Component"
participant API as "API Client"
participant Auth as "Auth Service"
participant Backend as "FastAPI Backend"
UI->>API : getAdminTenants({per_page : 100})
API->>Auth : Check Authentication
Auth->>Auth : Validate Access Token
Auth->>API : Token Refresh if Needed
API->>Backend : GET /api/admin/tenants?page=1&per_page=100
Backend->>Backend : RBAC Check
Backend->>Backend : Load Data with Pagination
Backend->>API : Return JSON Response with Pagination
API->>UI : Process Response with extractApiError()
UI->>API : addUserToTenant()
API->>Auth : Add CSRF Token
API->>Backend : POST /api/admin/tenants/{id}/users
Backend->>Backend : Validate Request
Backend->>Backend : Create User
Backend->>API : Return Success
API->>UI : Update UI State with Error Handling
UI->>API : removeUserFromTenant()
API->>Auth : Add CSRF Token
API->>Backend : DELETE /api/admin/tenants/{id}/users/{userId}
Backend->>Backend : Validate Request
Backend->>Backend : Deactivate User
Backend->>API : Return Success
API->>UI : Update UI State with extractApiError()
```

**Diagram sources**
- [UsersPage.jsx:320-354](file://app/frontend/src/pages/admin/UsersPage.jsx#L320-L354)
- [api.js:1-140](file://app/frontend/src/lib/api.js#L1-L140)
- [api.js:1077-1085](file://app/frontend/src/lib/api.js#L1077-L1085)

### User-Friendly Error Messaging

The system implements comprehensive user-friendly error messaging through the getUserFriendlyError() function:

```mermaid
flowchart TD
ErrorDetection[Error Detection] --> NetworkError[Network Error]
ErrorDetection --> HttpError[HTTP Error]
NetworkError --> NetworkMessage[Network Error Message]
HttpError --> StatusCheck[Check HTTP Status]
StatusCheck --> FourHundred[4xx Error Mapping]
StatusCheck --> FiveHundred[5xx Error Mapping]
FourHundred --> FourHundredMessage[Specific 4xx Message]
FiveHundred --> FiveHundredMessage[Specific 5xx Message]
NetworkMessage --> DisplayError[Display Error]
FourHundredMessage --> DisplayError
FiveHundredMessage --> DisplayError
```

**Diagram sources**
- [api.js:1046-1068](file://app/frontend/src/lib/api.js#L1046-L1068)

**Section sources**
- [UsersPage.jsx:295-649](file://app/frontend/src/pages/admin/UsersPage.jsx#L295-L649)
- [AuthContext.jsx:1-112](file://app/frontend/src/contexts/AuthContext.jsx#L1-L112)
- [api.js:1-140](file://app/frontend/src/lib/api.js#L1-L140)
- [api.js:1046-1085](file://app/frontend/src/lib/api.js#L1046-L1085)

## API Endpoints

### Authentication Endpoints

The system provides comprehensive authentication endpoints:

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/auth/register` | POST | Register new user and tenant | None |
| `/api/auth/verify-email/{token}` | GET | Verify user email address | None |
| `/api/auth/login` | POST | User login | None |
| `/api/auth/refresh` | POST | Refresh access token | None |
| `/api/auth/me` | GET | Get current user info | JWT Required |
| `/api/auth/logout` | POST | Logout user | JWT Required |
| `/api/auth/forgot-password` | POST | Request password reset | None |
| `/api/auth/reset-password` | POST | Reset user password | None |

### Team Management Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/team` | GET | List team members | JWT Required |
| `/api/invites` | POST | Invite team member | Admin Required |
| `/api/team/{user_id}` | DELETE | Remove team member | Admin Required |
| `/api/team/profiles` | POST | Create team profile | JWT Required |
| `/api/team/profiles` | GET | List team profiles | JWT Required |
| `/api/team/profiles/{profile_id}` | PUT | Update team profile | JWT Required |
| `/api/team/profiles/{profile_id}` | DELETE | Delete team profile | JWT Required |
| `/api/team/profiles/{profile_id}/gap-analysis` | GET | Calculate skill gaps | JWT Required |

### Admin Management Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/admin/tenants` | GET | List all tenants | Platform Admin |
| `/api/admin/tenants/{tenant_id}` | GET | Get tenant details | Platform Admin |
| `/api/admin/tenants` | POST | Create tenant | Super Admin |
| `/api/admin/tenants/{tenant_id}` | PUT | Update tenant | Platform Admin |
| `/api/admin/tenants/{tenant_id}` | DELETE | Delete tenant | Super Admin |
| `/api/admin/tenants/{tenant_id}/suspend` | POST | Suspend tenant | Platform Admin |
| `/api/admin/tenants/{tenant_id}/reactivate` | POST | Reactivate tenant | Platform Admin |
| `/api/admin/tenants/{tenant_id}/change-plan` | POST | Change tenant plan | Platform Admin |
| `/api/admin/tenants/{tenant_id}/adjust-usage` | POST | Adjust usage | Platform Admin |
| `/api/admin/tenants/{tenant_id}/usage-history` | GET | Get usage history | Platform Admin |
| `/api/admin/tenants/{tenant_id}/users` | POST | Add user to tenant | Platform Admin |
| `/api/admin/tenants/{tenant_id}/users` | GET | List tenant users | Platform Admin |
| `/api/admin/tenants/{tenant_id}/users/{user_id}` | DELETE | Remove user from tenant | Platform Admin |

### Tenant User Management Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/admin/tenants/{tenant_id}/users` | POST | Add user to tenant or create new user | Platform Admin |
| `/api/admin/tenants/{tenant_id}/users/{user_id}` | DELETE | Remove user from tenant (deactivate) | Platform Admin |

**Section sources**
- [auth_routes.py:175-517](file://app/backend/routes/auth.py#L175-L517)
- [team_routes.py:52-295](file://app/backend/routes/team.py#L52-L295)
- [admin_routes.py:201-800](file://app/backend/routes/admin.py#L201-L800)

## Best Practices and Guidelines

### Security Best Practices

1. **Token Management**: All authentication tokens are stored as httpOnly cookies to prevent XSS attacks
2. **CSRF Protection**: CSRF tokens are automatically attached to state-changing requests
3. **Rate Limiting**: Built-in rate limiting prevents brute force attacks
4. **Input Validation**: All user inputs are validated using Pydantic models
5. **Tenant Isolation**: Database queries always include tenant filtering

### User Experience Guidelines

1. **Progressive Enhancement**: Frontend gracefully handles authentication state changes
2. **Loading States**: Comprehensive loading states improve user experience
3. **Enhanced Error Handling**: Clear error messages with extractApiError() guide users through recovery
4. **Accessibility**: Components follow accessibility guidelines
5. **Responsive Design**: Interface works across all device sizes
6. **Advanced Filtering**: Sophisticated filtering reduces cognitive load
7. **Bulk Operations**: Efficient bulk actions for administrative tasks
8. **Optimized Pagination**: 100 items per page improves performance for large datasets

### Performance Considerations

1. **Database Indexing**: Strategic indexing on frequently queried fields
2. **Optimized Pagination**: 100 items per page reduces API calls for large datasets
3. **Caching**: JWT token validation results are cached
4. **Connection Pooling**: Database connections are pooled for efficiency
5. **Lazy Loading**: Frontend components use lazy loading for optimal performance
6. **Component Optimization**: React.memo and useCallback for performance optimization
7. **Error Handling Optimization**: extractApiError() prevents crashes from complex error responses

### Maintenance and Monitoring

1. **Audit Logging**: All administrative actions are logged
2. **Health Checks**: Regular health checks monitor system status
3. **Enhanced Error Tracking**: Comprehensive error tracking with user-friendly messages
4. **Performance Metrics**: System performance metrics collection
5. **Security Audits**: Regular security audits and vulnerability assessments
6. **User Management Analytics**: Track user engagement and system usage patterns

This comprehensive user management system provides a robust foundation for the Resume AI platform, supporting both individual user needs and enterprise-scale tenant management with strong security guarantees and excellent user experience. The enhanced error handling with extractApiError() utility and optimized pagination to 100 items per page significantly improves the reliability and performance of the administrative user management interface.