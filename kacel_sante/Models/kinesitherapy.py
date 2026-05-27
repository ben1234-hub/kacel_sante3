from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError

class KinesitherapyAppointment(models.Model):
    _name = 'kinesitherapy.appointment'
    _description = 'Rendez-vous'

    # Champs de base pour un rendez-vous
    name = fields.Char(string="Nom", compute='_compute_name', store=True, readonly=True)
    appointment_date = fields.Datetime(string="Date et heure du rendez-vous", required=True)
    duration = fields.Float(string="Durée (heures)", default = 1, required=True)
    end_date = fields.Datetime(string="Fin du rendez-vous", compute='_compute_end_date', store=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé'),
        ('canceled', 'Annulé'),
    ], string="Statut", default='draft')

    selected_act_ids = fields.One2many(
        'kinesitherapy.appointment.selected.act',  # Related model
        'appointment_id',  # Inverse field
        string="Selected Acts",
    )
    patient_details = fields.Text(
        string="Patient Details",
        compute="_compute_patient_details",
        store=True,
    )
    # patient_id = fields.Many2one('res.partner', string="Patient")
    total_patients = fields.Integer(string="Total Patients", compute='_compute_total_patients', store=True)

    all_patients_payed = fields.Boolean(string="All Patients Payed", compute='_compute_all_patients_payed', store=True)

    total_selected_amount = fields.Monetary(
        string="Montant",
        currency_field='currency_id',
        compute='_compute_total_selected_amount',
        store=True,
    )

    daily_total_amount = fields.Monetary(
        string="Total Amount for the Day",
        currency_field='currency_id',
        compute='_compute_daily_total_amount',
        store=True,
    )
    # Add a Many2one field to link to history.caisse
    history_caisse_id = fields.Many2one('history.caisse',
                                        string='History Caisse', readonly=True)
    total_amount_casse = fields.Monetary(related='history_caisse_id.total_amount')

    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id)

    @api.depends('selected_act_ids.amount')
    def _compute_total_selected_amount(self):
        """Calcule la somme des montants des actes sélectionnés."""
        for record in self:
            record.total_selected_amount = sum(act.amount for act in record.selected_act_ids)

    @api.depends('appointment_date')
    def _compute_daily_total_amount(self):
        """Compute the total amount for all kinesitherapy appointments on the same day."""
        for record in self:
            if record.appointment_date:
                # Convert the appointment_date to a date (without time)
                selected_date = fields.Date.to_date(record.appointment_date)

                # Search for all kinesitherapy appointments on the selected day
                appointments = self.search([
                    ('appointment_date', '>=', selected_date),
                    ('appointment_date', '<', selected_date + timedelta(days=1))
                ])

                # Calculate the total amount for the selected day, considering only paid acts
                total_amount = 0
                for appointment in appointments:
                    for act in appointment.selected_act_ids:
                        if act.payed:
                            total_amount += act.amount

                # Assign the total amount to the daily_total_amount field
                record.daily_total_amount = total_amount
            else:
                record.daily_total_amount = 0

    @api.depends('selected_act_ids.payed')
    def _compute_all_patients_payed(self):
        """Compute whether all patients have paid for this appointment."""
        for record in self:
            # Check if all selected acts are paid
            record.all_patients_payed = all(record.selected_act_ids.mapped('payed'))
    @api.depends('selected_act_ids.patient_id')
    def _compute_total_patients(self):
        """Compute the total number of unique patients in selected_act_ids."""
        for record in self:
            # Use a set to ensure uniqueness of patients
            unique_patients = set(record.selected_act_ids.mapped('patient_id.id'))
            record.total_patients = len(unique_patients)

    @api.depends('selected_act_ids.patient_id', 'selected_act_ids.payed')
    def _compute_patient_details(self):
        """Compute patient details (first name, phone, and payment status)."""
        for record in self:
            patient_details = []
            for act in record.selected_act_ids:
                # Extract the first name from the full name
                full_name = act.patient_id.name or ""
                first_name = full_name.split(" ")[0]  # Take the first part of the name
                phone = act.patient_id.phone or ""
                payed_status = "P" if act.payed else "NP"
                # Format: <First Name> <Phone> <Payed Status>
                patient_details.append(f"{first_name} {phone} ({payed_status})")
            # Separate patients with a pipe (|)
            record.patient_details = "\n | ".join(patient_details) if patient_details else False
    @api.depends('appointment_date')
    def _compute_name(self):
        for record in self:
            if record.appointment_date:
                date_str = record.appointment_date.strftime("%d/%m/%y")
                hour_str = str(record.appointment_date.hour +1)
                record.name = f"RND{date_str}/{hour_str}"
            else:
                record.name = "Nouveau Rendez-vous"

    @api.depends('appointment_date', 'duration')
    def _compute_end_date(self):
        """Compute the end date by adding the duration (in hours) to the appointment date."""
        for record in self:
            if record.appointment_date and record.duration:
                # Add the duration (in hours) to the appointment date
                record.end_date = record.appointment_date + timedelta(hours=record.duration)
            else:
                record.end_date = False

    def _update_history_caisse(self):
        """Lie le rendez-vous à l'historique de caisse correspondant à sa date."""
        for appointment in self:
            if not appointment.appointment_date:
                continue
            # Obtenir la date du rendez-vous (sans l'heure)
            appointment_date = fields.Date.to_date(appointment.appointment_date)
            # Rechercher ou créer un historique de caisse pour cette date
            history_caisse = self.env['history.caisse'].search([
                ('date', '=', appointment_date)
            ], limit=1)
            if not history_caisse:
                history_caisse = self.env['history.caisse'].create({'date': appointment_date})
            # Lier le rendez-vous à l'historique de caisse
            appointment.history_caisse_id = history_caisse.id

    @api.model
    def create(self, vals):
        # Créer le rendez-vous
        appointment = super(KinesitherapyAppointment, self).create(vals)
        appointment._update_history_caisse()
        return appointment

        return result
    # In kinesitherapy.appointment model
    def action_confirm(self):
        for appointment in self:
            # Check if all selected acts have valid abonnements or are paid
            for selected_act in appointment.selected_act_ids:
                # Skip paid acts
                if selected_act.payed:
                    continue
                # Find active abonnements for this act and patient
                abonnements = self.env['gestion.abonnement'].search([
                    ('patient_id', '=', selected_act.patient_id.id),
                    ('acts', '=', selected_act.act_id.id),
                    ('remaining_sessions', '>', 0)
                ])
                if not abonnements:
                    has_expired_abonnement = self.env['gestion.abonnement'].search([
                        ('patient_id', '=', selected_act.patient_id.id),
                        ('acts', '=', selected_act.act_id.id),
                        ('remaining_sessions', '<=', 0)
                    ], limit=1)

                    if has_expired_abonnement:
                        return {
                            'type': 'ir.actions.act_window',
                            'name': 'Abonnement Expiré',
                            'res_model': 'pay.act.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_selected_act_id': selected_act.id,
                                'default_appointment_id': appointment.id,
                                'default_message': f"Aucune séance restante pour le patient '{selected_act.patient_id.name}'. Voulez-vous payer maintenant ?"
                            }
                        }
            # If all checks pass, confirm the appointment
            appointment.state = 'confirmed'
            appointment._update_history_caisse()
            return True

    def action_done(self):
        """
        Fix the action_done method to ensure it only processes the current session
        and does not recalculate or affect old sessions.
        """
        for appointment in self:
            # Update act practice count only when the appointment is marked as 'done'
            appointment.update_act_practice_count()
            for selected_act in appointment.selected_act_ids:
                if selected_act.payed and selected_act.act_id and selected_act.patient_id:
                    # Find active abonnements for this act and patient
                    abonnements = self.env['gestion.abonnement'].search([
                        ('patient_id', '=', selected_act.patient_id.id),
                        ('acts', '=', selected_act.act_id.id),
                        ('remaining_sessions', '>', 0)  # Only consider abonnements with remaining sessions
                    ], order='id asc')

                    if abonnements:
                        # Use the first valid abonnement for the act
                        abonnement = abonnements[0]
                        if abonnement.remaining_sessions > 0:
                            # Deduct one session from the abonnement
                            abonnement.remaining_sessions -= 1
                            abonnement.used_sessions += 1
            # Mark the appointment as done
            appointment.state = 'done'
            appointment._update_history_caisse()

        return True

    def action_cancel(self):
        self.state = 'canceled'
        # Supprimer la liaison avec history.caisse
        for appointment in self:
            appointment.history_caisse_id = False

    def action_return_to_draft(self):
        """Return the appointment to the 'draft' state."""
        for record in self:
            if record.state == 'done':
                raise UserError("Vous ne pouvez pas retourner un rendez-vous terminé au brouillon.")
            record.state = 'draft'

    @api.onchange('selected_act_ids')
    def _onchange_selected_act_ids(self):
        """Prevent adding/removing patients if the state is 'done'."""
        if self.state == 'done':
            raise UserError("Vous ne pouvez pas ajouter ou supprimer des patients dans un rendez-vous terminé.")

    def update_act_practice_count(self):
        """Update the act practice count for the appointment's date."""
        for appointment in self:
            target_date = fields.Date.to_date(appointment.appointment_date)

            # Get or create the act.practice.count record for the date
            practice_count = self.env['act.practice.count'].search([
                ('date', '=', target_date)
            ], limit=1)
            if not practice_count:
                practice_count = self.env['act.practice.count'].create({
                    'date': target_date,
                })

            # Update act details for each selected act
            for selected_act in appointment.selected_act_ids:
                act_details = self.env['act.practice.details'].search([
                    ('practice_count_id', '=', practice_count.id),
                    ('act_id', '=', selected_act.act_id.id)
                ], limit=1)

                if act_details:
                    # Increment the count for existing act details
                    act_details.count += 1
                    act_details.total = act_details.count * act_details.unit_amount
                else:
                    # Create new act details for the act
                    self.env['act.practice.details'].create({
                        'practice_count_id': practice_count.id,
                        'act_id': selected_act.act_id.id,
                        'count': 1,
                        'unit_amount': selected_act.amount,
                        'total': selected_act.amount,
                    })

            # Recompute the daily total for the practice count
            practice_count._compute_daily_total()