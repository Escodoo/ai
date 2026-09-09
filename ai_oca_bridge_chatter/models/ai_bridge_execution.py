# Copyright 2025 Dixmit
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from markupsafe import Markup

from odoo import _, fields, models


class AiBridgeExecution(models.Model):
    _inherit = "ai.bridge.execution"

    chatter_user_id = fields.Many2one("res.users", readonly=True)

    def _get_channel(self):
        if self.ai_bridge_id.usage == "chatter":
            # For chatter usage, we need to get the channel from the message
            message = self.env["mail.message"].browse(self.res_id)
            if message.model != "discuss.channel":
                raise ValueError(_("The message does not belong to any channel."))
            return (
                self.env["discuss.channel"]
                .browse(message.res_id)
                .with_user(self.chatter_user_id.id)
            )
        return super()._get_channel()

    def _process_response_message(self, response):
        if self.ai_bridge_id.usage == "chatter":
            recipient = (
                self.env["discuss.channel.member"]
                .sudo()
                .search(
                    [
                        ("partner_id", "=", self.chatter_user_id.partner_id.id),
                        ("channel_id", "=", self._get_channel().id),
                    ],
                    limit=1,
                )
            )
            recipient._notify_typing(is_typing=False)
            # Existing bridges already return HTML. message_post escapes str
            # bodies and the Html field then wraps them, producing
            # <p>&lt;p&gt;...&lt;/p&gt;</p>. body_is_html=True also warns for
            # internal users, so convert HTML to Markup instead of rewriting.
            body = response.get("body")
            body_is_html = bool(response.pop("body_is_html", False))
            if not isinstance(body, Markup):
                body = body or ""
                if body_is_html or (body.lstrip().startswith("<") and ">" in body):
                    body = Markup(body)
            response.update(
                {
                    "author_id": self.chatter_user_id.partner_id.id,
                    "body": body,
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                }
            )

        return super()._process_response_message(response)
