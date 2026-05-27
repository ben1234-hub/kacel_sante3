
from odoo import api, fields, models


class MedicalQuestions(models.Model):
    """To add medical questionnaire question"""
    _name = 'medical.questions'
    _description = 'Medical Questions'
    _rec_name = 'question'

    question = fields.Char(string='Question')

    @api.model
    def create(self, vals):
        """Overrides the default create method to add a new medical question
        record and automatically create a corresponding entry in the
        `medical.questionnaire` model."""
        res = super(MedicalQuestions, self).create(vals)
        self.env['medical.questionnaire'].create({
            'question_id': res.id
        })
        return res

    def unlink(self):
        """Overrides the default unlink method to delete the current medical question record.
        Before deletion, it searches for and deletes any associated records in the
        `medical.questionnaire` model that reference this medical question."""
        for rec in self:
            for line in self.env['medical.questionnaire'].search([('question_id', '=', rec.id)]):
                line.unlink()
            return super(MedicalQuestions, self).unlink()
