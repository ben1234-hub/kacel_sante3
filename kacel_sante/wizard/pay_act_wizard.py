
from odoo import models, fields, api

class PayActWizard(models.TransientModel):
    _name = 'pay.act.wizard'
    _description = 'Payment Wizard for Expired Abonnements'

    selected_act_id = fields.Many2one(
        'kinesitherapy.appointment.selected.act',
        string="Selected Act",
        required=True
    )
    appointment_id = fields.Many2one(
        'kinesitherapy.appointment',
        string="Appointment",
        required=True
    )
    message = fields.Text(string="Message", readonly=True)
    is_remaining_sessions_zero = fields.Boolean(
        string="Remaining Sessions Zero",
        compute="_compute_is_remaining_sessions_zero",
        store=True
    )

    @api.depends('selected_act_id.remaining_sessions')
    def _compute_is_remaining_sessions_zero(self):
        """Check if the remaining sessions for the selected act are zero."""
        for wizard in self:
            wizard.is_remaining_sessions_zero = wizard.selected_act_id.remaining_sessions == 0

    def action_confirm_payment(self):
        """
        Mark the selected act as paid and confirm the appointment.
        Ensure only the current session's amount is updated, not all past sessions.
        """
        # Debugging: Log the selected act ID and its amount before processing
        print(f"Processing payment for selected_act_id: {self.selected_act_id.id}, Amount: {self.selected_act_id.amount}")

        # Mark the selected act as paid
        self.selected_act_id.payed = True

        # Update the amount for the selected act only if it hasn't been set yet
        if not self.selected_act_id.amount:
            self.selected_act_id.amount = self.selected_act_id.act_id.amount

        # Debugging: Log the updated amount after setting it
        print(f"Updated amount for selected_act_id: {self.selected_act_id.id}, New Amount: {self.selected_act_id.amount}")

        # Confirm the appointment
        self.appointment_id.action_confirm()

        return {'type': 'ir.actions.act_window_close'}