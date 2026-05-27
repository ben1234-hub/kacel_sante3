from odoo import models, fields

class Kinesitherapist(models.Model):
    _name = 'kinesitherapist'
    _description = 'Kinésithérapeute'

    # Basic Information
    name = fields.Char(string="Nom", required=True)
    specialite = fields.Char(string="Spécialité")
    affictation_ids = fields.Many2many(
        'affiction',
        string="Affectations",
        help="Affectations principales du kinésithérapeute."
    )

    # Contract Information
    date_recruttement = fields.Date(string="Date de Recrutement", default=fields.Date.today)
    date_fin_contrat = fields.Date(string="Date de Fin de Contrat")

    # Availability
    disponibilites = fields.Selection(
        selection=[
            ('present', 'Présent'),
            ('absent', 'Absent'),
        ],
        string="Disponibilités",
        default='present',
        required=True
    )