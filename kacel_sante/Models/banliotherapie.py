from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from datetime import timedelta


class BanliotherapieAppointment(models.Model):
    _name = 'banliotherapie.appointment'
    _description = 'Rendez-vous de Banliothérapie'

    name = fields.Char(string="Nom", compute='_compute_name', store=True, readonly=True)
    appointment_date = fields.Datetime(string="Date et heure", required=True)
    duration = fields.Float(string="Durée (heures)", default=1, required=True)
    end_date = fields.Datetime(string="Fin", compute='_compute_end_date', store=True)
    # patient_id = fields.Many2one('res.partner', string="Patient", required=True)
    patient_line_ids = fields.One2many(
        'banliotherapie.appointment.patient',
        'appointment_id',
        string="Patients"
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string="Statut", default='draft')

    history_caisse_id = fields.Many2one(
        'history.caisse.banliotherapie',
        string='Historique Caisse',
        readonly=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )
    amount = fields.Monetary(
        string="Montant",
        default=1500,
        required=True
    )

    total_amount = fields.Float(
        string="Montant Total",
        compute='_compute_total_amount',
        store=True
    )

    all_patients_paid = fields.Boolean(
        string="Tous payés",
        compute='_compute_all_paid',
        store=True
    )

    planning_slot_id = fields.Many2one(
        'planning.slot',
        string="Créneau horaire",
        compute='_compute_planning_slot',
        store=True,
        readonly=False
    )
    appointment_date_weekday = fields.Char(  # Changer de Integer à Char
        compute='_compute_appointment_date_weekday',
        store=True,
        string="Jour de la semaine (0-6)"
    )
    time_of_day = fields.Selection([
        ('morning', 'Matin'),
        ('evening', 'Soir')
    ], compute='_compute_time_of_day', store=True)

    total_amount_from_history = fields.Monetary(
        string="Total Amount From History",
        compute="_compute_total_amount_from_history",
        store=False,
        currency_field='currency_id'
    )
    @api.depends('history_caisse_id')
    def _compute_total_amount_from_history(self):
        for record in self:
            if record.history_caisse_id:
                record.total_amount_from_history = record.history_caisse_id.total_amount
            else:
                record.total_amount_from_history = 0.0

    def open_caisse_history(self):
        self.ensure_one()
        if self.history_caisse_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Historique Caisse',
                'res_model': 'history.caisse.banliotherapie',
                'view_mode': 'form',
                'res_id': self.history_caisse_id.id,
                'target': 'current',
            }
        else:
            raise UserError("Aucune historique de caisse n'est associée à cet rendez-vous.")

    @api.depends('appointment_date')
    def _compute_appointment_date_weekday(self):
        for rec in self:
            if rec.appointment_date:
                rec.appointment_date_weekday = str(rec.appointment_date.weekday())  # Convertir en string
            else:
                rec.appointment_date_weekday = False

    @api.depends('appointment_date')
    def _compute_time_of_day(self):
        for rec in self:
            if rec.appointment_date:
                hour = rec.appointment_date.hour
                rec.time_of_day = 'morning' if 7.00 <= hour < 11.00 else 'evening'
            else:
                rec.time_of_day = False

    @api.depends('appointment_date')
    def _compute_planning_slot(self):
        for rec in self:
            if rec.appointment_date:
                # Calcul du jour de la semaine (0=lundi, 6=dimanche)
                weekday = str(rec.appointment_date.weekday())
                # Détermination matin/soir
                hour = rec.appointment_date.hour
                time_of_day = 'morning' if 7.00 <= hour < 11.00 else 'evening'

                # Recherche du créneau correspondant
                slot = self.env['planning.slot'].search([
                    ('day_of_week', '=', weekday),
                    ('time_of_day', '=', time_of_day)
                ], limit=1)

                rec.planning_slot_id = slot
            else:
                rec.planning_slot_id = False

    @api.constrains('planning_slot_id', 'patient_line_ids')
    def _check_gender_compatibility(self):
        for appointment in self:
            if appointment.planning_slot_id.allowed_gender != 'both':
                allowed_gender = appointment.planning_slot_id.allowed_gender
                for patient in appointment.patient_line_ids:
                    if patient.patient_id.sexe != allowed_gender:
                        raise ValidationError(
                            f"Le patient {patient.patient_id.name} ne correspond pas "
                            f"au genre autorisé pour ce créneau ({allowed_gender})!"
                        )

    @api.depends('patient_line_ids.paid')
    def _compute_all_paid(self):
        for record in self:
            if record.patient_line_ids:
                record.all_patients_paid = all(record.patient_line_ids.mapped('paid'))
            else:
                record.all_patients_paid = False

    def action_mark_all_paid(self):
        for patient_line in self.patient_line_ids:
            patient_line.paid = True

    @api.depends('patient_line_ids.amount')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(line.amount for line in record.patient_line_ids)

    @api.depends('appointment_date')
    def _compute_name(self):
        for record in self:
            if record.appointment_date:
                date_str = record.appointment_date.strftime("%d/%m/%y")
                hour_str = str(record.appointment_date.hour + 1)
                record.name = f"BAN{date_str}/{hour_str}"
            else:
                record.name = "Nouveau Rendez-vous"

    @api.depends('appointment_date', 'duration')
    def _compute_end_date(self):
        for record in self:
            if record.appointment_date and record.duration:
                record.end_date = record.appointment_date + timedelta(hours=record.duration)
            else:
                record.end_date = False

    def _update_history_caisse(self):
        for appointment in self:
            if appointment.appointment_date:
                date = fields.Date.to_date(appointment.appointment_date)
                history = self.env['history.caisse.banliotherapie'].search(
                    [('date', '=', date)], limit=1)
                if not history:
                    history = self.env['history.caisse.banliotherapie'].create({'date': date})
                appointment.history_caisse_id = history.id

    @api.model
    def create(self, vals):
        # Créer le rendez-vous
        appointment = super(BanliotherapieAppointment, self).create(vals)
        # Mettre à jour l'historique de caisse
        appointment._update_history_caisse()
        return appointment

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        if not self.all_patients_paid:
            raise UserError("Tous les patients doivent être payés avant de terminer le rendez-vous !")
        self.state = 'done'
        self._update_history_caisse()

    def action_cancel(self):
        self.state = 'canceled'
        self.history_caisse_id = False


