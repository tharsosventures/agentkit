from unittest.mock import Mock

import json
import requests

import pytest

from coinbase_agentkit.action_providers.x402.x402_action_provider import (
    X402ActionProvider,
)
from coinbase_agentkit.network import Network


def test_supports_network(provider):
    network = Network(protocol_family="evm", network_id="base-mainnet")
    assert provider.supports_network(network)

    network = Network(protocol_family="evm", network_id="base-sepolia")
    assert provider.supports_network(network)

    network = Network(protocol_family="evm", network_id="ethereum")
    assert not provider.supports_network(network)

    network = Network(protocol_family="solana", network_id="mainnet")
    assert not provider.supports_network(network)


def test_fetch_payment_info_402(
    provider,
    mock_wallet_provider,
    mock_request,
    mock_decode_payment_response,
):
    mock_request.return_value.status_code = 402
    mock_request.return_value.json.return_value = {"detail": "payment"}
    mock_request.return_value.headers = {"x-payment-response": "encoded"}
    mock_decode_payment_response.return_value = {"success": True}

    result = provider.fetch_payment_info(
        mock_wallet_provider,
        {"url": "https://www.x402.org/protected", "method": "GET"},
    )

    data = json.loads(result)
    assert data["paymentRequired"] is True
    assert data["status"] == 402
    assert data["paymentDetails"] == {"success": True}


def test_fetch_payment_info_non_payment(provider, mock_wallet_provider, mock_request):
    mock_request.return_value.status_code = 200
    mock_request.return_value.json.return_value = {"message": "ok"}
    mock_request.return_value.headers = {}

    result = provider.fetch_payment_info(
        mock_wallet_provider,
        {"url": "https://api.example.com/free", "method": "GET"},
    )

    data = json.loads(result)
    assert data["paymentRequired"] is False
    assert data["status"] == 200
    assert data["data"] == {"message": "ok"}


def test_fetch_payment_info_http_error(provider, mock_wallet_provider, mock_request):
    response = Mock()
    response.status_code = 500
    response.json.return_value = {"error": "server"}
    response.reason = "Internal Server Error"
    error = requests.RequestException(response=response, request=None)
    mock_request.side_effect = error

    result = provider.fetch_payment_info(
        mock_wallet_provider,
        {"url": "https://api.example.com/endpoint", "method": "GET"},
    )

    assert "HTTP 500" in result
    assert "server" in result


def test_fetch_payment_info_network_error(provider, mock_wallet_provider, mock_request):
    error = requests.RequestException("timeout")
    error.request = Mock()
    mock_request.side_effect = error

    result = provider.fetch_payment_info(
        mock_wallet_provider,
        {"url": "https://api.example.com/endpoint", "method": "GET"},
    )

    assert "Network error" in result


def test_paid_request_success_with_payment(
    provider,
    mock_wallet_provider,
    mock_request,
    mock_with_payment_interceptor,
    mock_decode_payment_response,
):
    mock_with_payment_interceptor.return_value.request = mock_request
    mock_request.return_value.status_code = 200
    mock_request.return_value.json.return_value = {"data": "ok"}
    mock_request.return_value.headers = {"x-payment-response": "encoded"}
    mock_decode_payment_response.return_value = {"success": True}

    result = provider.paid_request(
        mock_wallet_provider,
        {"url": MOCK_URL, "method": "GET"},
    )
    data = json.loads(result)
    assert data["success"] is True
    assert data["status"] == 200
    assert data["paymentResponse"] == {"success": True}


def test_paid_request_http_error(provider, mock_wallet_provider, mock_request, mock_with_payment_interceptor):
    mock_with_payment_interceptor.return_value.request = mock_request
    response = Mock()
    response.status_code = 400
    response.json.return_value = {"error": "bad"}
    response.reason = "Bad Request"
    error = requests.RequestException(response=response, request=None)
    mock_request.side_effect = error

    result = provider.paid_request(
        mock_wallet_provider,
        {"url": MOCK_URL, "method": "POST"},
    )

    assert "HTTP 400" in result
    assert "bad" in result


def test_paid_request_network_error(provider, mock_wallet_provider, mock_request, mock_with_payment_interceptor):
    mock_with_payment_interceptor.return_value.request = mock_request
    error = requests.RequestException("timeout")
    error.request = Mock()
    mock_request.side_effect = error

    result = provider.paid_request(
        mock_wallet_provider,
        {"url": MOCK_URL, "method": "GET"},
    )
    assert "Network error" in result

