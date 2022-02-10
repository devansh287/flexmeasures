import pytest
from typing import Dict

from flexmeasures.auth.policy import ADMIN_ROLE
from flexmeasures.data.services.users import Account, create_user, User


@pytest.fixture(scope="module")
def setup_mdc_account(db) -> Dict[str, Account]:
    mdc_account = Account(
        name="Test MDC Account",
    )
    db.session.add(mdc_account)
    return {mdc_account.name: mdc_account}


@pytest.fixture(scope="module")
def setup_mdc_account_owner(db, setup_mdc_account) -> Dict[str, User]:
    account_owner = create_user(
        username="Test Account Owner",
        email="test_account_owner@seita.nl",
        account_name=setup_mdc_account["Test MDC Account"].name,
        password="testtest",
        # TODO: change ADMIN_ROLE to ACCOUNT_ADMIN
        user_roles=dict(
            name=ADMIN_ROLE, description="A user who can do everything."
        ),
    )
    return {account_owner.username: account_owner}
