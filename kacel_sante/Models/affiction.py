from odoo import models, fields

class Affiction(models.Model):
    _name = 'affiction'
    _description = 'Affiction Configuration'

    name = fields.Char(string='Service')
    etage = fields.Char(string='Etage')
    description = fields.Text(string='Description')