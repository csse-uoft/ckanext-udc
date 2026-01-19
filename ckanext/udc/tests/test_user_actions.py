"""
Unit tests for user management actions.
"""
import pytest
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.tests import helpers, factories


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestDeletedUsersList:
    """Tests for the deleted_users_list action."""

    def test_list_deleted_users_as_sysadmin(self):
        """Sysadmin can list deleted users."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Create and delete a user
        user = factories.User()
        user_obj = model.User.get(user['id'])
        user_obj.delete()
        model.Session.commit()
        
        # List deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('deleted_users_list', context=context)
        
        # Verify
        assert isinstance(result, dict)
        assert result["total"] > 0
        assert isinstance(result["results"], list)
        
        # Find our deleted user
        deleted_user = next((u for u in result["results"] if u['id'] == user['id']), None)
        assert deleted_user is not None
        assert deleted_user['name'] == user['name']
        assert deleted_user['state'] == 'deleted'
        assert 'email' in deleted_user
        assert 'created' in deleted_user
        assert 'about' in deleted_user

    def test_list_deleted_users_as_normal_user(self):
        """Normal users cannot list deleted users."""
        # Create normal user
        user = factories.User()
        
        # Try to list deleted users
        context = {'user': user['name'], 'ignore_auth': False}
        
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action('deleted_users_list', context=context)

    def test_list_deleted_users_anonymous(self):
        """Anonymous users cannot list deleted users."""
        context = {'user': None, 'ignore_auth': False}
        
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action('deleted_users_list', context=context)

    def test_list_deleted_users_empty(self):
        """Returns empty list when no deleted users exist."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Purge any existing deleted users first
        context = {'user': sysadmin['name'], 'ignore_auth': True}
        helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # List deleted users
        result = helpers.call_action('deleted_users_list', context=context)
        
        assert isinstance(result, dict)
        assert result["total"] == 0
        assert result["results"] == []

    def test_list_multiple_deleted_users(self):
        """Can list multiple deleted users."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Create and delete multiple users
        user1 = factories.User()
        user2 = factories.User()
        user3 = factories.User()
        
        for user in [user1, user2, user3]:
            user_obj = model.User.get(user['id'])
            user_obj.delete()
        model.Session.commit()
        
        # List deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('deleted_users_list', context=context)
        
        # Verify all three are in the list
        deleted_ids = [u['id'] for u in result["results"]]
        assert user1['id'] in deleted_ids
        assert user2['id'] in deleted_ids
        assert user3['id'] in deleted_ids

    def test_list_does_not_include_active_users(self):
        """Active users are not included in deleted users list."""
        # Create sysadmin and active user
        sysadmin = factories.Sysadmin()
        active_user = factories.User()
        
        # List deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('deleted_users_list', context=context)
        
        # Verify active user is not in the list
        deleted_ids = [u['id'] for u in result["results"]]
        assert active_user['id'] not in deleted_ids


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestPurgeDeletedUsers:
    """Tests for the purge_deleted_users action."""

    def test_purge_deleted_users_as_sysadmin(self):
        """Sysadmin can purge deleted users."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Create and delete a user
        user = factories.User()
        user_id = user['id']
        user_obj = model.User.get(user_id)
        user_obj.delete()
        model.Session.commit()
        
        # Purge deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # Verify result
        assert result['success'] is True
        assert result['count'] >= 1
        assert 'message' in result
        
        # Verify user is completely gone
        purged_user = model.User.get(user_id)
        assert purged_user is None

    def test_purge_deleted_users_as_normal_user(self):
        """Normal users cannot purge deleted users."""
        # Create normal user
        user = factories.User()
        
        # Try to purge deleted users
        context = {'user': user['name'], 'ignore_auth': False}
        
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action('purge_deleted_users', context=context)

    def test_purge_deleted_users_anonymous(self):
        """Anonymous users cannot purge deleted users."""
        context = {'user': None, 'ignore_auth': False}
        
        with pytest.raises(tk.NotAuthorized):
            helpers.call_action('purge_deleted_users', context=context)

    def test_purge_deleted_users_empty(self):
        """Purge returns zero count when no deleted users exist."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Purge any existing deleted users first
        context = {'user': sysadmin['name'], 'ignore_auth': True}
        helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # Purge again
        result = helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        assert result['success'] is True
        assert result['count'] == 0

    def test_purge_multiple_deleted_users(self):
        """Can purge multiple deleted users at once."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Create and delete multiple users
        user_ids = []
        for i in range(3):
            user = factories.User()
            user_ids.append(user['id'])
            user_obj = model.User.get(user['id'])
            user_obj.delete()
        model.Session.commit()
        
        # Purge deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('purge_deleted_users', context=context, ids=user_ids)
        
        # Verify result
        assert result['success'] is True
        assert result['count'] >= 3
        
        # Verify all users are completely gone
        for user_id in user_ids:
            purged_user = model.User.get(user_id)
            assert purged_user is None

    def test_purge_does_not_affect_active_users(self):
        """Active users are not affected by purge."""
        # Create sysadmin and active user
        sysadmin = factories.Sysadmin()
        active_user = factories.User()
        
        # Purge deleted users
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # Verify active user still exists
        user_obj = model.User.get(active_user['id'])
        assert user_obj is not None
        assert user_obj.state == 'active'

    def test_purge_removes_user_memberships(self):
        """Purge removes user's group and organization memberships."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        
        # Create user and organization
        user = factories.User()
        org = factories.Organization(
            users=[{'name': user['name'], 'capacity': 'member'}]
        )
        
        # Verify membership exists
        member = model.Session.query(model.Member).filter(
            model.Member.table_id == user['id'],
            model.Member.group_id == org['id']
        ).first()
        assert member is not None
        
        # Delete and purge user
        user_obj = model.User.get(user['id'])
        user_obj.delete()
        model.Session.commit()
        
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # Verify membership is gone
        member = model.Session.query(model.Member).filter(
            model.Member.table_id == user['id'],
            model.Member.group_id == org['id']
        ).first()
        assert member is None

    def test_purge_workflow(self):
        """Complete workflow: list, purge, verify."""
        # Create sysadmin
        sysadmin = factories.Sysadmin()
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        
        # Create and delete users
        user1 = factories.User()
        user2 = factories.User()
        
        for user in [user1, user2]:
            user_obj = model.User.get(user['id'])
            user_obj.delete()
        model.Session.commit()
        
        # Step 1: List deleted users
        deleted_list = helpers.call_action('deleted_users_list', context=context)
        initial_count = deleted_list["total"]
        assert initial_count >= 2
        
        deleted_ids = [u['id'] for u in deleted_list["results"]]
        assert user1['id'] in deleted_ids
        assert user2['id'] in deleted_ids
        
        # Step 2: Purge deleted users
        purge_result = helpers.call_action('purge_deleted_users', context=context, ids=deleted_ids)
        assert purge_result['success'] is True
        assert purge_result['count'] == initial_count
        
        # Step 3: Verify list is now empty
        deleted_list_after = helpers.call_action('deleted_users_list', context=context)
        assert deleted_list_after["total"] == 0
        
        # Step 4: Verify users are completely gone
        assert model.User.get(user1['id']) is None
        assert model.User.get(user2['id']) is None


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestUserManagementIntegration:
    """Integration tests for user management APIs."""

    def test_deleted_user_datasets_remain(self):
        """Datasets created by deleted users remain after purge."""
        # Create sysadmin and user
        sysadmin = factories.Sysadmin()
        user = factories.User()
        
        # Create dataset as user
        dataset = factories.Dataset(user=user)
        dataset_id = dataset['id']
        
        # Delete and purge user
        user_obj = model.User.get(user['id'])
        user_obj.delete()
        model.Session.commit()
        
        context = {'user': sysadmin['name'], 'ignore_auth': False}
        helpers.call_action('purge_deleted_users', context=context, ids=[])
        
        # Verify dataset still exists
        dataset_obj = model.Package.get(dataset_id)
        assert dataset_obj is not None
        assert dataset_obj.state == 'active'

    def test_cannot_purge_with_api_key_from_deleted_user(self):
        """Cannot use API key from a deleted user."""
        # Create user
        user = factories.User()
        api_key = user['apikey']
        
        # Delete user
        user_obj = model.User.get(user['id'])
        user_obj.delete()
        model.Session.commit()
        
        # Try to use deleted user's API key
        context = {'user': user['name'], 'ignore_auth': False}
        
        # This should fail because the user is deleted
        with pytest.raises((tk.NotAuthorized, tk.ObjectNotFound)):
            helpers.call_action('purge_deleted_users', context=context, ids=[])


@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestUserList:
    """Tests for the udc_user_list action."""

    def test_list_users_as_sysadmin(self):
        sysadmin = factories.Sysadmin()
        user = factories.User()

        context = {'user': sysadmin['name'], 'ignore_auth': False}
        result = helpers.call_action('udc_user_list', context=context, page=1, page_size=25)

        assert isinstance(result, dict)
        assert result["total"] >= 1
        assert any(u["id"] == user["id"] for u in result["results"])

    def test_list_users_as_normal_user(self):
        user = factories.User()
        context = {'user': user['name'], 'ignore_auth': False}

        with pytest.raises(tk.NotAuthorized):
            helpers.call_action('udc_user_list', context=context, page=1, page_size=25)
