from odoo import models, fields

class TypeAbonnement(models.Model):
    _name = 'type.abonnement'
    _description = 'Type d\'Abonnement'

    name = fields.Char(string="Nom", required=True)
    # pack_id = fields.Many2one(
    #     'pack',
    #     string="Pack",
    #     required=True,
    # )
    description = fields.Text(string="Description")