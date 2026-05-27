from email.policy import default

from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import ValidationError

class GestionAbonnement(models.Model):
    _name = 'gestion.abonnement'
    _description = 'Abonnements'

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    name = fields.Char(string="Code", compute='_compute_name', store=True, readonly=True)
    appointment_id = fields.Many2one(
        'medical.appointment',
        string="Rendez-vous",
        default=lambda self: self.env.context.get('default_appointment_id')
    )
    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        store=True,
    )
    affictation_ids = fields.Many2many(
        related= 'patient_id.affictation_ids',
        string="Affectation",
        help="Affectation principale du patient"
    )
    sexe = fields.Selection(related= 'patient_id.sexe')

    phone = fields.Char(related= 'patient_id.phone')

    act_ids = fields.Many2one(
        'patient.act.session',
        string="Acte",
        domain="[('patient_id', '=', patient_id)]"
    )
    remise_globale = fields.Float(string="Remise(%)")
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    total_sans_remise = fields.Float(
        string="Prix de pack",
        related="pack_name.amount",
        store=True
    )
    acts = fields.Many2one(
        string="Acte",
        related="act_ids.act_id",
        store=True
    )
    number_of_sessions = fields.Integer(
        string="Nombre de Séance",
        related="pack_name.nombre_seance",
        store=True
    )
    unit_amount = fields.Float(
        string="Montant Unité",
        related="act_ids.unit_amount",
        store=True
    )
    total_avec_remise = fields.Float(
        string="Prix avec Remise",
        compute='_compute_totaux',
        store=True
    )
    used_sessions = fields.Integer(string="Séances Utilisées", default=0)
    remaining_sessions = fields.Integer(
        string="Séances Restantes",
        compute='_compute_remaining_sessions',
        store=True
    )
    date_debut = fields.Date(string="Date de Début", default=fields.Date.today)
    date_fin = fields.Date(string="Date de Fin", compute='_compute_date_fin', store=True, readonly=False)
    date = fields.Date(string="Date", default=fields.Date.today)
    state = fields.Selection(
        selection=[
            ('with_debt', 'Avec Dette'),
            ('without_debt', 'Sans Dette'),
            ('abonnement_end', 'Fin d\'Abonnement'),
        ],
        string="État",
        compute='_compute_state',
        store=True,
    )
    etat = fields.Selection(
        selection=[
            ('ouvert', 'Ouvert'),  # Open
            ('ferme', 'Fermé'),  # Closed
        ],
        string="État",
        # compute='_compute_etat',
        default="ouvert",
        store=True,
        redonly = False,
    )
    # New Fields for Type Abonnement and Pack Validation
    type_abonnement_id = fields.Many2one(
        'type.abonnement',
        string="Type d'Abonnement",
    )
    pack_name = fields.Many2one('pack',
        string="Nom du Pack",
        store=True,
        # domain="[('patient_id', '=', patient_id)]"
    )
    verssement_ids = fields.One2many(
        'verssement',
        'gestion_abonnement_id',
        string="Versements",
    )

    amount_remaining = fields.Float(
        string="Reste à Payer",
        compute='_compute_amount_remaining',
        store=True,
    )
    total_verssement = fields.Float(
        string="Total des Versements",
        compute='_compute_total_verssement',
        store=True,
    )
    intensif_ids = fields.One2many(
        'service.intensif.patient.line',
        'abonnement_id',
        string="Historique des Séance",
        help="Historique des rendez-vous de kinésithérapie pratiqués par le patient."
    )

    # New field: Number of abonnements for the patient
    number_of_abonnements = fields.Integer(
        string="Nombre d'Abonnements",
        compute="_compute_number_of_abonnements",
        store=True,
    )

    @api.depends('patient_id')
    def _compute_number_of_abonnements(self):
        """Compute the total number of abonnements for the patient."""
        for record in self:
            if record.patient_id:
                # Count all abonnements linked to the patient
                record.number_of_abonnements = self.search_count([
                    ('patient_id', '=', record.patient_id.id)
                ])
            else:
                record.number_of_abonnements = 0

    @api.depends('verssement_ids.montant_versse')
    def _compute_total_verssement(self):
        for record in self:
            # Sum up all montant_versse values from related versements
            record.total_verssement = sum(record.verssement_ids.mapped('montant_versse'))

    @api.depends('total_verssement', 'total_avec_remise')
    def _compute_amount_remaining(self):
        for record in self:
            # Calculate remaining amount based on total_verssement
            record.amount_remaining = record.total_avec_remise - record.total_verssement

    @api.depends('remaining_sessions')
    def _compute_etat(self):
        """Compute the state based on remaining sessions."""
        for abonnement in self:
            if abonnement.remaining_sessions > 0:
                abonnement.etat = 'ouvert'  # Open if there are remaining sessions
            else:
                abonnement.etat = 'ferme'  # Closed if no sessions remain

    @api.depends('type_abonnement_id.name')
    def _compute_pack_name(self):
        """Compute the name of the pack based on type_abonnement."""
        for abonnement in self:
            abonnement.pack_name = abonnement.type_abonnement_id.name or "Aucun Pack"

    # @api.constrains('number_of_sessions', 'type_abonnement_id')
    # def _check_number_of_sessions(self):
    #     """Validate that the number_of_sessions matches the nombre_seance in the pack."""
    #     for abonnement in self:
    #         if abonnement.type_abonnement_id and abonnement.type_abonnement_id.pack_id:
    #             pack_nombre_seance = abonnement.type_abonnement_id.pack_id.nombre_seance
    #             if abonnement.number_of_sessions != pack_nombre_seance:
    #                 raise ValidationError(
    #                     f"Le nombre de séances ({abonnement.number_of_sessions}) ne correspond pas "
    #                     f"au nombre de séances défini dans le pack ({pack_nombre_seance})."
    #                 )

    @api.depends('date_debut')
    def _compute_date_fin(self):
        """Compute the end date as one month after the start date."""
        for abonnement in self:
            if abonnement.date_debut:
                abonnement.date_fin = abonnement.date_debut + timedelta(days=30)  # One month later
            else:
                abonnement.date_fin = False

    @api.depends('amount_remaining', 'remaining_sessions')
    def _compute_state(self):
        """Compute the state based on remaining amount and sessions."""
        for abonnement in self:
            if abonnement.remaining_sessions <= 0:
                abonnement.state = 'abonnement_end'
            elif abonnement.amount_remaining > 0:
                abonnement.state = 'with_debt'
            else:
                abonnement.state = 'without_debt'

    @api.depends('number_of_sessions', 'used_sessions')
    def _compute_remaining_sessions(self):
        for abonnement in self:
            abonnement.remaining_sessions = abonnement.number_of_sessions - abonnement.used_sessions

    @api.depends('total_sans_remise', 'remise_globale')
    def _compute_totaux(self):
        for abonnement in self:
            abonnement.total_avec_remise = abonnement.total_sans_remise * (1 - abonnement.remise_globale / 100)

    # @api.depends('total_avec_remise', 'amount_paid')
    # def _compute_amount_remaining(self):
    #     for abonnement in self:
    #         abonnement.amount_remaining = abonnement.total_avec_remise - abonnement.amount_paid

    @api.depends('patient_id', 'date')
    def _compute_name(self):
        for abonnement in self:
            if abonnement.patient_id and abonnement.date:
                first_name = abonnement.patient_id.name.split(" ")[0] if abonnement.patient_id.name else ""
                formatted_date = abonnement.date.strftime("%d/%m/%y")
                abonnement.name = f"ABN/{first_name}/{formatted_date}"
            else:
                abonnement.name = "Nouvel Abonnement"


