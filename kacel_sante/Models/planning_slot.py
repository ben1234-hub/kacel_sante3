from odoo import models, fields, api
from datetime import time


class PlanningSlot(models.Model):
    _name = 'planning.slot'
    _description = 'Créneaux horaires programmés'

    name = fields.Char(
        string="Nom du créneau",
        compute='_compute_name',
        store=True
    )

    day_of_week = fields.Selection([
        ('0', 'Lundi'),
        ('1', 'Mardi'),
        ('2', 'Mercredi'),
        ('3', 'Jeudi'),
        ('4', 'Vendredi'),
        ('5', 'Samedi'),
        ('6', 'Dimanche')
    ], string="Jour", required=True)

    time_of_day = fields.Selection([
        ('morning', 'Matin'),
        ('evening', 'Soir')
    ], string="Moment", required=True)

    allowed_gender = fields.Selection([
        ('homme', 'Hommes'),
        ('femme', 'Femmes')
    ], string="Genre autorisé", default='homme')


    start_time = fields.Float(string="Heure de début")
    end_time = fields.Float(string="Heure de fin")

    @api.onchange('time_of_day')
    def _onchange_time_of_day(self):
        """Définir les heures par défaut selon le moment"""
        if self.time_of_day == 'morning':
            self.start_time = 7.0  # 8h00
            self.end_time = 12.0  # 12h00
        elif self.time_of_day == 'evening':
            self.start_time = 13.00  # 16h00
            self.end_time = 16.30  # 20h00

    @api.depends('day_of_week', 'time_of_day', 'allowed_gender')
    def _compute_name(self):
        for rec in self:
            day = dict(self._fields['day_of_week'].selection).get(rec.day_of_week)
            time = dict(self._fields['time_of_day'].selection).get(rec.time_of_day)
            gender = dict(self._fields['allowed_gender'].selection).get(rec.allowed_gender)

            rec.name = f"{day}{time}{gender.replace(' ', '')}" if day and time and gender else False