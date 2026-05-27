# transfer_wizard.py
from odoo import models, fields, api


class PatientTransferWizard(models.TransientModel):
    _name = 'patient.transfer.wizard'
    _description = 'Wizard de transfert de patient'

    target_appointment_id = fields.Many2one(
        'kinesitherapy.appointment',
        string="Nouveau Rendez-vous",
        required=True,
        domain="[('id', '!=', current_appointment_id)]"
    )
    current_appointment_id = fields.Many2one(
        'kinesitherapy.appointment',
        default=lambda self: self.env.context.get('active_id')
    )
    selected_act_id = fields.Many2one(
        'kinesitherapy.appointment.selected.act',
        required=True
    )

    def action_confirm_transfer(self):
        # Récupérer l'ancien et le nouveau RDV
        old_appointment = self.current_appointment_id
        new_appointment = self.target_appointment_id

        # Copier l'acte sélectionné
        new_act = self.selected_act_id.copy({
            'appointment_id': new_appointment.id
        })

        # Supprimer l'ancien acte
        self.selected_act_id.unlink()

        return {'type': 'ir.actions.act_window_close'}