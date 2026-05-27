from odoo import models, fields, api
from datetime import date

class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    free = fields.Boolean(string="Gratuite", default=False,
                          help="If checked, the patient is eligible for free consultations.")

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _selection_company_type(self):
        return [('person', 'Patient')]

    company_type = fields.Selection(
        selection=_selection_company_type,
        string='Type de société',
        default='person',
        required=True,
    )

    dossier_num = fields.Char(string="N°", readonly=True, copy=False, index=True)
    organisme = fields.Char(string="Organisme")
    sexe = fields.Selection([('child', 'Petite Enfant'),
                             ('homme', 'Homme'),
                             ('femme', 'Femme')],
                            string="Sexe",
                            required=True)
    phone = fields.Char(required=True)
    # partner_gid = fields.Char(string="Partner GID", help="Global ID for the partner")
    name_arab = fields.Char(string="الاسم الكامل",)
    date_naissance = fields.Date(string="Date de naissance")
    age = fields.Integer(string="Âge", compute="_compute_age",readonly=False, store=True)
    wilaya = fields.Selection([
        ('01', '01 Adrar'), ('02', '02 Chlef'), ('03', '03 Laghouat'), ('04', '04 Oum El Bouaghi'),
        ('05', '05 Batna'), ('06', '06 Béjaïa'), ('07', '07 Biskra'), ('08', '08 Béchar'),
        ('09', '09 Blida'), ('10', '10 Bouira'), ('11', '11 Tamanrasset'), ('12', '12 Tébessa'),
        ('13', '13 Tlemcen'), ('14', '14 Tiaret'), ('15', '15 Tizi Ouzou'), ('16', '16 Alger'),
        ('17', '17 Djelfa'), ('18', '18 Jijel'), ('19', '19 Sétif'), ('20', '20 Saïda'),
        ('21', '21 Skikda'), ('22', '22 Sidi Bel Abbès'), ('23', '23 Annaba'), ('24', '24 Guelma'),
        ('25', '25 Constantine'), ('26', '26 Médéa'), ('27', '27 Mostaganem'), ('28', '28 M\'Sila'),
        ('29', '29 Mascara'), ('30', '30 Ouargla'), ('31', '31 Oran'), ('32', '32 El Bayadh'),
        ('33', '33 Illizi'), ('34', '34 Bordj Bou Arréridj'), ('35', '35 Boumerdès'), ('36', '36 El Tarf'),
        ('37', '37 Tindouf'), ('38', '38 Tissemsilt'), ('39', '39 El Oued'), ('40', '40 Khenchela'),
        ('41', '41 Souk Ahras'), ('42', '42 Tipaza'), ('43', '43 Mila'), ('44', '44 Aïn Defla'),
        ('45', '45 Naâma'), ('46', '46 Aïn Témouchent'), ('47', '47 Ghardaïa'), ('48', '48 Relizane'),
        ('49', '49 Timimoun'), ('50', '50 Bordj Badji Mokhtar'), ('51', '51 Ouled Djellal'), ('52', '52 Béni Abbes'),
        ('53', '53 In Salah'), ('54', '54 In Guezzam'), ('55', '55 Touggourt'), ('56', '56 Djanet'),
        ('57', '57 El M\'Ghair'), ('58', '58 El Meniaa'),
    ], string="Wilaya")

    patient_act_session_ids = fields.One2many(
        'patient.act.session',  # Related model
        'patient_id',  # Inverse field
        string="Actes de Kinésithérapie",
        readonly=False,
    )
    affictation_ids = fields.Many2many(
        'affiction',
        string="Affectations",
        help="Affectations principales du patient"
    )
    abonnement_ids = fields.One2many(
        'gestion.abonnement',
        'patient_id',
        string="Abonnements"
    )
    remaining_sessions = fields.Integer(
        string="Séances Restantes",
        related="abonnement_ids.remaining_sessions",
        store=True
    )
    number_of_sessions = fields.Integer(
        string="Actes Sélectionnés",
        related="abonnement_ids.number_of_sessions",
        store=True
    )

    medical_questionnaire_ids = fields.One2many('medical.questionnaire',
                                                 'patient_id',
                                                readonly=False,
                                                help="connect model medical questionnaire in patients")
    abonne = fields.Boolean(
        string="Abonné",
        compute="_compute_abonne_status",
        # store=True,
        help="Coché si le patient a au moins un abonnement actif"
    )
    examine_par = fields.Char(
        string="Examiné par",
        compute="_compute_examene_par",
        readonly=False,
        help="Nom du médecin basé sur l'affectation du patient"
    )

    medical_appointment_ids = fields.One2many(
        'medical.appointment',
        'patient_id',
        string="Rendez-vous Médicaux"
    )

    date_de_consultation = fields.Datetime(
        string="Date de Consultation",
        compute="_compute_date_de_consultation",
        store=True,
        readonly=False,
        help="La date de la dernière consultation médicale du patient."
    )

    kinesitherapy_appointment_ids = fields.One2many(
        'kinesitherapy.appointment.selected.act',
        'patient_id',
        string="Historique des Rendez-vous",
        help="Historique des rendez-vous de kinésithérapie pratiqués par le patient."
    )
    intensif_ids = fields.One2many(
        'service.intensif.patient.line',
        'patient_id',
        string="Historique des Séance",
        help="Historique des rendez-vous de kinésithérapie pratiqués par le patient."
    )

    show_historique_seances = fields.Boolean(
            string="Afficher Historique des Séances",
            compute="_compute_show_historique_seances",
            store=False,
            help="Indique si le patient a des affections correspondantes aux services intensifs."
     )

    @api.depends('affictation_ids', 'intensif_ids')
    def _compute_show_historique_seances(self):
            """Determine if the Historique des Séances page should be visible."""
            for partner in self:
                # Get all affiction_ids from related service.intensif records
                intensif_affictions = partner.intensif_ids.mapped('service_intensif_id.affiction_ids')
                # Check if there is any overlap between the patient's affictation_ids and the service.intensif affictions
                partner.show_historique_seances = bool(partner.affictation_ids & intensif_affictions)

    @api.model
    def get_abonnements_with_condition(self):
        """
        Fetch all abonnements where number_of_sessions >= number_of_sessions in patient.act.session.
        """
        abonnements = self.env['gestion.abonnement'].search([])
        valid_abonnements = []

        for abonnement in abonnements:
            # Get all sessions related to the current patient
            sessions = self.env['patient.act.session'].search([
                ('patient_id', '=', abonnement.patient_id.id)
            ])

            # Check if any session satisfies the condition
            if any(session.number_of_sessions <= abonnement.number_of_sessions for session in sessions):
                valid_abonnements.append(abonnement)

        return valid_abonnements

    @api.depends('medical_appointment_ids.state', 'medical_appointment_ids.appointment_date')
    def _compute_date_de_consultation(self):
        for partner in self:
            latest_appointment = self.env['medical.appointment'].search([
                ('patient_id', '=', partner.id),
                ('state', '=', 'done')
            ], order='appointment_date desc', limit=1)

            partner.date_de_consultation = latest_appointment.appointment_date if latest_appointment else False

    @api.depends('affictation_ids')
    def _compute_examene_par(self):
        """
        Compute the names of doctors based on the selected affectations.
        """
        for partner in self:
            if partner.affictation_ids:
                doctors = self.env['medical.doctor'].search([
                    ('affectation', 'in', partner.affictation_ids.ids)
                ])
                partner.examine_par = ", ".join(doctors.mapped('name'))
            else:
                partner.examine_par = ""

    @api.depends('abonnement_ids')
    def _compute_abonne_status(self):
        for partner in self:
            partner.abonne = bool(partner.abonnement_ids)

    @api.depends('date_naissance')
    def _compute_age(self):
        today = date.today()
        for patient in self:
            if patient.date_naissance:
                patient.age = today.year - patient.date_naissance.year - ((today.month, today.day) < (patient.date_naissance.month, patient.date_naissance.day))
            else:
                patient.age = 0


    def _generate_dossier_num(self):
        # Générer un numéro de dossier unique
        return self.env['ir.sequence'].next_by_code('seq_dossier_patient') or '/'

    @api.model
    def create(self, vals):
        # Générer le numéro de dossier uniquement lors de la création
        if not vals.get('dossier_num'):
            vals['dossier_num'] = self._generate_dossier_num()
        return super(ResPartner, self).create(vals)
