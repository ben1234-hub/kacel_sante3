from odoo import models, fields, api
from datetime import date, timedelta

class MedicalAppointment(models.Model):
    _name = 'medical.appointment'
    _description = 'Rendez-vous Médical'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Enable chatter and activities

    name = fields.Char(string='Code', compute='_compute_name', store=True, tracking=True)
    patient_id = fields.Many2one('res.partner', string='Patient', required=True,)
    patient_date_naissance = fields.Date(related='patient_id.date_naissance',
                                         string="Date de naissance", readonly=False)
    patient_age = fields.Integer(related='patient_id.age', string="Âge",
                                 readonly=False)
    patient_sexe = fields.Selection(related='patient_id.sexe', string="Sexe",
                                 readonly=False)
    patient_phone = fields.Char(related='patient_id.phone',
                                string="Téléphone", readonly=False)
    patient_category_id = fields.Many2many(related='patient_id.category_id', string="Étiquettes", readonly=False)
    patient_wilaya = fields.Selection(related='patient_id.wilaya',
                                      string="Wilaya", readonly=False)

    affictation_ids = fields.Many2many(
        related='patient_id.affictation_ids',
        string="Affectation",
        readonly=False,
        tracking = True
    )
    appointment_date = fields.Datetime(string='Date et Heure du Rendez-vous',
                                       default=fields.Date.today,
                                       required=True, tracking=True)
    appointment_date_only = fields.Date(string='Date du Rendez-vous (Date Only)',
                                        compute='_compute_appointment_date_only',
                                        store=True)
    amount = fields.Monetary(
        string="Amount",
        currency_field='currency_id',
        default=2000,  # Set default value to 2000
        tracking=True,
        help="The total amount for the appointment."
    )
    has_prior_consultation = fields.Boolean(
        string="Has Prior Consultation",
        compute="_compute_has_prior_consultation",
        store=True,
        help="Indicates if the patient has had a prior consultation."
    )
    amount_display = fields.Char(
        string="Amount Display",
        compute="_compute_amount_display",
        help="Displays either the amount or 'Control' for free consultations."
    )
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'En Attente'),
        ('consult', 'En consultation'),
        ('endconsult', 'Consultation Terminée'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé')
    ], string='État', default='draft', tracking=True)

    # Champs relationnels pour les questionnaires médicaux et les actes de kinésithérapie
    medical_questionnaire_ids = fields.One2many(
        related='patient_id.medical_questionnaire_ids',  # Point vers le champ dans res.partner
        string="Questionnaires Médicaux",
        readonly=False,  # Permettre la modification
    )

    patient_act_session_ids = fields.One2many(
        'patient.act.session',  # Related model
        'appointment_id',  # Inverse field
        string="Actes de Kinésithérapie",tracking=True
    )
    act_ids = fields.One2many( related='patient_id.patient_act_session_ids',
        string="Actes de Kinésithérapie",
        readonly=False,tracking=True)

    selected_act_id = fields.Many2one('patient.act.session', string="Sélectionner un Acte")

    # etage = fields.Char(string="Étage", compute='_compute_etage', readonly=True, store=True)

    total_medical_amount = fields.Monetary(
        string="Total Medical Amount",
        currency_field='currency_id',
        compute='_compute_total_medical_amount',
        store=True,
    )
    history_caisse_id = fields.Many2one('history.caisse',
                                        string='History Caisse', readonly=True)
    total_amount_casse = fields.Monetary(related='history_caisse_id.total_amount')

    discount = fields.Float(
        string="Remise (%)",
        default=0.0,
        help="Pourcentage de remise appliqué"
    )

    discounted_amount = fields.Monetary(
        string="Montant après remise",
        compute='_compute_discounted_amount',
        store=True
    )
    abonnement_ids = fields.One2many(
        'gestion.abonnement',
        'appointment_id',
        string="Abonnements",
    context = {'default_patient_id': patient_id}
    )
    @api.depends('amount', 'discount')
    def _compute_discounted_amount(self):
        for record in self:
            record.discounted_amount = record.amount * (1 - record.discount / 100.0)

    @api.depends('appointment_date')
    def _compute_appointment_date_only(self):
        """Compute the date part of the appointment_date field."""
        for record in self:
            if record.appointment_date:
                # Convert the Datetime field to a Date field
                record.appointment_date_only = fields.Date.to_date(record.appointment_date)
            else:
                record.appointment_date_only = False

    @api.depends('appointment_date')
    def _compute_total_medical_amount(self):
        for record in self:
            if record.appointment_date:
                selected_date = fields.Date.to_date(record.appointment_date)
                appointments = self.search([
                    ('appointment_date', '>=', selected_date),
                    ('appointment_date', '<', selected_date + timedelta(days=1))
                ])
                total_amount = 0
                for appointment in appointments:
                    if not appointment.has_prior_consultation and not any(
                            category.free for category in appointment.patient_id.category_id):
                        total_amount += appointment.discounted_amount  # Changé ici
                record.total_medical_amount = total_amount
            else:
                record.total_medical_amount = 0

    @api.depends('date_naissance')
    def _compute_age(self):
        today = date.today()
        for patient in self:
            if patient.date_naissance:
                patient.age = today.year - patient.date_naissance.year - ((today.month, today.day) < (patient.date_naissance.month, patient.date_naissance.day))
            else:
                patient.age = 0

    # @api.depends('patient_id.affictation_ids.etage')
    # def _compute_etage(self):
    #     for record in self:
    #         record.etage = record.patient_id.affictation_ids.etage or "00"

    @api.depends('patient_id')
    def _compute_has_prior_consultation(self):
        """Compute if the patient has had a prior consultation."""
        for record in self:
            if isinstance(record.id, models.NewId):
                # Skip computation for new records (not yet saved to the database)
                record.has_prior_consultation = False
            else:
                # Check if the patient has any prior appointments in the 'done' state
                prior_appointments = self.search([
                    ('patient_id', '=', record.patient_id.id),
                    ('state', '=', 'done'),
                    ('id', '!=', record.id)  # Exclude the current appointment
                ], limit=1)
                record.has_prior_consultation = bool(prior_appointments)

    @api.depends('discounted_amount', 'has_prior_consultation', 'patient_id.category_id.free')
    def _compute_amount_display(self):
        for record in self:
            if record.has_prior_consultation:
                record.amount_display = "Control"
            elif any(category.free for category in record.patient_id.category_id):
                record.amount_display = "VIP"
            else:
                record.amount_display = f"{record.discounted_amount} {record.currency_id.symbol}"

    @api.depends('patient_id', 'affictation_ids', 'appointment_date')
    def _compute_name(self):
        for record in self:
            # Récupérer le nom du patient
            patient_name = record.patient_id.name or ''

            # Extraire uniquement le prénom (premier mot du nom complet)
            first_name = patient_name.split(' ')[0] if patient_name else ''

            # Formater la date au format "JJMMAAHH" (Jour/Mois/Année/Heure)
            # if record.appointment_date:
            #     # date_str = record.appointment_date.strftime('%d%m%y%H')
            if record.appointment_date:
                date_str = record.appointment_date.strftime("%d/%m/%y")
                hour_str = str(record.appointment_date.hour + 1)
                date_str_total = f"{date_str}/{hour_str}"
            else:
                date_str_total = '00000000'

            # Construire le nom final
            record.name = f"{first_name}/{date_str_total}"

    def _update_history_caisse(self):
        """Lie le rendez-vous à l'historique de caisse correspondant à sa date."""
        for appointment in self:
            if not appointment.appointment_date:
                continue
            # Convertir la date du rendez-vous en date (sans heure)
            appointment_date = fields.Date.to_date(appointment.appointment_date)
            # Rechercher ou créer l'historique de caisse pour cette date
            history_caisse = self.env['history.caisse'].search([
                ('date', '=', appointment_date)
            ], limit=1)
            if not history_caisse:
                history_caisse = self.env['history.caisse'].create({'date': appointment_date})
            # Lier le rendez-vous à l'historique de caisse
            appointment.history_caisse_id = history_caisse.id

    @api.model
    def create(self, vals):
        # Créer le rendez-vous
        print('method create RDV')
        appointment = super(MedicalAppointment, self).create(vals)
        # Lier à l'historique de caisse
        appointment._update_history_caisse()
        return appointment

    def action_confirm(self):
        for record in self:
            if record.state == 'draft':
                record.state = 'confirm'
        return True

    def action_consult(self):
        """Transition to the 'consult' state."""
        for record in self:
            if record.state == 'confirm':
                record.state = 'consult'
        return True

    def action_endconsult(self):
        """Transition to the 'endconsult' state."""
        for record in self:
            if record.state == 'consult':
                record.state = 'endconsult'
        return True

    # def action_done(self):
    #     for record in self:
    #         if record.state == 'endconsult':
    #             record.state = 'done'
    #             # Find or create a history_caisse record for today
    #             today = fields.Date.today()
    #             history_caisse = self.env['history.caisse'].search([('date', '=', today)], limit=1)
    #             if not history_caisse:
    #                 history_caisse = self.env['history.caisse'].create({'date': today})
    #             # Link the appointment to the history_caisse record
    #             record.history_caisse_id = history_caisse.id
    #     return True

    def action_done(self):
        for record in self:
            if record.state == 'endconsult':
                record.state = 'done'
                # Utiliser la date du rendez-vous (appointment_date) au lieu de today()
                if record.appointment_date:
                    appointment_date = fields.Date.to_date(record.appointment_date)
                    history_caisse = self.env['history.caisse'].search([
                        ('date', '=', appointment_date)
                    ], limit=1)
                    if not history_caisse:
                        history_caisse = self.env['history.caisse'].create({'date': appointment_date})
                    record.history_caisse_id = history_caisse.id
        return True

    def action_cancel(self):
        for record in self:
            if record.state in ['draft', 'confirm', 'consult', 'endconsult']:
                record.state = 'cancel'
        return True

    def action_reopen(self):
        for record in self:
            if record.state == 'done':
                record.state = 'consult'
        return True