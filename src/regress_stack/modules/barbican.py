# Copyright 2025 - Canonical Ltd
# SPDX-License-Identifier: Apache-2.0

import logging
import pathlib

from regress_stack.core import utils as core_utils
from regress_stack.modules import keystone, mysql, rabbitmq
from regress_stack.modules import utils as module_utils

LOG = logging.getLogger(__name__)

DEPENDENCIES = {keystone, mysql, rabbitmq}
PACKAGES = [
    "barbican-api",
    "barbican-keystone-listener",
    "barbican-worker",
]
LOGS = ["/var/log/barbican"]

CONF = "/etc/barbican/barbican.conf"
URL = f"http://{core_utils.my_ip()}:9311/"
SERVICE = "barbican"
SERVICE_TYPE = "key-manager"
BARBICAN_ROLES = [
    "admin",
    "creator",
    "key-manager:service-admin",
]

TEST_INCLUDE_REGEXES = ["barbican_tempest_plugin.tests.api"]
TEST_EXCLUDE_REGEXES = []


def setup():
    db_user, db_pass = mysql.ensure_service(SERVICE)
    rabbit_user, rabbit_pass = rabbitmq.ensure_service(SERVICE)
    username, password = keystone.ensure_service_account(SERVICE, SERVICE_TYPE, URL)
    for role in BARBICAN_ROLES:
        keystone.ensure_role(role)
    module_utils.cfg_set(
        CONF,
        (
            "database",
            "connection",
            mysql.connection_string(SERVICE, db_user, db_pass),
        ),
        ("database", "max_pool_size", "1"),
        *module_utils.dict_to_cfg_set_args(
            "keystone_authtoken", keystone.authtoken_service(username, password)
        ),
        *module_utils.dict_to_cfg_set_args(
            "service_auth", keystone.account_dict(username, password)
        ),
        ("DEFAULT", "transport_url", rabbitmq.transport_url(rabbit_user, rabbit_pass)),
    )
    core_utils.sudo("barbican-manage", ["db", "upgrade"], user=SERVICE)
    core_utils.restart_service("barbican-keystone-listener", "barbican-worker")


def configure_tempest(tempest_conf: pathlib.Path):
    """Configure tempest for barbican."""
    conf = str(tempest_conf)
    module_utils.cfg_set(
        conf,
        ("service_available", "barbican", "True"),
        *module_utils.dict_to_cfg_set_args(
            "key_manager",
            {
                "region": module_utils.REGION,
            },
        ),
    )