class HistoryCaisseBanliotherapie(models.Model):
    _name = 'history.caisse.banliotherapie'
    _description = 'Historique Caisse Banliothérapie'

    date = fields.Date(string="Date", required=True)
    appointment_ids = fields.One2many(
        'banliotherapie.appointment',
        'history_caisse_id',
        string="Rendez-vous"
    )
    total_amount = fields.Monetary(
        string="Total",
        currency_field='currency_id',
        compute='_compute_total',
        store=True
    )
    number_of_appointments = fields.Integer(
        string="Nombre de RDV",
        compute='_compute_total',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('appointment_ids', 'appointment_ids.amount')
    def _compute_total(self):
        for record in self:
            record.total_amount = sum(record.appointment_ids.mapped('total_amount'))
            record.number_of_appointments = len(record.appointment_ids)

class BanliotherapieAppointmentPatient(models.Model):
    _name = 'banliotherapie.appointment.patient'
    _description = 'Patients dans un rendez-vous Banliothérapie'

    appointment_id = fields.Many2one('banliotherapie.appointment', required=True)
    patient_id = fields.Many2one('res.partner',
                                 string="Patient",
                                 required=True)
    phone = fields.Char(related='patient_id.phone', string="Téléphone", readonly=True)
    age = fields.Integer(related='patient_id.age', string="Âge", readonly=True)
    sexe = fields.Selection(related='patient_id.sexe', string="Sexe", readonly=True)
    tarif_id = fields.Many2one('gestion.tarif', string="Tarif Appliqué", required=True)
    amount = fields.Float(related='tarif_id.montant', string="Montant", readonly=True)
    paid = fields.Boolean(string="Payé", default=False)
    currency_id = fields.Many2one(
        'res.currency',
        string="Devise",
        default=lambda self: self.env.company.currency_id
    )

    def action_change_appointment(self):
        # Check if original appointment is in done/canceled
        if self.appointment_id.state in ['done', 'canceled']:
            raise UserError("Impossible de modifier un rendez-vous terminé ou annulé !")
        return {
            'type': 'ir.actions.act_window',
            'name': 'Changer le Rendez-vous',
            'res_model': 'change.appointment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_patient_line_id': self.id,
                'default_new_appointment_id': self.appointment_id.id,
            },
        }

class ChangeAppointmentWizard(models.TransientModel):
    _name = 'change.appointment.wizard'
    _description = 'Wizard to Change Patient Appointment'

    patient_line_id = fields.Many2one(
        'banliotherapie.appointment.patient',
        required=True,
        default=lambda self: self.env.context.get('default_patient_line_id')
    )
    new_appointment_id = fields.Many2one(
        'banliotherapie.appointment',
        string="Nouveau Rendez-vous",
        required=True,
        # Dynamic domain with today's date in user's timezone
        domain=lambda self: [
            ('state', '=', 'confirmed'),
            ('appointment_date', '>=', fields.Date.context_today(self))
        ]
    )

    def action_confirm(self):
        self.ensure_one()
        # Gender validation (existing code)
        patient_gender = self.patient_line_id.patient_id.sexe
        slot_gender = self.new_appointment_id.planning_slot_id.allowed_gender
        if patient_gender != slot_gender:
            raise ValidationError(
                f"Le patient {self.patient_line_id.patient_id.name} ne correspond pas au genre autorisé ({slot_gender}) !"
            )
        # Update the appointment
        self.patient_line_id.appointment_id = self.new_appointment_id
        return {'type': 'ir.actions.act_window_close'}