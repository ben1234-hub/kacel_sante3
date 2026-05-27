from odoo import models, fields

class Pack(models.Model):
    _name = 'pack'
    _description = 'Pack'

    name = fields.Char(string="Nom", required=True)
    nombre_seance = fields.Integer(string="Nombre de Séances", required=True)
    amount = fields.Float(string="Montant", required=True)
    note = fields.Text(string="Note")
    type_abonnement_id = fields.Many2one(
        'type.abonnement',
        string="Type d'Abonnement",
        required=True,
    )