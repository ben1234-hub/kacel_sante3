# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta, datetime

# -------------------------------------------------------------------------
# 1. Affection (Service / Étage)
# -------------------------------------------------------------------------
class Affection(models.Model):
    _name = 'affection'
    _description = 'Affectation (service/étage)'
    _rec_name = 'name'

    name = fields.Char(string='Service', required=True, index=True)
    etage = fields.Char(string='Étage')
    description = fields.Text(string='Description')


# -------------------------------------------------------------------------
# 2. Gestion des Tarifs (pour banliothérapie)
# -------------------------------------------------------------------------
class GestionTarif(models.Model):
    _name = 'gestion.tarif'
    _description = 'Gestion des Tarifs'
    _order = 'name'

    name = fields.Char(string='Nom du tarif', required=True, index=True)
    montant = fields.Float(string='Tarif', required=True)
    currency_id = fields.Many2one('res.currency', string='Devise', default=lambda self: self.env.company.currency_id)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Actif', default=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)', 'Un tarif avec ce nom existe déjà pour cette société.')
    ]


# -------------------------------------------------------------------------
# 3. Pack (pour abonnements)
# -------------------------------------------------------------------------
class Pack(models.Model):
    _name = 'pack'
    _description = 'Pack'
    _order = 'name'

    name = fields.Char(string='Nom', required=True, index=True)
    nombre_seance = fields.Integer(string='Nombre de séances', required=True)
    amount = fields.Float(string='Montant', required=True)
    note = fields.Text(string='Note')
    type_abonnement_id = fields.Many2one('type.abonnement', string="Type d'abonnement", required=True)
    act_id = fields.Many2one('kinesitherapy.act', string="Acte associé")
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Un pack avec ce nom existe déjà.')
    ]


# -------------------------------------------------------------------------
# 4. Type d'abonnement
# -------------------------------------------------------------------------
class TypeAbonnement(models.Model):
    _name = 'type.abonnement'
    _description = "Type d'abonnement"
    _rec_name = 'name'

    name = fields.Char(string='Nom', required=True, index=True)
    description = fields.Text(string='Description')


