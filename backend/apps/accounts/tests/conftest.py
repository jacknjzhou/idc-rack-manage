from unittest.mock import patch

import pytest
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminOrOperatorOrReadOnly

# The accounts tests verify the real permission policy. The rest of the
# regression suite can run with IDC_DISABLE_PERMISSIONS=1 (see config/settings.py),
# but these tests must always exercise the permission class regardless of that
# global bypass. DRF binds APIView.permission_classes at import time, so patch
# the class attribute directly instead of override_settings (which cannot
# reliably change it once DRF has been imported). Keeps test_roles.py identical
# to the task spec.
@pytest.fixture(autouse=True)
def enforce_permissions():
    with patch.object(APIView, "permission_classes",
                      [IsAdminOrOperatorOrReadOnly]):
        yield
