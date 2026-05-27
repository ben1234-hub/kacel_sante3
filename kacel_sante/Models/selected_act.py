from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date
from datetime import timedelta

class KinesitherapyAppointmentSelectedAct(models.Model):
    _name = 'kinesitherapy.appointment.selected.act'
    _description = 'Actes sélectionnés pour un rendez-vous'

    appointment_id = fields.Many2one('kinesitherapy.appointment', string="RDV", required=True, ondelete='cascade')
    appointment_name = fields.Char(related="appointment_id.name", string="RDV")
    appointment_date = fields.Datetime(related="appointment_id.appointment_date",string="Date et heure du rendez-vous")
    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        required=True,
        domain="[('patient_act_session_ids', '!=', False)]"  # Filter patients with at least one act
    )
    patient_phone = fields.Char(related="patient_id.phone", string="Phone", help="Phone number of the patient")
    payed = fields.Boolean(string="Payed", default=False)
    act_id = fields.Many2one(
        'kinesitherapy.act',
        string="Acte de Kinésithérapie",
        required=True,
        domain="[('id', 'in', available_act_ids)]"
    )
    abonnement_ids = fields.One2many(
        'gestion.abonnement',
        'patient_id',
        string="Abonnements"
    )
    remaining_sessions = fields.Integer(
        string="Séances Restantes",
        compute="_compute_remaining_and_number_of_sessions",
        store=True
    )
    number_of_sessions = fields.Integer(
        string="Nombre de Séances",
        compute="_compute_remaining_and_number_of_sessions",
        store=True
    )
    amount = fields.Float(string="Montant", compute="_compute_amount", readonly=True, store=True)
    # Add a display field for "VIP" or the amount
    amount_display = fields.Char(string="Montant", compute="_compute_amount_display", readonly=True, store=True)
    available_act_ids = fields.Many2many(
        'kinesitherapy.act',
        string="Actes disponibles",
        compute="_compute_available_act_ids",
        store=False  # Ne pas stocker ce champ en base de données
    )

    @api.depends('act_id.amount', 'patient_id.category_id.free', 'patient_id.abonnement_ids.remaining_sessions')
    def _compute_amount(self):
        """Calculer le montant à 0 si l'abonnement est actif."""
        for record in self:
            if any(category.free for category in record.patient_id.category_id):
                record.amount = 0
            else:
                is_abonne = any(
                    abonnement.acts.id == record.act_id.id and abonnement.remaining_sessions >= 0
                    for abonnement in record.patient_id.abonnement_ids
                )
                record.amount = 0 if is_abonne else record.act_id.amount

    @api.depends('amount', 'patient_id.category_id.free', 'patient_id.abonnement_ids.remaining_sessions')
    def _compute_amount_display(self):
        """Display 'Abonné' if the patient has an active abonnement for this act."""
        for record in self:
            if any(category.free for category in record.patient_id.category_id):
                record.amount_display = "VIP"
            else:
                is_abonne = any(
                    abonnement.acts.id == record.act_id.id and abonnement.remaining_sessions >= 0
                    for abonnement in record.patient_id.abonnement_ids
                )
                if is_abonne:
                    record.amount_display = "Abonné"
                else:
                    record.amount_display = f"{record.amount} {record.appointment_id.currency_id.symbol}"

    @api.depends('patient_id')
    def _compute_available_act_ids(self):
        """Compute available acts based on the selected patient."""
        for record in self:
            if record.patient_id:
                record.available_act_ids = record.patient_id.patient_act_session_ids.mapped('act_id')
            else:
                record.available_act_ids = False

    @api.depends('patient_id', 'act_id')
    def _compute_remaining_and_number_of_sessions(self):
        """Compute remaining and total number of sessions for the selected patient and act."""
        for record in self:
            if record.patient_id and record.act_id:
                abonnement = record.patient_id.abonnement_ids.filtered(
                    lambda a: a.acts.id == record.act_id.id
                )
                if abonnement:
                    record.remaining_sessions = sum(ab.remaining_sessions for ab in abonnement)
                    record.number_of_sessions = sum(ab.number_of_sessions for ab in abonnement)
                else:
                    record.remaining_sessions = 0
                    record.number_of_sessions = 0
            else:
                record.remaining_sessions = 0
                record.number_of_sessions = 0

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.patient_id and record.act_id:
            abonnements_actifs = record.patient_id.abonnement_ids.filtered(
                lambda a: a.acts.id == record.act_id.id and a.remaining_sessions > 0
            )
            if abonnements_actifs:
                record.payed = True
        return record

    def write(self, vals):
        for record in self:
            if 'act_id' in vals or 'patient_id' in vals:
                patient = record.patient_id
                act = record.act_id
                abonnements_actifs = patient.abonnement_ids.filtered(
                    lambda a: a.acts.id == act.id and a.remaining_sessions > 0
                )
                if abonnements_actifs:
                    vals['payed'] = True
        return super().write(vals)

    def action_transfer_patient(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transférer le patient',
            'res_model': 'patient.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_selected_act_id': self.id,
                'default_current_appointment_id': self.appointment_id.id
            }
        }

class ActPracticeCount(models.Model):
    _name = 'act.practice.count'
    _description = 'Nombre de pratiques par acte'

    date = fields.Date(string="Date", required=True)
    act_details_ids = fields.One2many('act.practice.details', 'practice_count_id', string="Act Details")
    daily_total = fields.Monetary(string="Total of the Day", currency_field='currency_id', compute="_compute_daily_total", store=True)

    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)

    @api.depends('act_details_ids.total')
    def _compute_daily_total(self):
        """Compute the total amount for all acts on the same day."""
        for record in self:
            record.daily_total = sum(act.total for act in record.act_details_ids)


class ActPracticeDetails(models.Model):
    _name = 'act.practice.details'
    _description = 'Détails des pratiques par acte'

    practice_count_id = fields.Many2one('act.practice.count', string="Practice Count", required=True, ondelete='cascade')
    act_id = fields.Many2one('kinesitherapy.act', string="Acte", required=True)
    count = fields.Integer(string="Nombre de pratiques", default=0)
    unit_amount = fields.Monetary(string="Montant unitaire", currency_field='currency_id')
    total = fields.Monetary(string="Total", currency_field='currency_id', compute="_compute_total", store=True)

    currency_id = fields.Many2one('res.currency', string="Currency", related='practice_count_id.currency_id')

    @api.depends('count', 'unit_amount')
    def _compute_total(self):
        """Compute the total amount for the act."""
        for record in self:
            record.total = record.count * record.unit_amount
