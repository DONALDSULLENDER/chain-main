import datetime
from pathlib import Path

import pytest
from dateutil.parser import isoparse

from .utils import cluster_fixture, wait_for_block_time, wait_for_new_blocks

"""
slashing testing
"""


# use custom cluster, use an unique base port
@pytest.fixture(scope="module")
def cluster(pytestconfig, tmp_path_factory):
    "override cluster fixture for this test module"
    yield from cluster_fixture(
        Path(__file__).parent / "configs/slashing.yaml",
        26700,
        tmp_path_factory,
        quiet=pytestconfig.getoption("supervisord-quiet"),
    )


@pytest.mark.slow
def test_slashing(cluster):
    "stop node2, wait for non-live slashing"
    addr = cluster.address("validator", i=2)
    val_addr = cluster.address("validator", i=2, bech="val")
    tokens1 = int((cluster.validator(val_addr))["tokens"])

    print("tokens before slashing", tokens1)
    print("stop and wait for 10 blocks")
    cluster.supervisor.stopProcess("node2")
    wait_for_new_blocks(cluster, 10)
    cluster.supervisor.startProcess("node2")

    val = cluster.validator(val_addr)
    tokens2 = int(val["tokens"])
    print("tokens after slashing", tokens2)
    assert tokens2 == int(tokens1 * 0.99), "slash amount is not correct"

    assert val["jailed"], "validator is jailed"

    # try to unjail
    rsp = cluster.unjail(addr, i=2)
    assert rsp["code"] == 4, "still jailed, can't be unjailed"

    # wait for 60s and unjail again
    wait_for_block_time(
        cluster, isoparse(val["unbonding_time"]) + datetime.timedelta(seconds=60)
    )
    rsp = cluster.unjail(addr, i=2)
    assert rsp["code"] == 0, f"unjail should success {rsp}"

    wait_for_new_blocks(cluster, 3)
    assert len(cluster.validators()) == 3