# -------------------------------------------------------------------------
# 5. Abonnement (gestion.abonnement)
# -------------------------------------------------------------------------
class GestionAbonnement(models.Model):
    _name = 'gestion.abonnement'
    _description = 'Abonnements'
    _rec_name = 'name'

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    name = fields.Char(string='Code', compute='_compute_name', store=True, readonly=True)
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, ondelete='cascade')
    pack_name = fields.Many2one('pack', string='Nom du pack', required=True)
    number_of_sessions = fields.Integer(string='Nombre de séances', related='pack_name.nombre_seance', store=True)
    total_sans_remise = fields.Float(string='Prix du pack', related='pack_name.amount', store=True)
    remise_globale = fields.Float(string='Remise (%)', default=0.0)
    total_avec_remise = fields.Float(string='Prix avec remise', compute='_compute_totaux', store=True)
    used_sessions = fields.Integer(string='Séances utilisées', default=0)
    remaining_sessions = fields.Integer(string='Séances restantes', compute='_compute_remaining_sessions', store=True)
    date_debut = fields.Date(string='Date de début', default=fields.Date.today)
    date_fin = fields.Date(string='Date de fin', compute='_compute_date_fin', store=True, readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    versement_ids = fields.One2many('versement', 'gestion_abonnement_id', string='Versements')
    total_versement = fields.Float(string='Total des versements', compute='_compute_total_versement', store=True)
    amount_remaining = fields.Float(string='Reste à payer', compute='_compute_amount_remaining', store=True)
    state = fields.Selection([
        ('with_debt', 'Avec dette'),
        ('without_debt', 'Sans dette'),
        ('abonnement_end', 'Fin d\'abonnement'),
    ], string='État', compute='_compute_state', store=True)
    etat = fields.Selection([
        ('ouvert', 'Ouvert'),
        ('ferme', 'Fermé'),
    ], string='État d\'utilisation', compute='_compute_etat', store=True)
    intensif_ids = fields.One2many('service.intensif.patient.line', 'abonnement_id', string='Historique des séances')
    number_of_abonnements = fields.Integer(string="Nb d'abonnements", compute='_compute_number_of_abonnements', store=True)
    act_ids = fields.Many2one('kinesitherapy.act', string='Acte')

    @api.depends('patient_id', 'date')
    def _compute_name(self):
        for abo in self:
            if abo.patient_id and abo.date:
                first_name = (abo.patient_id.name or '').split()[0]
                formatted_date = abo.date.strftime("%d/%m/%y")
                abo.name = f"ABN/{first_name}/{formatted_date}"
            else:
                abo.name = "Nouvel abonnement"

    @api.depends('total_sans_remise', 'remise_globale')
    def _compute_totaux(self):
        for abo in self:
            abo.total_avec_remise = abo.total_sans_remise * (1 - abo.remise_globale / 100.0)

    @api.depends('number_of_sessions', 'used_sessions')
    def _compute_remaining_sessions(self):
        for abo in self:
            abo.remaining_sessions = max(0, abo.number_of_sessions - abo.used_sessions)

    @api.depends('date_debut')
    def _compute_date_fin(self):
        for abo in self:
            abo.date_fin = abo.date_debut + timedelta(days=30) if abo.date_debut else False

    @api.depends('versement_ids.montant_verse')
    def _compute_total_versement(self):
        for abo in self:
            abo.total_versement = sum(abo.versement_ids.mapped('montant_verse'))

    @api.depends('total_avec_remise', 'total_versement')
    def _compute_amount_remaining(self):
        for abo in self:
            abo.amount_remaining = abo.total_avec_remise - abo.total_versement

    @api.depends('amount_remaining', 'remaining_sessions')
    def _compute_state(self):
        for abo in self:
            if abo.remaining_sessions <= 0:
                abo.state = 'abonnement_end'
            elif abo.amount_remaining > 0:
                abo.state = 'with_debt'
            else:
                abo.state = 'without_debt'

    @api.depends('remaining_sessions')
    def _compute_etat(self):
        for abo in self:
            abo.etat = 'ouvert' if abo.remaining_sessions > 0 else 'ferme'

    @api.depends('patient_id')
    def _compute_number_of_abonnements(self):
        for abo in self:
            abo.number_of_abonnements = self.search_count([('patient_id', '=', abo.patient_id.id)]) if abo.patient_id else 0

    @api.constrains('used_sessions', 'number_of_sessions')
    def _check_used_sessions(self):
        for abo in self:
            if abo.used_sessions > abo.number_of_sessions:
                raise ValidationError(_("Les séances utilisées ne peuvent pas dépasser le nombre total."))

    @api.constrains('date_debut', 'date_fin')
    def _check_dates(self):
        for abo in self:
            if abo.date_fin and abo.date_debut and abo.date_fin < abo.date_debut:
                raise ValidationError(_("La date de fin doit être postérieure à la date de début."))


# -------------------------------------------------------------------------
# 6. Versement
# -------------------------------------------------------------------------
class Versement(models.Model):
    _name = 'versement'
    _description = 'Versements'
    _rec_name = 'name'

    name = fields.Char(string='Référence', readonly=True, copy=False, default='Nouveau versement')
    gestion_abonnement_id = fields.Many2one('gestion.abonnement', string='Abonnement', required=True, ondelete='cascade')
    patient_id = fields.Many2one(related='gestion_abonnement_id.patient_id', string='Patient', store=True)
    date_versement = fields.Date(string='Date de versement', default=fields.Date.today, required=True, index=True)
    montant_verse = fields.Float(string='Montant versé', required=True)
    total = fields.Float(string='Total à payer', related='gestion_abonnement_id.total_avec_remise', store=False)
    rest = fields.Float(string='Reste à payer', compute='_compute_rest', store=False)

    @api.depends('gestion_abonnement_id.amount_remaining')
    def _compute_rest(self):
        for rec in self:
            rec.rest = rec.gestion_abonnement_id.amount_remaining if rec.gestion_abonnement_id else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Nouveau versement') == 'Nouveau versement':
                vals['name'] = self.env['ir.sequence'].next_by_code('versement.sequence') or '/'
        return super().create(vals_list)


# -------------------------------------------------------------------------
# 7. Caisse Abonnement
# -------------------------------------------------------------------------
class CaisseAbonnement(models.Model):
    _name = 'caisse.abonnement'
    _description = 'Caisse abonnement'
    _rec_name = 'date'

    date = fields.Date(string='Date', default=fields.Date.today, required=True, index=True)
    total_amount_paid = fields.Monetary(string='Montant total payé', currency_field='currency_id', compute='_compute_totals', store=False)
    number_of_versements = fields.Integer(string='Nb de versements', compute='_compute_totals', store=False)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('date')
    def _compute_totals(self):
        for rec in self:
            versements = self.env['versement'].search([('date_versement', '=', rec.date)])
            rec.total_amount_paid = sum(versements.mapped('montant_verse'))
            rec.number_of_versements = len(versements)

    def action_view_versements(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Versements du %s' % self.date,
            'res_model': 'versement',
            'view_mode': 'tree,form',
            'domain': [('date_versement', '=', self.date)],
        }


# -------------------------------------------------------------------------
# 8. Planning Slot
# -------------------------------------------------------------------------
class PlanningSlot(models.Model):
    _name = 'planning.slot'
    _description = 'Créneau horaire'
    _rec_name = 'name'

    day_of_week = fields.Selection([
        ('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'), ('3', 'Jeudi'),
        ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')
    ], string='Jour', required=True, index=True)
    time_of_day = fields.Selection([
        ('morning', 'Matin'),
        ('evening', 'Soir')
    ], string='Moment', required=True)
    allowed_gender = fields.Selection([
        ('homme', 'Hommes'),
        ('femme', 'Femmes'),
        ('both', 'Les deux')
    ], string='Genre autorisé', default='both')
    start_time = fields.Float(string='Heure début')
    end_time = fields.Float(string='Heure fin')
    name = fields.Char(string='Nom', compute='_compute_name', store=True)

    @api.onchange('time_of_day')
    def _onchange_time_of_day(self):
        if self.time_of_day == 'morning':
            self.start_time = 7.0
            self.end_time = 12.0
        elif self.time_of_day == 'evening':
            self.start_time = 13.0
            self.end_time = 16.5

    @api.depends('day_of_week', 'time_of_day', 'allowed_gender')
    def _compute_name(self):
        days = dict(self._fields['day_of_week'].selection)
        times = dict(self._fields['time_of_day'].selection)
        genders = dict(self._fields['allowed_gender'].selection)
        for rec in self:
            rec.name = f"{days.get(rec.day_of_week, '')} {times.get(rec.time_of_day, '')} {genders.get(rec.allowed_gender, '')}"


# -------------------------------------------------------------------------
# 9. Rendez-vous Banliothérapie
# -------------------------------------------------------------------------
class BanliotherapieAppointment(models.Model):
    _name = 'banliotherapie.appointment'
    _description = 'Rendez-vous de banliothérapie'
    _rec_name = 'name'

    name = fields.Char(string='Nom', compute='_compute_name', store=True, readonly=True)
    appointment_date = fields.Datetime(string='Date et heure', required=True, index=True)
    duration = fields.Float(string='Durée (heures)', default=1.0, required=True)
    end_date = fields.Datetime(string='Fin', compute='_compute_end_date', store=True)
    patient_line_ids = fields.One2many('banliotherapie.appointment.patient', 'appointment_id', string='Patients')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string='Statut', default='draft', index=True)
    history_caisse_id = fields.Many2one('history.caisse', string='Historique caisse', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Montant', default=1500.0, required=True)
    total_amount = fields.Monetary(string='Montant total', compute='_compute_total_amount', store=True)
    all_patients_paid = fields.Boolean(string='Tous payés', compute='_compute_all_paid', store=True)
    planning_slot_id = fields.Many2one('planning.slot', string='Créneau horaire', compute='_compute_planning_slot', store=True, readonly=False)
    appointment_date_weekday = fields.Char(string='Jour semaine (0-6)', compute='_compute_appointment_date_weekday', store=True)
    time_of_day = fields.Selection([('morning', 'Matin'), ('evening', 'Soir')], compute='_compute_time_of_day', store=True)

    @api.depends('appointment_date')
    def _compute_name(self):
        for rec in self:
            if rec.appointment_date:
                rec.name = f"BAN{rec.appointment_date.strftime('%d/%m/%y')}/{rec.appointment_date.hour}"
            else:
                rec.name = "Nouveau RDV"

    @api.depends('appointment_date', 'duration')
    def _compute_end_date(self):
        for rec in self:
            rec.end_date = rec.appointment_date + timedelta(hours=rec.duration) if rec.appointment_date else False

    @api.depends('patient_line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.patient_line_ids.mapped('amount'))

    @api.depends('patient_line_ids.paid')
    def _compute_all_paid(self):
        for rec in self:
            rec.all_patients_paid = all(rec.patient_line_ids.mapped('paid')) if rec.patient_line_ids else False

    @api.depends('appointment_date')
    def _compute_appointment_date_weekday(self):
        for rec in self:
            rec.appointment_date_weekday = str(rec.appointment_date.weekday()) if rec.appointment_date else False

    @api.depends('appointment_date')
    def _compute_time_of_day(self):
        for rec in self:
            if rec.appointment_date:
                rec.time_of_day = 'morning' if 7 <= rec.appointment_date.hour < 11 else 'evening'
            else:
                rec.time_of_day = False

    @api.depends('appointment_date')
    def _compute_planning_slot(self):
        for rec in self:
            if rec.appointment_date:
                weekday = str(rec.appointment_date.weekday())
                hour = rec.appointment_date.hour
                time_of_day = 'morning' if 7 <= hour < 11 else 'evening'
                slot = self.env['planning.slot'].search([('day_of_week', '=', weekday), ('time_of_day', '=', time_of_day)], limit=1)
                rec.planning_slot_id = slot
            else:
                rec.planning_slot_id = False

    @api.constrains('planning_slot_id', 'patient_line_ids')
    def _check_gender_compatibility(self):
        for app in self:
            if app.planning_slot_id and app.planning_slot_id.allowed_gender != 'both':
                allowed = app.planning_slot_id.allowed_gender
                for line in app.patient_line_ids:
                    if line.patient_id.sexe != allowed:
                        raise ValidationError(_("Le patient %s ne correspond pas au genre autorisé (%s)") % (line.patient_id.name, allowed))

    def _update_history_caisse(self):
        for app in self:
            if app.appointment_date:
                date_only = fields.Date.to_date(app.appointment_date)
                history = self.env['history.caisse'].search([('date', '=', date_only)], limit=1)
                if not history:
                    history = self.env['history.caisse'].create({'date': date_only})
                app.history_caisse_id = history.id

    @api.model
    def create(self, vals):
        app = super().create(vals)
        app._update_history_caisse()
        return app

    def action_confirm(self):
        self.state = 'confirmed'

    def action_done(self):
        if not self.all_patients_paid:
            raise UserError(_("Tous les patients doivent être payés avant de terminer."))
        self.state = 'done'
        self._update_history_caisse()

    def action_cancel(self):
        self.state = 'canceled'
        self.history_caisse_id = False


# -------------------------------------------------------------------------
# 10. Ligne patient pour banliothérapie
# -------------------------------------------------------------------------
class BanliotherapieAppointmentPatient(models.Model):
    _name = 'banliotherapie.appointment.patient'
    _description = 'Patient dans un rendez-vous banliothérapie'

    appointment_id = fields.Many2one('banliotherapie.appointment', required=True, ondelete='cascade')
    patient_id = fields.Many2one('res.partner', string='Patient', required=True)
    phone = fields.Char(related='patient_id.phone', string='Téléphone')
    age = fields.Integer(related='patient_id.age', string='Âge')
    sexe = fields.Selection(related='patient_id.sexe', string='Sexe')
    tarif_id = fields.Many2one('gestion.tarif', string='Tarif appliqué', required=True)
    amount = fields.Float(related='tarif_id.montant', string='Montant', readonly=True)
    paid = fields.Boolean(string='Payé', default=False)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    _sql_constraints = [
        ('unique_patient_per_appointment', 'unique(appointment_id, patient_id)', 'Un patient ne peut être ajouté qu\'une fois par rendez-vous.'),
    ]

    def action_change_appointment(self):
        if self.appointment_id.state in ['done', 'canceled']:
            raise UserError(_("Impossible de modifier un rendez-vous terminé ou annulé."))
        return {
            'type': 'ir.actions.act_window',
            'name': 'Changer le rendez-vous',
            'res_model': 'change.appointment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_patient_line_id': self.id, 'default_new_appointment_id': self.appointment_id.id},
        }


# -------------------------------------------------------------------------
# 11. Wizard pour changer de rendez-vous (banliothérapie)
# -------------------------------------------------------------------------
class ChangeAppointmentWizard(models.TransientModel):
    _name = 'change.appointment.wizard'
    _description = 'Wizard changement de RDV'

    patient_line_id = fields.Many2one('banliotherapie.appointment.patient', required=True)
    new_appointment_id = fields.Many2one('banliotherapie.appointment', string='Nouveau rendez-vous', required=True)

    def action_confirm(self):
        self.ensure_one()
        patient_gender = self.patient_line_id.patient_id.sexe
        slot_gender = self.new_appointment_id.planning_slot_id.allowed_gender
        if patient_gender != slot_gender and slot_gender != 'both':
            raise ValidationError(_("Le patient ne correspond pas au genre autorisé pour ce créneau."))
        self.patient_line_id.appointment_id = self.new_appointment_id
        return {'type': 'ir.actions.act_window_close'}


# -------------------------------------------------------------------------
# 12. Kinésithérapeute
# -------------------------------------------------------------------------
class Kinesitherapist(models.Model):
    _name = 'kinesitherapist'
    _description = 'Kinésithérapeute'
    _order = 'name'

    name = fields.Char(string='Nom', required=True, index=True)
    specialite = fields.Char(string='Spécialité')
    affectation_ids = fields.Many2many('affection', string='Affectations')
    date_recrutement = fields.Date(string='Date de recrutement', default=fields.Date.today)
    date_fin_contrat = fields.Date(string='Date de fin de contrat')
    disponibilites = fields.Selection([
        ('present', 'Présent'),
        ('absent', 'Absent'),
    ], string='Disponibilité', default='present', required=True)
    active = fields.Boolean(string='Actif', default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.constrains('date_recrutement', 'date_fin_contrat')
    def _check_dates(self):
        for r in self:
            if r.date_fin_contrat and r.date_recrutement and r.date_fin_contrat < r.date_recrutement:
                raise ValidationError(_("La date de fin de contrat doit être postérieure à la date de recrutement."))


# -------------------------------------------------------------------------
# 13. Acte de kinésithérapie
# -------------------------------------------------------------------------
class KinesitherapyAct(models.Model):
    _name = 'kinesitherapy.act'
    _description = 'Acte de kinésithérapie'
    _order = 'name'

    name = fields.Char(string='Nom', required=True, index=True)
    amount = fields.Float(string='Montant', required=True)
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Actif', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Un acte avec ce nom existe déjà.'),
    ]


