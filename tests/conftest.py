"""Global pytest fixtures."""
import pytest
import pytest_socket


@pytest.fixture(autouse=True)
def allow_local_socket():
    """Enable socket usage for mock furnace tests."""
    pytest_socket.enable_socket()
    yield


@pytest.fixture
def socket_enabled():
    """Fixture required by pytest-homeassistant-custom-component HTTP test client."""
    pytest_socket.enable_socket()
    yield
