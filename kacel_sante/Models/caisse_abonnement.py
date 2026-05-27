from odoo import models, fields, api
from datetime import date

class CaisseAbonnement(models.Model):
    _name = 'caisse.abonnement'
    _description = 'Caisse Abonnement'

    date = fields.Date(string="Date", default=fields.Date.today)
    total_amount_paid = fields.Monetary(
        string="Montant Total Payé",
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    number_of_verssements = fields.Integer(
        string="Nombre de Versements",
        compute='_compute_totals',
        store=True
    )
    verssement_details = fields.One2many(
        'verssement',
        compute='_compute_verssement_details',
        string="Détails des Versements"
    )
    currency_id = fields.Many2one('res.currency', string="Currency", default=lambda self: self.env.company.currency_id)

    @api.depends('date')
    def _compute_totals(self):
        """Compute the total amount paid and number of versements for the day."""
        for record in self:
            if record.date:
                # Search for all versements on the given date
                versements = self.env['verssement'].search([
                    ('date_verssement', '=', record.date)
                ])
                # Compute the total amount paid and the number of versements
                record.total_amount_paid = sum(v.montant_versse for v in versements)
                record.number_of_verssements = len(versements)
            else:
                record.total_amount_paid = 0
                record.number_of_verssements = 0

    @api.depends('date')
    def _compute_verssement_details(self):
        """Compute the details of versements for the day."""
        for record in self:
            if record.date:
                # Fetch all versements for the given date
                versements = self.env['verssement'].search([
                    ('date_verssement', '=', record.date)
                ])
                record.verssement_details = versements
            else:
                record.verssement_details = False