# -------------------------------------------------------------------------
# 14. Patient Act Session (lien entre patient, acte et rendez-vous)
# -------------------------------------------------------------------------
class PatientActSession(models.Model):
    _name = 'patient.act.session'
    _description = 'Session d\'acte patient'
    _rec_name = 'act_id'

    act_id = fields.Many2one('kinesitherapy.act', string='Acte', required=True)
    number_of_sessions = fields.Integer(string='Nb séances', default=1, required=True)
    unit_amount = fields.Float(related='act_id.amount', string='Montant unitaire', store=True)
    total_amount = fields.Float(string='Total', compute='_compute_total_amount', store=True)
    paid = fields.Boolean(string='Payé', default=False)
    appointment_id = fields.Many2one('medical.appointment', string='RDV médical')
    kine_appointment_id = fields.Many2one('kinesitherapy.appointment', string='RDV kiné')
    patient_id = fields.Many2one('res.partner', string='Patient')
    patient_phone = fields.Char(related='patient_id.phone', string='Téléphone')

    @api.depends('unit_amount', 'number_of_sessions')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.unit_amount * rec.number_of_sessions

    @api.constrains('appointment_id', 'kine_appointment_id')
    def _check_one_appointment(self):
        for rec in self:
            if rec.appointment_id and rec.kine_appointment_id:
                raise ValidationError(_("Une session ne peut pas être liée à deux rendez-vous."))

    @api.constrains('number_of_sessions')
    def _check_positive_sessions(self):
        for rec in self:
            if rec.number_of_sessions <= 0:
                raise ValidationError(_("Le nombre de séances doit être positif."))

    @api.model
    def create(self, vals):
        if 'appointment_id' not in vals and self._context.get('default_appointment_id'):
            vals['appointment_id'] = self._context['default_appointment_id']
        if 'kine_appointment_id' not in vals and self._context.get('default_kine_appointment_id'):
            vals['kine_appointment_id'] = self._context['default_kine_appointment_id']
        if 'patient_id' not in vals and self._context.get('default_patient_id'):
            vals['patient_id'] = self._context['default_patient_id']
        session = super().create(vals)
        if not session.patient_id:
            if session.appointment_id:
                session.patient_id = session.appointment_id.patient_id.id
            elif session.kine_appointment_id and session.kine_appointment_id.selected_act_ids:
                session.patient_id = session.kine_appointment_id.selected_act_ids[0].patient_id.id
        return session


