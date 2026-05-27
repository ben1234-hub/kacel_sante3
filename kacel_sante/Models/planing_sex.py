from odoo import models, fields, api


class PlaningSex(models.Model):
    _name = 'planing.sex'
    _description = 'Planning des séances'

    jour_semaine = fields.Selection([
        ('lundi', 'Lundi'),
        ('mardi', 'Mardi'),
        ('mercredi', 'Mercredi'),
        ('jeudi', 'Jeudi'),
        ('vendredi', 'Vendredi'),
        ('samedi', 'Samedi'),
        ('dimanche', 'Dimanche')
    ], string='Jours de semaine', required=True)

    shift  = fields.Selection([
        ('matin','Matin'),
        ('soir','Soir')
    ],string='Shift', required=True)

    # Add the sex field
    sex = fields.Selection([
        ('homme', 'Homme'),
        ('femme', 'Femme')
    ], string='Sexe', required=True)