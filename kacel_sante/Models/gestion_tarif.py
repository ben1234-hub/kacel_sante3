# Ajouter dans banliotherapie.py
from odoo import models, fields

class GestionTarif(models.Model):
    _name = 'gestion.tarif'
    _description = 'Gestion des Tarifs'

    name = fields.Char(string="Nom du Tarif", required=True)
    montant = fields.Float(string="Tarif", required=True)
    description = fields.Text(string="Description")