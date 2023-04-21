"""REST client handling, including mailchimpStream base class."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, List

import requests
from singer_sdk.authenticators import BearerTokenAuthenticator
from singer_sdk.helpers.jsonpath import extract_jsonpath
from singer_sdk.streams import RESTStream
from singer_sdk.pagination import BaseOffsetPaginator

_Auth = Callable[[requests.PreparedRequest], requests.PreparedRequest]
SCHEMAS_DIR = Path(__file__).parent / Path("./schemas")
PAGE_SIZE = 1000

class MailchimpPaginator(BaseOffsetPaginator):
    response_key: str # name of the parent stream, needed to detect end of records
                        # sometimes bespoke response key needed to detect end of records

    def __init__(self, response_key: str) -> None:
        self.response_key = response_key
        super().__init__(
            start_value=0,
            page_size = PAGE_SIZE,
            )
        
    def has_more(self, response) -> bool:
        return len(response.json()[self.response_key])

class MailchimpStream(RESTStream):
    """Mailchimp stream class."""
    _LOG_REQUEST_METRIC_URLS = True

    next_page_token_jsonpath = "$.next_page"  # Or override `get_next_page_token`.
    exclude_fields: List[str] = [
        '_links',
    ]

    response_key: str  # used to find the list of records in the response

    @property
    def url_base(self) -> str:
        dc = self.config['dc']
        return f"https://{dc}.api.mailchimp.com/3.0"
    
    @property
    def records_jsonpath(self) -> str:
        return f"$.{self.response_key}[*]"

    @property
    def authenticator(self) -> BearerTokenAuthenticator:
        """Return a new authenticator object.

        Returns:
            An authenticator instance.
        """
        return BearerTokenAuthenticator.create_for_stream(
            self,
            token=self.config.get("api_key", ""),
        )

    @property
    def http_headers(self) -> dict:
        """Return the http headers needed.

        Returns:
            A dictionary of HTTP headers.
        """
        headers = {}
        if "user_agent" in self.config:
            headers["User-Agent"] = self.config.get("user_agent")
        # If not using an authenticator, you may also provide inline auth headers:
        # headers["Private-Token"] = self.config.get("auth_token")
        return headers

    def get_next_page_token(
        self,
        response: requests.Response,
        previous_token: Any | None,
    ) -> Any | None:
        """Return a token for identifying next page or None if no more pages.

        Args:
            response: The HTTP ``requests.Response`` object.
            previous_token: The previous page token value.

        Returns:
            The next pagination token.
        """
        # TODO: If pagination is required, return a token which can be used to get the
        #       next page. If this is the final page, return "None" to end the
        #       pagination loop.
        if self.next_page_token_jsonpath:
            all_matches = extract_jsonpath(
                self.next_page_token_jsonpath, response.json()
            )
            first_match = next(iter(all_matches), None)
            next_page_token = first_match
        else:
            next_page_token = response.headers.get("X-Next-Page", None)

        return next_page_token
    
    @property
    def page_size(self):
        return PAGE_SIZE

    def get_url_params(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict[str, Any]:
        """Return a dictionary of values to be used in URL parameterization.

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary of URL query parameters.
        """
        params: dict = {}
        if next_page_token:
            params["offset"] = next_page_token
        if self.exclude_fields:
            fields = [
                f'{self.response_key}.{fname}'
                for fname
                in self.exclude_fields
            ]
            params['exclude_fields'] = ','.join(fields)
        params['count'] = self.page_size
        return params

    def prepare_request_payload(
        self,
        context: dict | None,
        next_page_token: Any | None,
    ) -> dict | None:
        """Prepare the data payload for the REST API request.

        By default, no payload will be sent (return None).

        Args:
            context: The stream context.
            next_page_token: The next page index or value.

        Returns:
            A dictionary with the JSON body for a POST requests.
        """
        # TODO: Delete this method if no payload is required. (Most REST APIs.)
        return None

    def parse_response(self, response: requests.Response) -> Iterable[dict]:
        """Parse the response and return an iterator of result records.

        Args:
            response: The HTTP ``requests.Response`` object.

        Yields:
            Each record from the source.
        """
        # TODO: Parse response body and return a set of records.
        yield from extract_jsonpath(self.records_jsonpath, input=response.json())
    
    def post_process(self, row: dict, context: dict | None = None) -> dict | None:
        """
        This API returns empty strings in place of nulls
        Need to convert these to true nulls to get correct datetime handling,
        otherwise errors from trying to generate datetime from "".
        """
        row = {
            k: None if v == "" else v
            for k,v
            in row.items()
        }
        return row
    
    @property
    def schema_filepath(self) -> Path | None:
        return SCHEMAS_DIR / f'{self.name}.json'
    
    def get_new_paginator(self) -> BaseOffsetPaginator:
        return MailchimpPaginator(
            self.response_key
        )

