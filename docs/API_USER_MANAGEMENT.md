# User Management API

This document describes the user management APIs for listing and purging deleted users.

## Overview

CKAN supports soft-deletion of users, where a user's `state` field is set to `'deleted'` but the user record remains in the database. The UDC extension provides two APIs for managing these deleted users:

1. **List Deleted Users** - Get a list of all soft-deleted users
2. **Purge Deleted Users** - Permanently remove all soft-deleted users from the database

## Authorization

Both APIs require **sysadmin privileges**. Non-sysadmin users will receive an authorization error.

## API Endpoints

### 1. List Deleted Users

Returns a list of all users that have been soft-deleted (where `state = 'deleted'`).

#### Endpoint

```
POST /api/3/action/deleted_users_list
```

#### Request

No parameters required.

```bash
curl -X POST \
  -H "Authorization: YOUR_API_KEY" \
  https://your-ckan-instance.com/api/3/action/deleted_users_list
```

#### Response

```json
{
  "success": true,
  "result": [
    {
      "id": "user-uuid-1",
      "name": "deleted_user_1",
      "fullname": "John Doe",
      "email": "john@example.com",
      "created": "2024-01-15T10:30:00",
      "state": "deleted"
    },
    {
      "id": "user-uuid-2",
      "name": "deleted_user_2",
      "fullname": "Jane Smith",
      "email": "jane@example.com",
      "created": "2024-03-20T14:45:00",
      "state": "deleted"
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (UUID) of the user |
| `name` | string | Username |
| `fullname` | string | Full name of the user |
| `email` | string | Email address |
| `created` | string | ISO 8601 timestamp of when the user was created |
| `state` | string | Always `"deleted"` for users in this list |

#### Python Example

```python
import ckan.plugins.toolkit as tk

# Get action
action = tk.get_action('deleted_users_list')

# Call with sysadmin context
context = {'user': 'admin_username'}
result = action(context, {})

print(f"Found {len(result)} deleted users")
for user in result:
    print(f"- {user['name']} ({user['email']})")
```

---

### 2. Purge Deleted Users

Permanently removes all soft-deleted users from the database. This action:

1. Removes all group and organization memberships
2. Removes all package collaboration relationships
3. Permanently deletes the user records

**⚠️ WARNING: This action cannot be undone. All deleted users will be permanently removed from the database.**

#### Endpoint

```
POST /api/3/action/purge_deleted_users
```

#### Request

No parameters required.

```bash
curl -X POST \
  -H "Authorization: YOUR_API_KEY" \
  https://your-ckan-instance.com/api/3/action/purge_deleted_users
```

#### Response

```json
{
  "success": true,
  "result": {
    "success": true,
    "count": 5,
    "message": "Successfully purged 5 deleted user(s)"
  }
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Always `true` if operation succeeded |
| `count` | integer | Number of users that were purged |
| `message` | string | Human-readable success message |

#### Python Example

```python
import ckan.plugins.toolkit as tk

# Get action
action = tk.get_action('purge_deleted_users')

# Call with sysadmin context
context = {'user': 'admin_username'}
result = action(context, {})

print(result['message'])  # "Successfully purged 5 deleted user(s)"
```

---

## Error Responses

### Authorization Error (Non-Sysadmin)

```json
{
  "success": false,
  "error": {
    "message": "Access denied",
    "__type": "Authorization Error"
  }
}
```

### General Error

```json
{
  "success": false,
  "error": {
    "message": "Error description",
    "__type": "Validation Error"
  }
}
```

---

## Usage Workflow

A typical workflow for managing deleted users:

```python
import ckan.plugins.toolkit as tk

# 1. List deleted users to see what will be purged
list_action = tk.get_action('deleted_users_list')
context = {'user': 'admin_username'}

deleted_users = list_action(context, {})
print(f"Found {len(deleted_users)} deleted users:")
for user in deleted_users:
    print(f"  - {user['name']} ({user['email']})")

# 2. Confirm with admin before purging
confirm = input(f"\nPurge {len(deleted_users)} users? (yes/no): ")

if confirm.lower() == 'yes':
    # 3. Purge all deleted users
    purge_action = tk.get_action('purge_deleted_users')
    result = purge_action(context, {})
    print(f"\n{result['message']}")
else:
    print("Purge cancelled")
```

---

## Technical Details

### Database Operations

When purging users, the following operations are performed:

1. **Query deleted users**: `SELECT * FROM "user" WHERE state = 'deleted'`
2. **Remove memberships**: Delete records from `member` table where `table_id = user.id`
3. **Remove collaborations**: Delete records from `package_member` table where `user_id = user.id`
4. **Purge user**: Call `user.purge()` to permanently delete the user record
5. **Commit transaction**: Persist all changes to the database

### Implementation

- **Module**: `ckanext.udc.user.actions`
- **Authorization**: `ckanext.udc.user.auth`
- **Functions**:
  - `deleted_users_list(context, data_dict)` - List action
  - `purge_deleted_users(context, data_dict)` - Purge action

---

## Security Considerations

1. **Sysadmin Only**: Both APIs are restricted to sysadmin users
2. **Irreversible**: Purge operations cannot be undone
3. **Audit Logging**: Consider logging purge operations for compliance
4. **Data Retention**: Ensure compliance with data retention policies before purging
5. **Backup**: Always maintain database backups before performing purge operations

---

## Testing

### Manual Testing

1. **Create and delete a test user**:
   ```bash
   # Create user
   ckan -c /etc/ckan/default/ckan.ini user add test_user email=test@example.com
   
   # Delete user (soft delete)
   ckan -c /etc/ckan/default/ckan.ini user remove test_user
   ```

2. **List deleted users via API**:
   ```bash
   curl -X POST \
     -H "Authorization: YOUR_API_KEY" \
     http://localhost:5000/api/3/action/deleted_users_list
   ```

3. **Purge deleted users via API**:
   ```bash
   curl -X POST \
     -H "Authorization: YOUR_API_KEY" \
     http://localhost:5000/api/3/action/purge_deleted_users
   ```

### Unit Testing
Under `/ckanext-udc/ckanext/udc/tests/user/`, unit tests cover:

---

## FAQ

**Q: What happens to datasets owned by purged users?**  
A: Datasets are not deleted. The dataset's `creator_user_id` field will still reference the purged user's ID, but the user record will no longer exist.

**Q: Can I recover a purged user?**  
A: No, purge operations are permanent. Only soft-deleted users (with `state='deleted'`) can potentially be reactivated before purging.

**Q: How do I soft-delete a user?**  
A: Use the standard CKAN API: `POST /api/3/action/user_delete` or the CLI command `ckan user remove <username>`

**Q: Will purging affect API keys or tokens?**  
A: Yes, all associated API keys and tokens will be removed when the user is purged.

**Q: Should I purge users regularly?**  
A: This depends on your organization's data retention policies and compliance requirements. Some organizations prefer to keep deleted users indefinitely for audit purposes.

---

## See Also

- [CKAN User Management Documentation](https://docs.ckan.org/en/latest/maintaining/cli.html#user-management)
- [CKAN API Guide](https://docs.ckan.org/en/latest/api/index.html)
- [CKAN Authorization Guide](https://docs.ckan.org/en/latest/maintaining/authorization.html)
