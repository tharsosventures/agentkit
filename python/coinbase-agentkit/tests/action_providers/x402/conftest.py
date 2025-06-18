"""Fixtures for X402 action provider tests."""

from unittest.mock import Mock, patch

import pytest

from coinbase_agentkit.action_providers.x402.x402_action_provider import X402ActionProvider
from coinbase_agentkit.wallet_providers.evm_wallet_provider import EvmWalletProvider
from coinbase_agentkit.network import Network

MOCK_SIGNER = "mock-signer"
MOCK_URL = "https://www.x402.org/protected"
MOCK_NETWORK = Network(protocol_family="evm", network_id="base-sepolia")


@pytest.fixture
def mock_wallet_provider():
    wallet = Mock(spec=EvmWalletProvider)
    wallet.to_signer.return_value = MOCK_SIGNER
    wallet.get_network.return_value = MOCK_NETWORK
    return wallet


@pytest.fixture
def mock_request():
    with patch("requests.request") as mock:
        yield mock


@pytest.fixture
def mock_with_payment_interceptor():
    with patch(
        "coinbase_agentkit.action_providers.x402.x402_action_provider.with_payment_interceptor"
    ) as mock:
        yield mock


@pytest.fixture
def mock_decode_payment_response():
    with patch(
        "coinbase_agentkit.action_providers.x402.x402_action_provider.decode_x_payment_response"
    ) as mock:
        yield mock


@pytest.fixture
def provider():
    return X402ActionProvider()
