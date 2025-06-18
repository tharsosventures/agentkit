"""Action provider for making requests to x402-protected APIs."""

from __future__ import annotations

import json
from typing import Any

import requests

from ..action_decorator import create_action
from ..action_provider import ActionProvider
from ...network import Network
from ...wallet_providers import EvmWalletProvider
from .schemas import FetchPaymentInfoSchema, PaidRequestSchema

try:
    # Optional dependency used to handle the payment flow automatically.
    from x402_requests import with_payment_interceptor, decode_x_payment_response
except Exception:  # pragma: no cover - fallback when library is not installed
    def with_payment_interceptor(session: requests.Session, account: Any) -> requests.Session:  # type: ignore[return-type]
        raise NotImplementedError("x402-requests library is required")

    def decode_x_payment_response(data: str) -> Any:  # type: ignore[return-type]
        raise NotImplementedError("x402-requests library is required")


SUPPORTED_NETWORKS = ["base-mainnet", "base-sepolia"]


class X402ActionProvider(ActionProvider[EvmWalletProvider]):
    """Action provider for x402-protected API requests."""

    def __init__(self) -> None:
        super().__init__("x402", [])

    @create_action(
        name="paid_request",
        description=(
            """\
This tool makes HTTP requests to APIs that are protected by x402 paywalls. It automatically handles the payment flow when a 402 Payment Required response is received.

Inputs:
- url: The full URL of the x402-protected API endpoint
- method: The HTTP method (GET, POST, PUT, DELETE, PATCH) - defaults to GET
- headers: Optional additional headers to include in the request
- body: Optional request body for POST/PUT/PATCH requests

The tool will:
1. Make the initial request to the protected endpoint
2. If a 402 Payment Required response is received, automatically handle the payment using the wallet
3. Retry the request with payment proof
4. Return the API response data

Supported on EVM networks where the wallet can sign payment transactions.
"""
        ),
        schema=PaidRequestSchema,
    )
    def paid_request(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Make a paid request to an x402-protected endpoint."""
        try:
            validated = PaidRequestSchema(**args)

            account = wallet_provider.to_signer()
            session = with_payment_interceptor(requests.Session(), account)

            response = session.request(
                url=str(validated.url),
                method=validated.method,
                headers=validated.headers,
                json=validated.body,
            )

            payment_header = response.headers.get("x-payment-response")
            payment_response: Any | None = None
            if payment_header:
                try:
                    payment_response = decode_x_payment_response(payment_header)
                except Exception:
                    try:
                        payment_response = json.loads(payment_header)
                    except Exception:
                        payment_response = {
                            "error": "Failed to decode payment response",
                            "rawHeader": payment_header,
                        }

            result = {
                "success": True,
                "url": str(validated.url),
                "method": validated.method,
                "status": response.status_code,
                "data": response.json() if isinstance(response.text, str) else response.text,
                "paymentResponse": payment_response,
            }
            return json.dumps(result, indent=2)
        except requests.RequestException as exc:
            if exc.response is not None:
                data = None
                try:
                    data = exc.response.json()
                except Exception:
                    pass
                message = data.get("error") if isinstance(data, dict) else exc.response.reason
                return f"Error making paid request to {args.get('url')}: HTTP {exc.response.status_code} - {message}"
            if exc.request is not None:
                return f"Error making paid request to {args.get('url')}: Network error - {exc}"  # type: ignore[str-format]
            return f"Error making paid request to {args.get('url')}: {exc}"
        except Exception as exc:  # pragma: no cover - generic fallback
            return f"Error making paid request to {args.get('url')}: {exc}"

    @create_action(
        name="fetch_payment_info",
        description=(
            """\
This tool fetches payment information from x402-protected API endpoints without actually making any payments. It's useful for checking payment requirements before deciding whether to proceed with a paid request.

Inputs:
- url: The full URL of the x402-protected API endpoint
- method: The HTTP method (GET, POST, PUT, DELETE, PATCH) - defaults to GET
- headers: Optional additional headers to include in the request

The tool will:
1. Make a request to the protected endpoint
2. Receive the 402 Payment Required response with payment details
3. Return information about the payment requirements (amount, token, etc.)

Note: Payment amounts are returned in the smallest unit of the token. For example, for USDC (which has 6 decimal places) maxAmountRequired "10000" corresponds to 0.01 USDC.

This is useful for understanding what payment will be required before using the paid_request action.
"""
        ),
        schema=FetchPaymentInfoSchema,
    )
    def fetch_payment_info(self, wallet_provider: EvmWalletProvider, args: dict[str, Any]) -> str:
        """Fetch payment info from an x402-protected endpoint."""
        try:
            validated = FetchPaymentInfoSchema(**args)
            response = requests.request(
                url=str(validated.url),
                method=validated.method,
                headers=validated.headers,
            )
            if response.status_code == 402:
                payment_header = response.headers.get("x-payment-response")
                payment_details: Any | None = None
                if payment_header:
                    try:
                        payment_details = decode_x_payment_response(payment_header)
                    except Exception:
                        try:
                            payment_details = json.loads(payment_header)
                        except Exception:
                            payment_details = {
                                "error": "Failed to decode payment response",
                                "rawHeader": payment_header,
                            }
                result = {
                    "paymentRequired": True,
                    "url": str(validated.url),
                    "status": 402,
                    "data": response.json(),
                    "paymentDetails": payment_details,
                }
                return json.dumps(result, indent=2)

            result = {
                "paymentRequired": False,
                "url": str(validated.url),
                "status": response.status_code,
                "data": response.json() if isinstance(response.text, str) else response.text,
            }
            return json.dumps(result, indent=2)
        except requests.RequestException as exc:
            if exc.response is not None:
                if exc.response.status_code == 402:
                    payment_header = exc.response.headers.get("x-payment-response")
                    payment_details: Any | None = None
                    if payment_header:
                        try:
                            payment_details = decode_x_payment_response(payment_header)
                        except Exception:
                            try:
                                payment_details = json.loads(payment_header)
                            except Exception:
                                payment_details = {
                                    "error": "Failed to decode payment response",
                                    "rawHeader": payment_header,
                                }
                    result = {
                        "paymentRequired": True,
                        "url": str(args.get("url")),
                        "status": 402,
                        "paymentDetails": payment_details,
                        "data": exc.response.json(),
                    }
                    return json.dumps(result, indent=2)
                data = None
                try:
                    data = exc.response.json()
                except Exception:
                    pass
                message = data.get("error") if isinstance(data, dict) else exc.response.reason
                return f"Error fetching payment info from {args.get('url')}: HTTP {exc.response.status_code} - {message}"
            if exc.request is not None:
                return f"Error fetching payment info from {args.get('url')}: Network error - {exc}"  # type: ignore[str-format]
            return f"Error fetching payment info from {args.get('url')}: {exc}"
        except Exception as exc:  # pragma: no cover - generic fallback
            return f"Error fetching payment info from {args.get('url')}: {exc}"

    def supports_network(self, network: Network) -> bool:
        """Check if the provider supports the given network."""
        return network.protocol_family == "evm" and network.network_id in SUPPORTED_NETWORKS


def x402_action_provider() -> X402ActionProvider:
    """Factory for X402ActionProvider."""
    return X402ActionProvider()

