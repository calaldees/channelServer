import pytest
import logging
import socket
import time

from ..server import aiohttp_app


log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(process)d %(name)s: %(message)s')


# Fixtures ---------------------------------------------------------------------

@pytest.fixture(scope='session')
def server():
    yield aiohttp_app()


# Tests ------------------------------------------------------------------------

def test_stub(server):
    assert True
