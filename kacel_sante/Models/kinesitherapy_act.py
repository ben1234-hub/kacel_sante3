from odoo import models, fields

class KinesitherapyAct(models.Model):
    _name = 'kinesitherapy.act'
    _description = 'Acte de Kinésithérapie'

    name = fields.Char(string="Nom de l'acte", required=True)
    amount = fields.Float(string="Montant", required=True)
    description = fields.Text(string="Description")

    # Add a One2many field to show related patient act sessions
    # patient_act_session_ids = fields.One2many(
    #     'patient.act.session',  # Related model
    #     'act_id',  # Inverse field
    #     string="Sessions des Patients",
    # )