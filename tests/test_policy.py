def test_groups_combine_defaults_dept_and_title(policy):
    assert policy.groups_for("Engineering", "Security Engineer") == {
        "all-staff", "eng-all", "github-users", "sec-tools", "vpn-privileged"}


def test_unknown_department_gets_defaults_only(policy):
    assert policy.groups_for("Marketing", "Intern") == {"all-staff"}


def test_managed_groups_cover_policy_groups(policy):
    assert {"all-staff", "crm-admins", "server-admins"} <= policy.managed_groups
    assert "some-manual-group" not in policy.managed_groups