# -------------------------------------------------------------------------
# 15. Rendez-vous de kinésithérapie
# -------------------------------------------------------------------------
class KinesitherapyAppointment(models.Model):
    _name = 'kinesitherapy.appointment'
    _description = 'Rendez-vous de kinésithérapie'
    _order = 'appointment_date desc'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    appointment_date = fields.Datetime(string='Date et heure', required=True, index=True)
    duration = fields.Float(string='Durée (heures)', default=1.0, required=True)
    end_date = fields.Datetime(string='Fin', compute='_compute_end_date', store=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string='Statut', default='draft', index=True)
    selected_act_ids = fields.One2many('kinesitherapy.appointment.selected.act', 'appointment_id', string='Actes sélectionnés')
    patient_details = fields.Text(string='Détails patients', compute='_compute_patient_details')
    total_patients = fields.Integer(string='Nb patients', compute='_compute_total_patients', store=True)
    all_patients_payed = fields.Boolean(string='Tous payés', compute='_compute_all_patients_payed', store=True)
    total_selected_amount = fields.Monetary(string='Montant total', currency_field='currency_id', compute='_compute_total_selected_amount', store=True)
    history_caisse_id = fields.Many2one('history.caisse', string='Historique caisse', readonly=True)
    total_amount_caisse = fields.Monetary(related='history_caisse_id.total_amount', string='Total caisse')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('selected_act_ids.amount')
    def _compute_total_selected_amount(self):
        for rec in self:
            rec.total_selected_amount = sum(rec.selected_act_ids.mapped('amount'))

    @api.depends('selected_act_ids.payed')
    def _compute_all_patients_payed(self):
        for rec in self:
            rec.all_patients_payed = all(rec.selected_act_ids.mapped('payed'))

    @api.depends('selected_act_ids.patient_id')
    def _compute_total_patients(self):
        for rec in self:
            rec.total_patients = len(set(rec.selected_act_ids.mapped('patient_id.id')))

    @api.depends('selected_act_ids.patient_id', 'selected_act_ids.payed')
    def _compute_patient_details(self):
        for rec in self:
            details = []
            for act in rec.selected_act_ids:
                name = act.patient_id.name or ''
                first_name = name.split()[0] if name else '?'
                phone = act.patient_id.phone or ''
                status = 'P' if act.payed else 'NP'
                details.append(f"{first_name} {phone} ({status})")
            rec.patient_details = "\n | ".join(details) if details else False

    @api.depends('appointment_date')
    def _compute_name(self):
        for rec in self:
            if rec.appointment_date:
                rec.name = f"KINE{rec.appointment_date.strftime('%d%m%y%H')}"
            else:
                rec.name = "Nouveau RDV"

    @api.depends('appointment_date', 'duration')
    def _compute_end_date(self):
        for rec in self:
            rec.end_date = rec.appointment_date + timedelta(hours=rec.duration) if rec.appointment_date else False

    def _update_history_caisse(self):
        for app in self:
            if app.appointment_date:
                date_only = fields.Date.to_date(app.appointment_date)
                history = self.env['history.caisse'].search([('date', '=', date_only)], limit=1)
                if not history:
                    history = self.env['history.caisse'].create({'date': date_only})
                app.history_caisse_id = history.id

    @api.model
    def create(self, vals):
        app = super().create(vals)
        app._update_history_caisse()
        return app

    def write(self, vals):
        res = super().write(vals)
        if 'appointment_date' in vals or 'state' in vals:
            for app in self:
                app._update_history_caisse()
        return res

    def action_confirm(self):
        for app in self:
            # Vérifications optionnelles
            app.state = 'confirmed'
            app._update_history_caisse()

    def action_done(self):
        for app in self:
            for act in app.selected_act_ids:
                if act.payed and act.act_id and act.patient_id:
                    abonnements = self.env['gestion.abonnement'].search([
                        ('patient_id', '=', act.patient_id.id),
                        ('act_ids', '=', act.act_id.id),
                        ('remaining_sessions', '>', 0)
                    ], limit=1)
                    if abonnements:
                        abonnements.used_sessions += 1
            app.state = 'done'
            app._update_history_caisse()

    def action_cancel(self):
        for app in self:
            app.state = 'canceled'
            app.history_caisse_id = False


