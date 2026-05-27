from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError

class ServiceIntensif(models.Model):
    _name = 'service.intensif'
    _description = 'Service Intensif'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Nom", compute='_compute_name', required=True, tracking=True)
    start_date = fields.Datetime(
        string="Date et Heure de Début",
        default=lambda self: fields.Datetime.now(),
        required=True,
        tracking=True
    )
    duration = fields.Float(
        string="Durée (heures)",
        default=1.0,
        required=True,
        tracking=True
    )
    end_date = fields.Datetime(
        string="Date et Heure de Fin",
        compute="_compute_end_date",
        store=True,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string="État", default='draft', tracking=True)
    patient_line_ids = fields.One2many(
        'service.intensif.patient.line',
        'service_intensif_id',
        string="Lignes des Patients",
        tracking=True
    )
    abonnement_id = fields.Many2one(
        'gestion.abonnement',
        string="Abonnement",
        domain="[('patient_id', '=', patient_line_ids.patient_id)]",
        tracking=True
    )
    affiction_ids = fields.Many2many(
        'affiction',
        string="Affictions Acceptées",
        help="Affictions acceptées pour ce service intensif."
    )

    @api.depends('start_date')
    def _compute_name(self):
        for record in self:
            if record.start_date:
                date_str = record.start_date.strftime("%d/%m/%y")
                hour_str = str(record.start_date.hour +1)
                record.name = f"INT{date_str}/{hour_str}"
            else:
                record.name = "Nouveau"

    @api.model
    def create(self, vals):
        # Fetch the default affictions from the configuration
        config = self.env['service.intensif.config'].search([], limit=1)
        if config and config.default_affiction_ids:
            vals['affiction_ids'] = [(6, 0, config.default_affiction_ids.ids)]
        return super(ServiceIntensif, self).create(vals)

    @api.depends('start_date', 'duration')
    def _compute_end_date(self):
        for record in self:
            if record.start_date and record.duration:
                record.end_date = record.start_date + timedelta(hours=record.duration)
            else:
                record.end_date = False

    @api.model
    def get_available_patients(self):
        """Return patients with valid affictation_ids for this service."""
        # Example: Only patients with affictation_ids matching "Intensif" or "Reeducation"
        valid_affictions = self.env['affiction'].search([('name', 'in', ['Intensif', 'Reeducation'])])
        return self.env['res.partner'].search([
            ('affictation_ids', 'in', valid_affictions.ids),
            ('id', 'not in', self.patient_line_ids.mapped('patient_id').ids)  # Exclude already selected patients
        ])

    def action_confirm(self):
        """Confirm the service and create planing_kines records."""
        for record in self:

            # Update the state
            record.state = 'confirmed'

    def action_done(self):
        for record in self:
            # Get all available kinesitherapists
            # Get all available kinesitherapists
            kinesitherapists = self.env['kinesitherapist'].search([])
            if not kinesitherapists:
                raise ValidationError("Aucun kinésithérapeute disponible pour la planification.")

            # Create a list of patients to assign
            patients = [line.patient_id for line in record.patient_line_ids]

            # Check if there are enough kinesitherapists for the number of patients
            if len(patients) > len(kinesitherapists):
                raise ValidationError("Pas assez de kinésithérapeutes disponibles pour tous les patients.")

            # Create the planing.kines record
            planing_kines = self.env['planing.kines'].create({
                'start_date': record.start_date,
                'service_intensif_id': record.id,
            })

            # Assign a unique kinesitherapist to each patient
            for i, patient in enumerate(patients):
                kinesitherapist = kinesitherapists[i % len(kinesitherapists)]  # Cycle through kinesitherapists
                self.env['planing.kines.line'].create({
                    'planing_kines_id': planing_kines.id,
                    'patient_id': patient.id,
                    'kinesitherapist_id': kinesitherapist.id,
                })
            for line in record.patient_line_ids:
                # Deduct one session from the patient's subscription
                abonnement = self.env['gestion.abonnement'].search([
                    ('patient_id', '=', line.patient_id.id),
                    ('remaining_sessions', '>', 0)
                ], limit=1)
                if abonnement:
                    abonnement.remaining_sessions -= 1
                    abonnement.used_sessions += 1
            record.state = 'done'

    def action_cancel(self):
        for record in self:
            record.state = 'canceled'

    def open_patients(self):
        """Open the list of patients with matching affictions."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Patients',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('affictation_ids', 'in', self.affiction_ids.ids)],
            'context': {'default_affiction_ids': self.affiction_ids.ids},
        }

class ServiceIntensifPatientLine(models.Model):
    _name = 'service.intensif.patient.line'
    _description = 'Ligne des Patients pour Service Intensif'

    service_intensif_id = fields.Many2one(
        'service.intensif',
        string="Service Intensif",
        required=True,
        ondelete='cascade'
    )
    affiction_ids = fields.Many2many(
        related="service_intensif_id.affiction_ids",
        string="Affictions Acceptées",
        help="Affictions acceptées pour ce service intensif."
    )
    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        required=True,
        domain="[('id', 'in', suitable_patient_ids)]",
    )
    name_arab = fields.Char(string="الاسم الكامل",
                            related="patient_id.name_arab",)

    abonnement_id = fields.Many2one(
        'gestion.abonnement',
        string="Abonnement",
        compute="_compute_abonnement_id",
        store=True,
        readonly=False
        # domain="[('patient_id', '=', patient_id), ('remaining_sessions', '>', 0)]"
    )
    type_abonnement_id = fields.Many2one(
        related="abonnement_id.pack_name.type_abonnement_id",
        string="Type d'Abonnement",
    )
    pack_name = fields.Char(
        string="Nom du Pack",
        related="abonnement_id.pack_name.name",
        readonly=True
    )
    total_verssement = fields.Float(
        string="Total des Versements",
        related="abonnement_id.total_verssement",
        store=True,
    )
    total_avec_remise = fields.Float(
        string="Prix avec Remise",
        related="abonnement_id.total_avec_remise",
        store=True
    )
    used_sessions = fields.Integer(string="Séances Utilisées",
                                   related="abonnement_id.used_sessions",
                                   default=0)
    etat = fields.Selection(
        selection=[
            ('ouvert', 'Ouvert'),
            ('ferme', 'Fermé'),
        ],
        string="État",
        related="abonnement_id.etat",
        readonly=True
    )
    number_of_sessions = fields.Integer(
        string="Nombre de Séances",
        related="abonnement_id.number_of_sessions",
        readonly=True
    )
    remaining_sessions = fields.Integer(
        string="Séances Restantes",
        related="abonnement_id.remaining_sessions",
        readonly=True
    )
    start_date = fields.Datetime(
        string="Date de Début",
        related="service_intensif_id.start_date",
        readonly=True
    )
    suitable_patient_ids = fields.Many2many(
        'res.partner',
        compute="_compute_suitable_patients",
        store=False,
        help="Patients whose affictions match the selected service's affictions."
    )

    @api.depends('patient_id')
    def _compute_abonnement_id(self):
        """Automatically fetch the last open abonnement for the selected patient."""
        for record in self:
            if record.patient_id:
                # Search for the last open abonnement with etat = 'ouvert'
                abonnement = self.env['gestion.abonnement'].search([
                    ('patient_id', '=', record.patient_id.id),
                    ('etat', '=', 'ouvert')
                ], order='id desc', limit=1)

                if abonnement:
                    record.abonnement_id = abonnement.id
                else:
                    record.abonnement_id = False
                    raise ValidationError(f"Aucun abonnement ouvert trouvé pour le patient {record.patient_id.name}.")
            else:
                record.abonnement_id = False

    @api.constrains('abonnement_id')
    def _check_number_of_sessions(self):
        """Ensure that the selected abonnement has remaining sessions."""
        for record in self:
            if record.abonnement_id and record.abonnement_id.remaining_sessions <= 0:
                raise ValidationError(f"L'abonnement sélectionné pour le patient {record.patient_id.name} n'a plus de séances restantes.")

    @api.depends('service_intensif_id.affiction_ids')
    def _compute_suitable_patients(self):
        """Filter patients based on the selected affictions."""
        for line in self:
            if line.service_intensif_id and line.service_intensif_id.affiction_ids:
                # Get all patients with matching affictions
                patients = self.env['res.partner'].search([
                    ('affictation_ids', 'in', line.service_intensif_id.affiction_ids.ids)
                ])
                line.suitable_patient_ids = patients
            else:
                line.suitable_patient_ids = self.env['res.partner']

class ServiceIntensifConfig(models.Model):
    _name = 'service.intensif.config'
    _description = 'Configuration for Service Intensif'

    name = fields.Char(string="Nom de la Configuration", required=True)
    default_affiction_ids = fields.Many2many(
        'affiction',
        string="Affictions Acceptées",
        help="Affictions par défaut pour tous les services intensifs."
    )