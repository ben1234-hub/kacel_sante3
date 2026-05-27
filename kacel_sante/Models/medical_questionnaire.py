
from odoo import fields, models


class MedicalQuestionnaire(models.Model):
    """Medical questions to be asked to the patients while their appointment"""
    _name = 'medical.questionnaire'
    _description = 'Medical Questionnaire'

    question_id = fields.Many2one('medical.questions',
                                  string='Questions',
                                  help="All added question")
    yes_no = fields.Selection([('yes', 'Oui'), ('no', 'Non')],
                              string='Yes or No', help="")
    reason = fields.Text(string='Reason', help="Reason for the question answer")
    patient_id = fields.Many2one('res.partner',
                                 string='Patient',
                                 help="Patient name")
