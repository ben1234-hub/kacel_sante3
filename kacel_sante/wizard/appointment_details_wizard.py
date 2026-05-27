from odoo import models, fields, api

class AppointmentDetailsWizard(models.TransientModel):
    _name = 'banliotherapie.appointment.details.wizard'
    _description = 'Appointment Details Wizard'

    appointment_id = fields.Many2one('banliotherapie.appointment', string="Appointment")
    patient_line_ids = fields.One2many(
        related='appointment_id.patient_line_ids',
        string="Patients",
        readonly=True,
    )
    total_patients = fields.Integer(
        compute='_compute_total_patients',
        string="Total Patients",
        store=False,
    )

    @api.depends('patient_line_ids')
    def _compute_total_patients(self):
        for record in self:
            record.total_patients = len(record.patient_line_ids)