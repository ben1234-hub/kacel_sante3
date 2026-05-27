from odoo import models, fields, api
from datetime import date

class HistoryCaisse(models.Model):
    _name = 'history.caisse'
    _description = 'Historique de Caisse'
    _order = 'date desc'

    date = fields.Date(string='Date', compute='_compute_date', store=True)
    appointment_ids = fields.One2many('medical.appointment', 'history_caisse_id', string='Appointments')
    kinesitherapy_appointment_ids = fields.One2many('kinesitherapy.appointment', 'history_caisse_id', string='Kinesitherapy Appointments')
    total_amount = fields.Monetary(string='Montant Total', currency_field='currency_id', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    number_of_appointments = fields.Integer(string='Nombre des RDVs Medical',
                                            compute='_compute_number_of_appointments',
                                            store=True)
    number_of_appointments_kinesitherapy = fields.Integer(string='Nombre des RDVs kinesitherapy',
                                            compute='_compute_number_of_appointments_kinesitherapy',
                                            store=True)
    amount_display = fields.Char(
        string="Amount Display",
        compute="_compute_amount_display",
        help="Displays either the amount or 'Control' for free consultations."
    )
    total_medical_amount = fields.Monetary(
        string="Total Medical",
        currency_field='currency_id',
        compute='_compute_total_medical_amount',
        store=True,
    )

    total_kinesitherapy_amount = fields.Monetary(
        string="Total Kinésithérapie",
        currency_field='currency_id',
        compute='_compute_total_kinesitherapy_amount',
        store=True,
    )

    # Update the depends and computation for total_amount
    @api.depends('total_medical_amount', 'total_kinesitherapy_amount')
    def _compute_total_amount(self):
        """Calcule le montant total combiné avec abonnements."""
        for record in self:
            record.total_amount = (
                    record.total_medical_amount
                    + record.total_kinesitherapy_amount
            )

    @api.depends('appointment_ids.appointment_date','kinesitherapy_appointment_ids.appointment_date')
    def _compute_date(self):
        """Compute the date based on the appointment_date of the linked appointments."""
        for record in self:
            if record.appointment_ids:
                # Use the appointment_date of the first linked appointment
                record.date = fields.Date.to_date(record.appointment_ids[0].appointment_date)
            elif record.kinesitherapy_appointment_ids:
                # Use the appointment_date of the first linked appointment
                record.date = fields.Date.to_date(record.kinesitherapy_appointment_ids[0].appointment_date)
                # print('in the fucking method')
            else:
                record.date = False

    @api.depends('appointment_ids', 'appointment_ids.discounted_amount', 'appointment_ids.has_prior_consultation', 'appointment_ids.patient_id.category_id.free')
    def _compute_total_medical_amount(self):
        """Calcule le montant total des rendez-vous médicaux (hors consultations gratuites)."""
        for record in self:
            paid_medical = record.appointment_ids.filtered(
                lambda a: not a.has_prior_consultation
                and not any(cat.free for cat in a.patient_id.category_id)
            )
            record.total_medical_amount = sum(paid_medical.mapped('discounted_amount'))

    @api.depends('kinesitherapy_appointment_ids', 'kinesitherapy_appointment_ids.total_selected_amount')
    def _compute_total_kinesitherapy_amount(self):
        """Calcule le montant total des rendez-vous de kinésithérapie."""
        for record in self:
            record.total_kinesitherapy_amount = sum(
                record.kinesitherapy_appointment_ids.mapped('total_selected_amount')
            )

    # Correction du bug dans _compute_number_of_appointments_kinesitherapy
    @api.depends('kinesitherapy_appointment_ids')
    def _compute_number_of_appointments_kinesitherapy(self):
        for record in self:
            record.number_of_appointments_kinesitherapy = len(record.kinesitherapy_appointment_ids)

    @api.depends('appointment_ids')
    def _compute_number_of_appointments(self):
        """Compute the number of linked appointments."""
        for record in self:
            record.number_of_appointments = len(record.appointment_ids)