class Verssement(models.Model):
    _name = 'verssement'
    _description = 'Versements'
    _rec_name = 'name'  # Use the 'name' field as the record's display name

    name = fields.Char(
        string="Référence",
        readonly=True,
        copy=False,
        default='Nouveau Versement',
    )

    gestion_abonnement_id = fields.Many2one(
        'gestion.abonnement',
        string="Abonnement",
        required=True,
        tracking=True,
    )
    patient_id = fields.Many2one(string="Patient",
                             related='gestion_abonnement_id.patient_id',
                             store=True,)
    date_verssement = fields.Date(
        string="Date de Versement",
        default=fields.Date.today,
        tracking=True,
    )
    montant_versse = fields.Float(
        string="Montant Versé",
        required=True,
        tracking=True,
    )
    rest = fields.Float(
        string="Reste à Payer",
        related="gestion_abonnement_id.amount_remaining",
        store=True,
    )
    total = fields.Float(
        string="Total à Payer",
        related="gestion_abonnement_id.total_avec_remise",
        store=True,
    )
    pack_name = fields.Many2one('pack',
                                related="gestion_abonnement_id.pack_name",
        string="Nom du Pack",
        store=True,
        # domain="[('patient_id', '=', patient_id)]"
    )
    @api.depends('montant_versse', 'total')
    def _compute_rest(self):
        for record in self:
            record.rest = record.total - record.montant_versse

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau Versement') == 'Nouveau Versement':
                # Generate a unique sequence for the name (e.g., V0001, V0002)
                vals['name'] = self.env['ir.sequence'].next_by_code('verssement.sequence') or 'Nouveau Versement'
        records = super().create(vals_list)
        # Update caisse.abonnement after creation
        for record in records:
            record._update_caisse_abonnement()
        return records

    def write(self, vals):
        res = super().write(vals)
        # Update caisse.abonnement after modification
        for record in self:
            record._update_caisse_abonnement()
        return res

    def unlink(self):
        # Store dates before deletion
        dates_to_update = set(record.date_verssement for record in self)
        res = super().unlink()
        # Update caisse.abonnement for each affected date
        for date_verssement in dates_to_update:
            caisse = self.env['caisse.abonnement'].search([('date', '=', date_verssement)], limit=1)
            if caisse:
                caisse._compute_totals()
                caisse._compute_verssement_details()
        return res

    def _update_caisse_abonnement(self):
        """Update or create a caisse.abonnement record for the same date."""
        for record in self:
            if record.date_verssement:
                caisse = self.env['caisse.abonnement'].search([
                    ('date', '=', record.date_verssement)
                ], limit=1)
                if not caisse:
                    # Create a new caisse.abonnement record if none exists for the date
                    caisse = self.env['caisse.abonnement'].create({
                        'date': record.date_verssement
                    })
                # Recompute totals and details for the caisse.abonnement record
                caisse._compute_totals()
                caisse._compute_verssement_details()