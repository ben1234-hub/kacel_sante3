from odoo import models, fields, api
from datetime import date


class MedicalDoctor(models.Model):
    _name = 'medical.doctor'
    _description = 'Médecin'

    # Champs du modèle
    name = fields.Char('Nom', required=True)
    phone = fields.Char('Numéro de téléphone')
    email = fields.Char('Email')
    adresse = fields.Char('Adresse')
    specialite = fields.Char('Spécialité')
    affectation = fields.Many2one( 'affiction',string='Affectation')
    # Champs date de recrutement et fin de contrat
    date_recrutement = fields.Date('Date de recrutement')
    date_fin_contrat = fields.Date('Date de fin de contrat')

    # Champ actif pour gérer l'archivage
    active = fields.Boolean(default=True)

    # Champ Many2many pour lier les patients (res.partner) au médecin
    patient_ids = fields.Many2many(
        'res.partner',
        'doctor_patient_rel',
        'doctor_id',
        'partner_id',
        string='Patients Consultés',
    )

    # Nouveau champ booléen pour indiquer si le médecin est en consultation
    en_consultation = fields.Boolean(string="En Consultation", default=False)

    # New Computed Field for Patients with Same Affictation
    patients_with_same_affictation = fields.One2many(
        'res.partner',
        compute="_compute_patients_with_same_affictation",
        string="Patients Consultés",
        help="Liste des patients ayant la même affectation que le médecin."
    )

    @api.depends('affectation')
    def _compute_patients_with_same_affictation(self):
        """Compute the list of patients with the same affictation as the doctor."""
        for doctor in self:
            if doctor.affectation:
                # Search for patients with the same affictation
                patients = self.env['res.partner'].search([
                    ('affictation_ids', '=', doctor.affectation.id)
                ])
                doctor.patients_with_same_affictation = patients
            else:
                doctor.patients_with_same_affictation = False

    @api.model
    def archive_expired_contracts(self):
        """Méthode qui archive les médecins dont le contrat est expiré"""
        today = date.today()
        expired_doctors = self.search([('date_fin_contrat', '<', today), ('active', '=', True)])
        expired_doctors.write({'active': False})
