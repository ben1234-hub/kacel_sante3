odoo.define('kacel_sante.CalendarView', function (require) {
    "use strict";

    var CalendarView = require('calendar.CalendarView');
    var CalendarRenderer = require('calendar.CalendarRenderer');

    // Override le rendu du calendrier
    CalendarRenderer.include({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            // Désactiver la création et la modification
            this.options.readonly = true;
        },
    });

    // Override la fenêtre contextuelle (pop-up)
    CalendarRenderer.include({
        _onOpenEvent: function (event) {
            var record = event.data.record;

            // Afficher une fenêtre contextuelle personnalisée
            new Dialog(this, {
                title: "Détails du Rendez-vous",
                size: 'medium',
                $content: $('<div>', {
                    html: "<b>Nom :</b> " + record.name + "<br/>" +
                          "<b>Date :</b> " + record.appointment_date + "<br/>" +
                          "<b>État :</b> " + record.state + "<br/>" +
                          "<b>Nombre de patients :</b> " + record.patient_count
                }),
                buttons: [
                    {
                        text: "Fermer",
                        close: true
                    }
                ]
            }).open();
        }
    });

    return CalendarView;
});