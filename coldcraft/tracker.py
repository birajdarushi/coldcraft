"""
Tracker — GTM Engine Mailer Agent
Email open/click tracking via pixel injection and link rewriting.
Constitution §6.4: tracking is opt-in per campaign.
"""

import re
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class Tracker:

    def __init__(self, config):
        self.tracking_domain = getattr(config, "tracking_domain", None)
        self.enabled = bool(self.tracking_domain)

    def inject_pixel(self, body_html: str, campaign_id: str) -> str:
        """
        Constitution §6.4: only inject if tracking is configured.
        Injects a 1×1 transparent pixel before </body>.
        """
        if not self.enabled:
            return body_html

        pixel_url = f"https://{self.tracking_domain}/track/open/{campaign_id}"
        pixel_tag = (
            f'<img src="{pixel_url}" width="1" height="1" '
            f'style="display:none;border:0;width:1px;height:1px;" '
            f'alt="" />'
        )

        if "</body>" in body_html:
            return body_html.replace("</body>", f"{pixel_tag}</body>")
        return body_html + pixel_tag

    def rewrite_links(self, body_html: str, campaign_id: str) -> str:
        """
        Rewrite all href links to pass through tracking server.
        Preserves original URL as query param.
        """
        if not self.enabled:
            return body_html

        def replace_href(match):
            original_url = match.group(1)
            # Skip mailto, tel, unsubscribe links — don't track those
            if original_url.startswith(("mailto:", "tel:", "#")):
                return match.group(0)
            if "unsubscribe" in original_url.lower():
                return match.group(0)
            encoded = quote(original_url, safe="")
            tracked = (
                f"https://{self.tracking_domain}/track/click/"
                f"{campaign_id}?url={encoded}"
            )
            return f'href="{tracked}"'

        return re.sub(r'href="([^"]+)"', replace_href, body_html)

    def record_open(self, campaign_id: str, metadata: dict = None) -> None:
        """Called by the tracking endpoint when pixel loads."""
        from .db.session import get_session
        from .db.models import EmailEvent
        import uuid
        from datetime import datetime, timezone

        with get_session() as db:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="opened",
                occurred_at=datetime.now(timezone.utc),
                event_metadata=str(metadata or {}),
            )
            db.add(event)
            db.commit()
        logger.info(f"Open event recorded: campaign={campaign_id}")

    def record_click(self, campaign_id: str, url: str) -> None:
        """Called by the tracking endpoint when a link is clicked."""
        from .db.session import get_session
        from .db.models import EmailEvent
        import uuid
        from datetime import datetime, timezone

        with get_session() as db:
            event = EmailEvent(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                event_type="clicked",
                occurred_at=datetime.now(timezone.utc),
                event_metadata=str({"url": url}),
            )
            db.add(event)
            db.commit()
        logger.info(f"Click event recorded: campaign={campaign_id} url={url}")
