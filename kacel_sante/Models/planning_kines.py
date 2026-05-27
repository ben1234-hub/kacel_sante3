from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta

class PlaningKines(models.Model):
    _name = 'planing.kines'
    _description = 'Planning des Kinésithérapeutes'

    name = fields.Char(string="Nom", compute="_compute_name", store=True)
    start_date = fields.Datetime(string="Date de Début", required=True)
    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        required=True,
    )
    kinesitherapist_id = fields.Many2one(
        'kinesitherapist',
        string="Kinésithérapeute",
        required=True,
    )
    # Define the One2many relationship
    line_ids = fields.One2many(
        'planing.kines.line',  # Related model
        'planing_kines_id',    # Inverse field
        string="Lignes de Planification"
    )
    @api.depends('start_date')
    def _compute_name(self):
        """Generate a unique name for the planning entry."""
        for record in self:
            if record.start_date:
                date_str = record.start_date.strftime("%d/%m/%Y")
                hour_str = record.start_date.strftime("%H")
                record.name = f"PL-{date_str}/{hour_str}"
            else:
                record.name = "Nouveau Planning"

    @api.constrains('start_date', 'kinesitherapist_id', 'patient_id')
    def _check_unique_kinesitherapist_patient_per_day(self):
        """
        Ensure that the same kinesitherapist cannot be assigned to the same patient on the same day.
        """
        for record in self:
            if record.start_date and record.kinesitherapist_id and record.patient_id:
                # Extract the date part from the start_date
                selected_date = fields.Date.to_date(record.start_date)

                # Search for overlapping records
                overlapping_plans = self.search([
                    ('kinesitherapist_id', '=', record.kinesitherapist_id.id),
                    ('patient_id', '=', record.patient_id.id),
                    ('start_date', '>=', selected_date),
                    ('start_date', '<', selected_date + timedelta(days=1)),
                    ('id', '!=', record.id),  # Exclude the current record
                ])

                if overlapping_plans:
                    raise ValidationError(
                        f"Le kinésithérapeute {record.kinesitherapist_id.name} est déjà assigné au patient "
                        f"{record.patient_id.name} pour la journée du {selected_date.strftime('%d/%m/%Y')}."
                    )

class PlaningKinesLine(models.Model):
    _name = 'planing.kines.line'
    _description = 'Lignes de Planification des Kinésithérapeutes'

    planing_kines_id = fields.Many2one(
        'planing.kines',
        string="Planification",
        required=True,
        ondelete='cascade'
    )
    patient_id = fields.Many2one(
        'res.partner',
        string="Patient",
        required=True
    )
    kinesitherapist_id = fields.Many2one(
        'kinesitherapist',
        string="Kinésithérapeute",
        required=True
    )