# -------------------------------------------------------------------------
# 16. Acte sélectionné dans un RDV kiné
# -------------------------------------------------------------------------
class KinesitherapyAppointmentSelectedAct(models.Model):
    _name = 'kinesitherapy.appointment.selected.act'
    _description = 'Actes sélectionnés pour un rendez-vous'

    appointment_id = fields.Many2one('kinesitherapy.appointment', string="RDV", required=True, ondelete='cascade')
    appointment_name = fields.Char(related="appointment_id.name", string="RDV")
    appointment_date = fields.Datetime(related="appointment_id.appointment_date", string="Date et heure")
    patient_id = fields.Many2one('res.partner', string="Patient", required=True)
    patient_phone = fields.Char(related="patient_id.phone", string="Téléphone")
    payed = fields.Boolean(string="Payé", default=False)
    act_id = fields.Many2one('kinesitherapy.act', string="Acte", required=True)
    amount = fields.Float(string="Montant", compute="_compute_amount", readonly=True, store=True)
    amount_display = fields.Char(string="Affichage montant", compute="_compute_amount_display", readonly=True)
    available_act_ids = fields.Many2many('kinesitherapy.act', string="Actes disponibles", compute="_compute_available_act_ids")
    remaining_sessions = fields.Integer(string="Séances restantes", compute="_compute_remaining_and_number_of_sessions", store=True)
    number_of_sessions = fields.Integer(string="Nb séances total", compute="_compute_remaining_and_number_of_sessions", store=True)

    @api.depends('act_id.amount', 'patient_id.category_id.free', 'patient_id.abonnement_ids')
    def _compute_amount(self):
        for rec in self:
            if any(cat.free for cat in rec.patient_id.category_id):
                rec.amount = 0.0
            else:
                abos = rec.patient_id.abonnement_ids.filtered(
                    lambda a: a.act_ids.id == rec.act_id.id and a.remaining_sessions > 0
                )
                rec.amount = 0.0 if abos else rec.act_id.amount

    @api.depends('amount', 'patient_id.category_id.free', 'patient_id.abonnement_ids')
    def _compute_amount_display(self):
        for rec in self:
            if any(cat.free for cat in rec.patient_id.category_id):
                rec.amount_display = "VIP"
            else:
                abos = rec.patient_id.abonnement_ids.filtered(
                    lambda a: a.act_ids.id == rec.act_id.id and a.remaining_sessions > 0
                )
                if abos:
                    rec.amount_display = "Abonné"
                else:
                    rec.amount_display = f"{rec.amount:.2f} {rec.appointment_id.currency_id.symbol if rec.appointment_id else ''}"

    @api.depends('patient_id')
    def _compute_available_act_ids(self):
        for rec in self:
            if rec.patient_id:
                rec.available_act_ids = rec.patient_id.patient_act_session_ids.mapped('act_id')
            else:
                rec.available_act_ids = False

    @api.depends('patient_id', 'act_id')
    def _compute_remaining_and_number_of_sessions(self):
        for rec in self:
            if rec.patient_id and rec.act_id:
                abos = rec.patient_id.abonnement_ids.filtered(lambda a: a.act_ids.id == rec.act_id.id)
                rec.remaining_sessions = sum(abos.mapped('remaining_sessions'))
                rec.number_of_sessions = sum(abos.mapped('number_of_sessions'))
            else:
                rec.remaining_sessions = 0
                rec.number_of_sessions = 0

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.patient_id and record.act_id:
            abos = record.patient_id.abonnement_ids.filtered(
                lambda a: a.act_ids.id == record.act_id.id and a.remaining_sessions > 0
            )
            if abos:
                record.payed = True
        return record

    def write(self, vals):
        for rec in self:
            if 'act_id' in vals or 'patient_id' in vals:
                patient = vals.get('patient_id', rec.patient_id.id)
                act = vals.get('act_id', rec.act_id.id)
                if patient and act:
                    abos = self.env['gestion.abonnement'].search([
                        ('patient_id', '=', patient),
                        ('act_ids', '=', act),
                        ('remaining_sessions', '>', 0)
                    ])
                    if abos:
                        vals['payed'] = True
        return super().write(vals)

    def action_transfer_patient(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Transférer le patient',
            'res_model': 'patient.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_selected_act_id': self.id,
                'default_current_appointment_id': self.appointment_id.id
            }
        }


# -------------------------------------------------------------------------
# 17. Compteur de pratiques par acte
# -------------------------------------------------------------------------
class ActPracticeCount(models.Model):
    _name = 'act.practice.count'
    _description = 'Compteur de pratiques par acte'
    _rec_name = 'date'

    date = fields.Date(string="Date", required=True, index=True)
    act_details_ids = fields.One2many('act.practice.details', 'practice_count_id', string="Détails actes")
    daily_total = fields.Monetary(string="Total journalier", currency_field='currency_id', compute="_compute_daily_total", store=True)
    currency_id = fields.Many2one('res.currency', string="Devise", default=lambda self: self.env.company.currency_id)

    @api.depends('act_details_ids.total')
    def _compute_daily_total(self):
        for rec in self:
            rec.daily_total = sum(rec.act_details_ids.mapped('total'))


class ActPracticeDetails(models.Model):
    _name = 'act.practice.details'
    _description = 'Détail des pratiques par acte'

    practice_count_id = fields.Many2one('act.practice.count', string="Compteur", required=True, ondelete='cascade')
    act_id = fields.Many2one('kinesitherapy.act', string="Acte", required=True)
    count = fields.Integer(string="Nombre", default=0)
    unit_amount = fields.Monetary(string="Montant unitaire", currency_field='currency_id')
    total = fields.Monetary(string="Total", currency_field='currency_id', compute="_compute_total", store=True)
    currency_id = fields.Many2one('res.currency', string="Devise", related='practice_count_id.currency_id')

    @api.depends('count', 'unit_amount')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.count * rec.unit_amount


