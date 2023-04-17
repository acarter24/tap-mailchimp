"""mailchimp tap class."""

from __future__ import annotations

from singer_sdk import Tap
from singer_sdk import typing as th  # JSON schema typing helpers

# TODO: Import your custom stream types here:
from tap_mailchimp import streams


class Tapmailchimp(Tap):
    """Mailchimp tap class."""

    name = "tap-mailchimp"

    # TODO: Update this section with the actual config values you expect:
    config_jsonschema = th.PropertiesList(
        th.Property(
            "api_key",
            th.StringType,
            required=True,
            secret=True,  # Flag config as protected.
            description="The token to authenticate against the API service",
        ),
        th.Property(
            "start_date",
            th.DateTimeType,
            description="The earliest record date to sync",
        ),
        th.Property(
            "dc",
            th.StringType,
            required=True,
            description="Your Mailchimp DC",
        ),
    ).to_dict()

    def discover_streams(self) -> list[streams.MailchimpStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            streams.CampaignsStream(self),
            streams.ReportsEmailActivity(self),
            streams.ReportsUnsubscribes(self),
            streams.ListsStream(self),
            streams.ListsMembersStream(self),
        ]


if __name__ == "__main__":
    Tapmailchimp.cli()
