"""Fixed, explicit grants. No wildcard, implicit inheritance or browser authority."""
from types import MappingProxyType

PERMISSIONS = frozenset({'platform.read', 'module.read', 'module.manage', 'users.manage', 'audit.read', 'notifications.manage'})
ROLE_PERMISSIONS = MappingProxyType({
    'owner': PERMISSIONS,
    'admin': frozenset({'platform.read', 'module.read', 'module.manage', 'audit.read', 'notifications.manage'}),
    'viewer': frozenset({'platform.read', 'module.read'}),
})


def permissions_for(role):
    return ROLE_PERMISSIONS.get(role, frozenset())