# -------------------------------------------------------------------------
# 18. Rendez-vous médical
# -------------------------------------------------------------------------
class MedicalAppointment(models.Model):
    _name = 'medical.appointment'
    _description = 'Rendez-vous médical'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'appointment_date desc'

    name = fields.Char(string='Code', compute='_compute_name', store=True, tracking=True)
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, tracking=True)
    patient_date_naissance = fields.Date(related='patient_id.date_naissance', string='Date naissance')
    patient_age = fields.Integer(related='patient_id.age', string='Âge')
    patient_sexe = fields.Selection(related='patient_id.sexe', string='Sexe')
    patient_phone = fields.Char(related='patient_id.phone', string='Téléphone')
    patient_category_id = fields.Many2many(related='patient_id.category_id', string='Étiquettes')
    patient_wilaya = fields.Selection(related='patient_id.wilaya', string='Wilaya')
    affectation_ids = fields.Many2many(related='patient_id.affectation_ids', string='Affectations', tracking=True)
    appointment_date = fields.Datetime(string='Date et heure', required=True, index=True, tracking=True)
    appointment_date_only = fields.Date(string='Date', compute='_compute_appointment_date_only', store=True)
    amount = fields.Monetary(string='Montant de base', default=2000.0, tracking=True)
    discount = fields.Float(string='Remise (%)', default=0.0)
    discounted_amount = fields.Monetary(string='Montant après remise', compute='_compute_discounted_amount', store=True)
    has_prior_consultation = fields.Boolean(string='Première consultation ?', compute='_compute_has_prior_consultation', store=True)
    amount_display = fields.Char(string='Affichage montant', compute='_compute_amount_display')
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirm', 'En attente'),
        ('consult', 'En consultation'),
        ('endconsult', 'Consultation terminée'),
        ('done', 'Terminé'),
        ('cancel', 'Annulé'),
    ], string='État', default='draft', tracking=True, index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    history_caisse_id = fields.Many2one('history.caisse', string='Historique caisse', readonly=True)
    total_amount_caisse = fields.Monetary(related='history_caisse_id.total_amount', string='Total caisse')
    medical_questionnaire_ids = fields.One2many(related='patient_id.medical_questionnaire_ids', string='Questionnaires')
    patient_act_session_ids = fields.One2many('patient.act.session', 'appointment_id', string='Actes kiné')

    @api.depends('amount', 'discount')
    def _compute_discounted_amount(self):
        for r in self:
            r.discounted_amount = r.amount * (1 - r.discount / 100.0)

    @api.depends('appointment_date')
    def _compute_appointment_date_only(self):
        for r in self:
            r.appointment_date_only = fields.Date.to_date(r.appointment_date) if r.appointment_date else False

    @api.depends('patient_id')
    def _compute_has_prior_consultation(self):
        for r in self:
            if isinstance(r.id, models.NewId):
                r.has_prior_consultation = False
            else:
                prior = self.search([('patient_id', '=', r.patient_id.id), ('state', '=', 'done'), ('id', '!=', r.id)], limit=1)
                r.has_prior_consultation = bool(prior)

    @api.depends('discounted_amount', 'has_prior_consultation', 'patient_id.category_id.free')
    def _compute_amount_display(self):
        for r in self:
            if r.has_prior_consultation:
                r.amount_display = "Contrôle"
            elif any(cat.free for cat in r.patient_id.category_id):
                r.amount_display = "VIP"
            else:
                r.amount_display = f"{r.discounted_amount:.2f} {r.currency_id.symbol}"

    @api.depends('patient_id', 'appointment_date')
    def _compute_name(self):
        for r in self:
            first_name = (r.patient_id.name or '').split()[0] if r.patient_id.name else ''
            if r.appointment_date:
                r.name = f"{first_name}/{r.appointment_date.strftime('%d/%m/%y/%H')}"
            else:
                r.name = "Nouveau RDV"

    def _update_history_caisse(self):
        for app in self:
            if app.appointment_date:
                date_only = fields.Date.to_date(app.appointment_date)
                history = self.env['history.caisse'].search([('date', '=', date_only)], limit=1)
                if not history:
                    history = self.env['history.caisse'].create({'date': date_only})
                app.history_caisse_id = history.id

    @api.model
    def create(self, vals):
        app = super().create(vals)
        app._update_history_caisse()
        return app

    def write(self, vals):
        res = super().write(vals)
        if 'appointment_date' in vals or 'state' in vals:
            for app in self:
                app._update_history_caisse()
        return res

    def action_confirm(self):
        self.filtered(lambda r: r.state == 'draft').write({'state': 'confirm'})

    def action_consult(self):
        self.filtered(lambda r: r.state == 'confirm').write({'state': 'consult'})

    def action_endconsult(self):
        self.filtered(lambda r: r.state == 'consult').write({'state': 'endconsult'})

    def action_done(self):
        for r in self:
            if r.state == 'endconsult':
                r.state = 'done'
                r._update_history_caisse()

    def action_cancel(self):
        self.filtered(lambda r: r.state in ['draft', 'confirm', 'consult', 'endconsult']).write({'state': 'cancel'})
        for r in self:
            r.history_caisse_id = False

    def action_reopen(self):
        self.filtered(lambda r: r.state == 'done').write({'state': 'consult'})


# -------------------------------------------------------------------------
# 19. Médecin
# -------------------------------------------------------------------------
class MedicalDoctor(models.Model):
    _name = 'medical.doctor'
    _description = 'Médecin'
    _order = 'name'

    name = fields.Char(string='Nom', required=True, index=True)
    phone = fields.Char(string='Téléphone')
    email = fields.Char(string='Email')
    adresse = fields.Char(string='Adresse')
    specialite = fields.Char(string='Spécialité')
    affectation = fields.Many2one('affection', string='Affectation')
    date_recrutement = fields.Date(string='Date de recrutement')
    date_fin_contrat = fields.Date(string='Date de fin de contrat')
    active = fields.Boolean(string='Actif', default=True)
    en_consultation = fields.Boolean(string='En consultation', default=False)
    patient_ids = fields.Many2many('res.partner', 'doctor_patient_rel', 'doctor_id', 'partner_id', string='Patients consultés')
    patients_same_affectation_ids = fields.Many2many('res.partner', compute='_compute_patients_same_affectation', string='Patients même affectation')

    @api.depends('affectation')
    def _compute_patients_same_affectation(self):
        for doc in self:
            if doc.affectation:
                patients = self.env['res.partner'].search([('affectation_ids', '=', doc.affectation.id)])
                doc.patients_same_affectation_ids = patients
            else:
                doc.patients_same_affectation_ids = False

    @api.model
    def archive_expired_contracts(self):
        today = date.today()
        expired = self.search([('date_fin_contrat', '<', today), ('active', '=', True)])
        expired.write({'active': False})


# -------------------------------------------------------------------------
# 20. Questions médicales
# -------------------------------------------------------------------------
class MedicalQuestions(models.Model):
    _name = 'medical.questions'
    _description = 'Questions médicales'
    _rec_name = 'question'

    question = fields.Char(string='Question', required=True)


class MedicalQuestionnaire(models.Model):
    _name = 'medical.questionnaire'
    _description = 'Questionnaire médical'
    _rec_name = 'question_id'

    question_id = fields.Many2one('medical.questions', string='Question', required=True)
    yes_no = fields.Selection([('yes', 'Oui'), ('no', 'Non')], string='Réponse')
    reason = fields.Text(string='Motif')
    patient_id = fields.Many2one('res.partner', string='Patient', required=True, index=True)
    appointment_id = fields.Many2one('medical.appointment', string='Rendez-vous')


