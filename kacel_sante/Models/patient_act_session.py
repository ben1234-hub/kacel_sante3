from odoo import models, fields, api

class PatientActSession(models.Model):
    _name = 'patient.act.session'
    _description = 'Patient Act Sessions'
    name = fields.Char(string="Nom de l'Acte",related='act_id.name',store=True,readonly=True)
    appointment_id = fields.Many2one('medical.appointment', string="Rendez-vous")
    patient_id = fields.Many2one('res.partner', string="Patient")
    kine_appointment_id = fields.Many2one('kinesitherapy.appointment', string="Rendez-vous")
    act_id = fields.Many2one('kinesitherapy.act', string="Acte de Kinésithérapie")
    number_of_sessions = fields.Integer(string="Nombre de séances", required=True, default=1)
    patient_phone = fields.Char(related="patient_id.phone", string="Phone", help="Phone number of the patient")
    act_ids = fields.Many2one(
        'kinesitherapy.act',
        string="Acte de Kinésithérapie",
        # required=True,
        domain="[('id', 'in', available_act_ids)]"  # Domaine dynamique
    )
    available_act_ids = fields.Many2many(
        'kinesitherapy.act',
        string="Actes disponibles",
        compute="_compute_available_act_ids",
        store=False  # Ne pas stocker ce champ en base de données
    )
    payed = fields.Boolean(string="Payed", default=False)
    unit_amount = fields.Float(
        string="Montant Unitaire",
        related="act_id.amount",
        store=True
    )
    total_amount = fields.Float(
        string="Total",
        compute="_compute_total_amount",
        store=True
    )

    @api.depends('unit_amount', 'number_of_sessions')
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = record.unit_amount * record.number_of_sessions

    @api.depends('patient_id')
    def _compute_available_act_ids(self):
        """Calcule les actes disponibles en fonction du patient sélectionné."""
        for record in self:
            if record.patient_id:
                # Récupérer les actes liés au patient
                record.available_act_ids = record.patient_id.selected_act_id
            else:
                record.available_act_ids = False

    @api.model
    def create(self, vals):
        # Ensure appointment_id is always set from the context if not provided
        if 'appointment_id' not in vals and 'default_appointment_id' in self._context:
            vals['appointment_id'] = self._context.get('default_appointment_id')
        # Ensure patient_id is always set from the context if not provided
        if 'patient_id' not in vals and 'default_patient_id' in self._context:
            vals['patient_id'] = self._context.get('default_patient_id')
        return super(PatientActSession, self).create(vals)

