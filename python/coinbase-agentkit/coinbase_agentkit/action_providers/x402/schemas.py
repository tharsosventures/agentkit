"""Schemas for the X402 action provider."""

from typing import Any, Literal
from pydantic import BaseModel, Field, HttpUrl


class PaidRequestSchema(BaseModel):
    """Input schema for making a paid request to an x402-protected endpoint."""

    url: HttpUrl = Field(..., description="The URL of the x402-protected API endpoint")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        "GET", description="The HTTP method to use for the request"
    )
    headers: dict[str, str] | None = Field(
        default=None, description="Optional headers to include in the request"
    )
    body: Any | None = Field(
        default=None, description="Optional request body for POST/PUT/PATCH requests"
    )


class FetchPaymentInfoSchema(BaseModel):
    """Input schema for fetching payment info from an x402 endpoint."""

    url: HttpUrl = Field(..., description="The URL of the x402-protected API endpoint")
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        "GET", description="The HTTP method to use for the request"
    )
    headers: dict[str, str] | None = Field(
        default=None, description="Optional headers to include in the request"
    )