# -------------------------------------------------------------------------
# 21. Historique de caisse global
# -------------------------------------------------------------------------
class HistoryCaisse(models.Model):
    _name = 'history.caisse'
    _description = 'Historique de caisse'
    _order = 'date desc'
    _rec_name = 'date'

    date = fields.Date(string='Date', required=True, default=fields.Date.today, index=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    medical_appointment_ids = fields.One2many('medical.appointment', 'history_caisse_id', string='RDV médicaux')
    kinesitherapy_appointment_ids = fields.One2many('kinesitherapy.appointment', 'history_caisse_id', string='RDV kiné')
    banliotherapie_appointment_ids = fields.One2many('banliotherapie.appointment', 'history_caisse_id', string='RDV banliothérapie')
    total_medical_amount = fields.Monetary(string='Total médical', compute='_compute_totals', store=True)
    total_kinesitherapy_amount = fields.Monetary(string='Total kiné', compute='_compute_totals', store=True)
    total_banliotherapie_amount = fields.Monetary(string='Total banlio', compute='_compute_totals', store=True)
    total_amount = fields.Monetary(string='Total général', compute='_compute_totals', store=True)
    nb_medical = fields.Integer(string='Nb RDV médicaux', compute='_compute_numbers', store=True)
    nb_kine = fields.Integer(string='Nb RDV kiné', compute='_compute_numbers', store=True)
    nb_banlio = fields.Integer(string='Nb RDV banlio', compute='_compute_numbers', store=True)

    @api.depends(
        'medical_appointment_ids.discounted_amount', 'medical_appointment_ids.has_prior_consultation',
        'medical_appointment_ids.patient_id.category_id.free',
        'kinesitherapy_appointment_ids.total_selected_amount',
        'banliotherapie_appointment_ids.total_amount'
    )
    def _compute_totals(self):
        for rec in self:
            paid_medical = rec.medical_appointment_ids.filtered(
                lambda a: not a.has_prior_consultation and not any(cat.free for cat in a.patient_id.category_id)
            )
            rec.total_medical_amount = sum(paid_medical.mapped('discounted_amount'))
            rec.total_kinesitherapy_amount = sum(rec.kinesitherapy_appointment_ids.mapped('total_selected_amount'))
            rec.total_banliotherapie_amount = sum(rec.banliotherapie_appointment_ids.mapped('total_amount'))
            rec.total_amount = rec.total_medical_amount + rec.total_kinesitherapy_amount + rec.total_banliotherapie_amount

    @api.depends('medical_appointment_ids', 'kinesitherapy_appointment_ids', 'banliotherapie_appointment_ids')
    def _compute_numbers(self):
        for rec in self:
            rec.nb_medical = len(rec.medical_appointment_ids)
            rec.nb_kine = len(rec.kinesitherapy_appointment_ids)
            rec.nb_banlio = len(rec.banliotherapie_appointment_ids)


# -------------------------------------------------------------------------
# 22. Héritage de res.partner
# -------------------------------------------------------------------------
class ResPartnerInherit(models.Model):
    _inherit = 'res.partner'

    company_type = fields.Selection(selection_add=[('person', 'Patient')], default='person', required=True)
    dossier_num = fields.Char(string='N° dossier', readonly=True, copy=False, index=True)
    organisme = fields.Char(string='Organisme')
    sexe = fields.Selection([
        ('child', 'Petit enfant'),
        ('homme', 'Homme'),
        ('femme', 'Femme')
    ], string='Sexe', required=True)
    name_arab = fields.Char(string='الاسم الكامل')
    date_naissance = fields.Date(string='Date de naissance')
    age = fields.Integer(string='Âge', compute='_compute_age', store=True)
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
    ], string='Wilaya')
    affectation_ids = fields.Many2many('affection', string='Affectations')
    abonnement_ids = fields.One2many('gestion.abonnement', 'patient_id', string='Abonnements')
    medical_questionnaire_ids = fields.One2many('medical.questionnaire', 'patient_id', string='Questionnaires')
    patient_act_session_ids = fields.One2many('patient.act.session', 'patient_id', string='Actes kiné')
    intensif_ids = fields.One2many('service.intensif.patient.line', 'patient_id', string='Séances intensives')
    medical_appointment_ids = fields.One2many('medical.appointment', 'patient_id', string='RDV médicaux')
    kinesitherapy_selected_act_ids = fields.One2many('kinesitherapy.appointment.selected.act', 'patient_id', string='Actes kiné sélectionnés')
    date_de_consultation = fields.Datetime(string='Dernière consultation', compute='_compute_last_consultation', store=True)
    abonne = fields.Boolean(string='Abonné', compute='_compute_abonne')
    examine_par = fields.Char(string='Examiné par', compute='_compute_examine_par')
    show_historique_seances = fields.Boolean(string='Afficher historique', compute='_compute_show_historique')

    @api.depends('date_naissance')
    def _compute_age(self):
        today = date.today()
        for p in self:
            if p.date_naissance:
                p.age = today.year - p.date_naissance.year - ((today.month, today.day) < (p.date_naissance.month, p.date_naissance.day))
            else:
                p.age = 0

    @api.depends('medical_appointment_ids.state', 'medical_appointment_ids.appointment_date')
    def _compute_last_consultation(self):
        for p in self:
            last = self.env['medical.appointment'].search([('patient_id', '=', p.id), ('state', '=', 'done')], order='appointment_date desc', limit=1)
            p.date_de_consultation = last.appointment_date if last else False

    @api.depends('abonnement_ids')
    def _compute_abonne(self):
        for p in self:
            p.abonne = bool(p.abonnement_ids)

    @api.depends('affectation_ids')
    def _compute_examine_par(self):
        for p in self:
            if p.affectation_ids:
                doctors = self.env['medical.doctor'].search([('affectation', 'in', p.affectation_ids.ids)])
                p.examine_par = ", ".join(doctors.mapped('name'))
            else:
                p.examine_par = ""

    @api.depends('affectation_ids', 'intensif_ids')
    def _compute_show_historique(self):
        for p in self:
            intensif_aff = p.intensif_ids.mapped('service_intensif_id.affectation_ids')
            p.show_historique_seances = bool(p.affectation_ids & intensif_aff)

    @api.model
    def create(self, vals):
        if not vals.get('dossier_num'):
            vals['dossier_num'] = self.env['ir.sequence'].next_by_code('seq_dossier_patient') or '/'
        return super().create(vals)


