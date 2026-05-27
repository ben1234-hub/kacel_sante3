/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";

// Patch the CalendarController to customize the existing appointment popup
patch(CalendarController.prototype, {
    async _openEvent(ev) {
        // Call the original method to preserve its behavior
        const originalMethod = this._super || this.__super__;
        if (originalMethod) {
            await originalMethod.apply(this, arguments);
        }

        // Get the record IDs of the clicked event
        const recordIds = ev.detail.recordIds;

        if (recordIds && recordIds.length > 0) {
            // Fetch appointment details
            const orm = useService("orm");
            const notifications = useService("notification");

            try {
                const appointments = await orm.read(this.props.model, recordIds, ["name", "patient_line_ids"]);

                // Prepare patient data
                const patientsData = [];
                for (const appointment of appointments) {
                    const patientLines = await orm.read("banliotherapie.appointment.patient", appointment.patient_line_ids, ["patient_id", "phone"]);
                    patientsData.push(...patientLines.map((line) => ({
                        name: line.patient_id[1], // Patient name
                        phone: line.phone || "N/A", // Patient phone number
                    })));
                }

                // Add patient details to the popup
                this._addPatientDetailsToPopup(patientsData, appointments.length);
            } catch (error) {
                console.error("Error fetching appointment details:", error);
                notifications.add(`An error occurred while loading appointment details.`, { type: "danger" });
            }
        }
    },

    /**
     * Add patient details to the existing popup.
     * @param {Array<Object>} patientsData - Array of patient objects with `name` and `phone`.
     * @param {number} totalAppointments - Total number of appointments in the clicked cell.
     */
    _addPatientDetailsToPopup(patientsData, totalAppointments) {
        const dialogService = this.env.services.dialog;

        // Generate the HTML content for the patient details table
        const content = `
            <div style="margin-top: 10px; border-top: 1px solid #ccc; padding-top: 10px;">
                <p><b>Total Appointments:</b> ${totalAppointments}</p>
                <p><b>Total Patients:</b> ${patientsData.length}</p>
                <table border="1" style="width:100%; margin-top: 10px;">
                    <thead>
                        <tr>
                            <th style="padding: 5px;">Nom</th>
                            <th style="padding: 5px;">Téléphone</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${patientsData
                            .map(
                                (patient) => `<tr><td style="padding: 5px;">${patient.name}</td><td style="padding: 5px;">${patient.phone}</td></tr>`
                            )
                            .join("")}
                    </tbody>
                </table>
            </div>
        `;

        // Update the existing popup with the new content
        const currentDialog = dialogService.getDialogs().find((dialog) => dialog.el.classList.contains("o_calendar_event_dialog"));
        if (currentDialog) {
            const popupBody = currentDialog.el.querySelector(".o_calendar_event_dialog_body");
            if (popupBody) {
                popupBody.innerHTML += content;
            }
        }
    },
});