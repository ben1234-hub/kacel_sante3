/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarRenderer } from "@web/views/calendar/calendar_renderer";
import { markup } from "@odoo/owl";

// Patch the CalendarRenderer
patch(CalendarRenderer.prototype, {
    name: "kacel_sante.CalendarRendererPatch",
    _openEvent(ev) {
        console.log("Step 1: Entering _openEvent method");

        // Call the original method first
        const result = super._openEvent(...arguments);
        console.log("Step 2: Original method executed successfully");
    },
});