# -------------------------------------------------------------------------
# 23. Planning kinésithérapeute
# -------------------------------------------------------------------------
class PlanningKines(models.Model):
    _name = 'planning.kines'
    _description = 'Planning journalier des kinés'
    _rec_name = 'name'

    name = fields.Char(string='Référence', compute='_compute_name', store=True)
    date = fields.Date(string='Date', required=True, index=True)
    kinesitherapist_id = fields.Many2one('kinesitherapist', string='Kinésithérapeute', required=True)
    line_ids = fields.One2many('planning.kines.line', 'planning_kines_id', string='Créneaux')
    service_intensif_id = fields.Many2one('service.intensif', string='Service intensif')

    @api.depends('date', 'kinesitherapist_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.kinesitherapist_id.name} - {rec.date}" if rec.date else "Nouveau planning"

    @api.constrains('date', 'kinesitherapist_id')
    def _check_unique_per_day(self):
        for rec in self:
            same = self.search([('kinesitherapist_id', '=', rec.kinesitherapist_id.id), ('date', '=', rec.date), ('id', '!=', rec.id)])
            if same:
                raise ValidationError(_("Un planning existe déjà pour ce kiné à cette date."))


class PlanningKinesLine(models.Model):
    _name = 'planning.kines.line'
    _description = 'Ligne de planning kiné'
    _order = 'start_datetime'

    planning_kines_id = fields.Many2one('planning.kines', required=True, ondelete='cascade')
    patient_id = fields.Many2one('res.partner', string='Patient', required=True)
    kinesitherapist_id = fields.Many2one('kinesitherapist', string='Kinésithérapeute', required=True)
    start_datetime = fields.Datetime(string='Début', required=True)
    duration = fields.Float(string='Durée (heures)', default=1.0, required=True)
    end_datetime = fields.Datetime(string='Fin', compute='_compute_end_datetime', store=True)
    notes = fields.Text(string='Notes')

    @api.depends('start_datetime', 'duration')
    def _compute_end_datetime(self):
        for line in self:
            line.end_datetime = line.start_datetime + timedelta(hours=line.duration) if line.start_datetime else False

    @api.constrains('start_datetime', 'duration')
    def _check_hours(self):
        for line in self:
            if line.duration <= 0:
                raise ValidationError(_("La durée doit être positive."))
            if line.end_datetime and line.end_datetime.date() != line.start_datetime.date():
                raise ValidationError(_("Le créneau ne peut pas dépasser minuit."))

    @api.constrains('planning_kines_id', 'start_datetime')
    def _check_date_consistency(self):
        for line in self:
            if line.planning_kines_id.date != line.start_datetime.date():
                raise ValidationError(_("La date du créneau doit correspondre à la date du planning."))


# -------------------------------------------------------------------------
# 24. Service Intensif
# -------------------------------------------------------------------------
class ServiceIntensif(models.Model):
    _name = 'service.intensif'
    _description = 'Service Intensif'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Nom', compute='_compute_name', store=True, tracking=True)
    start_date = fields.Datetime(string='Date et heure début', default=fields.Datetime.now, required=True, tracking=True)
    duration = fields.Float(string='Durée (heures)', default=1.0, required=True, tracking=True)
    end_date = fields.Datetime(string='Date et heure fin', compute='_compute_end_date', store=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string='État', default='draft', tracking=True, index=True)
    patient_line_ids = fields.One2many('service.intensif.patient.line', 'service_intensif_id', string='Patients', tracking=True)
    affectation_ids = fields.Many2many('affection', string='Affectations acceptées')

    @api.depends('start_date')
    def _compute_name(self):
        for rec in self:
            if rec.start_date:
                rec.name = f"INT{rec.start_date.strftime('%d/%m/%y/%H')}"
            else:
                rec.name = "Nouveau service"

    @api.depends('start_date', 'duration')
    def _compute_end_date(self):
        for rec in self:
            rec.end_date = rec.start_date + timedelta(hours=rec.duration) if rec.start_date else False

    @api.model
    def create(self, vals):
        if 'affectation_ids' not in vals:
            config = self.env['service.intensif.config'].search([], limit=1)
            if config and config.default_affectation_ids:
                vals['affectation_ids'] = [(6, 0, config.default_affectation_ids.ids)]
        return super().create(vals)

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_done(self):
        for rec in self:
            kines = self.env['kinesitherapist'].search([])
            if not kines:
                raise ValidationError(_("Aucun kinésithérapeute disponible."))
            patients = rec.patient_line_ids.mapped('patient_id')
            if len(patients) > len(kines):
                raise ValidationError(_("Pas assez de kinésithérapeutes pour tous les patients."))
            planning = self.env['planning.kines'].create({
                'date': fields.Date.to_date(rec.start_date),
                'kinesitherapist_id': False,
                'service_intensif_id': rec.id,
            })
            for i, patient in enumerate(patients):
                kin = kines[i % len(kines)]
                self.env['planning.kines.line'].create({
                    'planning_kines_id': planning.id,
                    'patient_id': patient.id,
                    'kinesitherapist_id': kin.id,
                    'start_datetime': rec.start_date,
                    'duration': rec.duration,
                })
            for line in rec.patient_line_ids:
                if line.abonnement_id:
                    line.abonnement_id.used_sessions += 1
            rec.state = 'done'

    def action_cancel(self):
        self.write({'state': 'canceled'})

    def open_patients(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Patients',
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('affectation_ids', 'in', self.affectation_ids.ids)],
            'context': {'default_affectation_ids': self.affectation_ids.ids},
        }


class ServiceIntensifPatientLine(models.Model):
    _name = 'service.intensif.patient.line'
    _description = 'Ligne patient pour service intensif'

    service_intensif_id = fields.Many2one('service.intensif', required=True, ondelete='cascade')
    patient_id = fields.Many2one('res.partner', string='Patient', required=True)
    name_arab = fields.Char(related='patient_id.name_arab', string='الاسم الكامل')
    affectation_ids = fields.Many2many(related='service_intensif_id.affectation_ids', string='Affectations')
    abonnement_id = fields.Many2one('gestion.abonnement', string='Abonnement', compute='_compute_abonnement_id', store=True, readonly=False)
    type_abonnement_id = fields.Many2one(related='abonnement_id.pack_name.type_abonnement_id', string="Type d'abonnement")
    pack_name = fields.Char(related='abonnement_id.pack_name.name', string='Pack')
    total_versement = fields.Float(related='abonnement_id.total_versement', string='Total versé')
    total_avec_remise = fields.Float(related='abonnement_id.total_avec_remise', string='Total avec remise')
    used_sessions = fields.Integer(related='abonnement_id.used_sessions', string='Séances utilisées')
    etat = fields.Selection(related='abonnement_id.etat', string='État')
    number_of_sessions = fields.Integer(related='abonnement_id.number_of_sessions', string='Nb séances total')
    remaining_sessions = fields.Integer(related='abonnement_id.remaining_sessions', string='Séances restantes')
    start_date = fields.Datetime(related='service_intensif_id.start_date', string='Date début')
    suitable_patient_ids = fields.Many2many('res.partner', compute='_compute_suitable_patients', string='Patients éligibles')

    @api.depends('service_intensif_id.affectation_ids')
    def _compute_suitable_patients(self):
        for line in self:
            if line.service_intensif_id and line.service_intensif_id.affectation_ids:
                patients = self.env['res.partner'].search([
                    ('affectation_ids', 'in', line.service_intensif_id.affectation_ids.ids)
                ])
                line.suitable_patient_ids = patients
            else:
                line.suitable_patient_ids = False

    @api.depends('patient_id')
    def _compute_abonnement_id(self):
        for line in self:
            if line.patient_id:
                abo = self.env['gestion.abonnement'].search([
                    ('patient_id', '=', line.patient_id.id),
                    ('etat', '=', 'ouvert')
                ], order='id desc', limit=1)
                line.abonnement_id = abo.id if abo else False
            else:
                line.abonnement_id = False

    @api.constrains('abonnement_id')
    def _check_remaining_sessions(self):
        for line in self:
            if line.abonnement_id and line.abonnement_id.remaining_sessions <= 0:
                raise ValidationError(_("L'abonnement du patient %s n'a plus de séances.") % line.patient_id.name)

    @api.onchange('patient_id')
    def _onchange_patient_id(self):
        self._compute_abonnement_id()


class ServiceIntensifConfig(models.Model):
    _name = 'service.intensif.config'
    _description = 'Configuration service intensif'

    name = fields.Char(string='Nom de la configuration', required=True)
    default_affectation_ids = fields.Many2many('affection', string='Affectations par défaut')
