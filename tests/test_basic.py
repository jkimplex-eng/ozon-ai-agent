"""Basic tests for ozon_agent."""


def test_import():
    """Test that the package can be imported."""
    import ozon_agent
    assert ozon_agent.__version__ == "0.1.0"


def test_ozon_client_init():
    """Test OzonClient initialization."""
    from ozon_agent.api.ozon_client import OzonClient
    client = OzonClient(client_id="test", api_key="test")
    assert client.client_id == "test"
    assert client.api_key == "test"
    client.close()


def test_database_url():
    """Test database URL configuration."""
    from ozon_agent.db.connection import get_database_url
    url = get_database_url()
    assert "postgresql" in url
