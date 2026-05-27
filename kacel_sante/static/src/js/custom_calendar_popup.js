odoo.define('kacel_sante.CustomCalendarPopup', function (require) {
    "use strict";

    var CalendarController = require('web.CalendarController');
    var Dialog = require('web.Dialog');

    CalendarController.include({
        _onOpenEvent: function (event) {
            if (!event.data || !event.data.record) {
                console.error("Données du rendez-vous introuvables.");
                return;
            }

            var record = event.data.record;
            var name = record.name || "N/A";
            var appointment_date = record.appointment_date || "Non spécifié";
            var state = record.state || "Inconnu";

            // Fetch patient details from selected_act_ids
            var patientDetails = [];
            if (record.selected_act_ids && record.selected_act_ids.length > 0) {
                record.selected_act_ids.forEach(function (act) {
                    patientDetails.push({
                        name: act.patient_id.name || "N/A",
                        phone: act.patient_id.phone || "N/A",
                        act: act.act_id.name || "N/A",
                    });
                });
            }

            // Build the popup content
            var content = $('<div>', {
                html: `<b>Nom du rendez-vous :</b> ${name} <br/>
                       <b>Date :</b> ${appointment_date} <br/>
                       <b>État :</b> ${state} <br/>
                       <b>Patients :</b> ${patientDetails.length}`
            });

            // Add patient details to the popup
            if (patientDetails.length > 0) {
                var patientList = $('<ul>');
                patientDetails.forEach(function (patient) {
                    patientList.append($('<li>', {
                        html: `<b>Nom :</b> ${patient.name} <br/>
                               <b>Téléphone :</b> ${patient.phone} <br/>
                               <b>Acte :</b> ${patient.act}`
                    }));
                });
                content.append(patientList);
            }

            // Open the custom popup
            new Dialog(this, {
                title: "Détails du Rendez-vous",
                size: 'medium',
                $content: content,
                buttons: [
                    {
                        text: "Fermer",
                        close: true
                    }
                ]
            }).open();
        }
    });
});