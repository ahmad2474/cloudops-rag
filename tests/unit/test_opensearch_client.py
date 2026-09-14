"""Client construction for the OpenSearch provider (no network)."""

from unittest.mock import patch

import pytest
from opensearchpy import AWSV4SignerAsyncAuth

from cloudops_rag.providers.opensearch import make_client


def test_plain_client_has_no_auth() -> None:
    c = make_client("http://localhost:9200")
    assert c.transport.hosts[0]["host"] == "localhost"


def test_sigv4_client_signs_with_credential_chain() -> None:
    class Creds:
        access_key = "AKIAEXAMPLE"
        secret_key = "x"
        token = None

    with patch("boto3.Session") as session:
        session.return_value.get_credentials.return_value = Creds()
        c = make_client("https://search-demo.us-east-1.es.amazonaws.com", auth="sigv4")
    kwargs = c.transport.kwargs
    assert isinstance(kwargs["http_auth"], AWSV4SignerAsyncAuth)
    assert kwargs["verify_certs"] is True


def test_sigv4_without_credentials_fails_loudly() -> None:
    with patch("boto3.Session") as session:
        session.return_value.get_credentials.return_value = None
        with pytest.raises(RuntimeError, match="no AWS credentials"):
            make_client("https://x.es.amazonaws.com", auth="sigv4")
