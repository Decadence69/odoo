/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

export class SquareFormController extends FormController {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.notification = registry.category("services").get("notification");
        this.orm = registry.category("services").get("orm");
        this.rpc = registry.category("services").get("rpc");
    }

    /**
     * @override
     */
    async afterExecuteActionButton(clickParams) {
        await super.afterExecuteActionButton(clickParams);

        // Check if we need to reload the form
        if (clickParams.name === 'action_test_square_credentials') {
            // Force reload the record to reflect state changes
            await this._refreshSquareForm();
        }
    }
    
    /**
     * Refresh the form after Square credentials test
     * @private
     */
    async _refreshSquareForm() {
        try {
            // Wait a moment for the server to process the state change
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Force reload the record
            await this.model.root.load();
            
            // Additional refresh via RPC to ensure we have the latest data
            const providerId = this.model.root.data.id;
            if (providerId) {
                const result = await this.rpc('/payment/square/refresh_form', {
                    provider_id: providerId
                });
                
                if (result.success) {
                    // If the state changed, make sure the UI reflects it
                    if (result.state !== this.model.root.data.state) {
                        await this.model.root.load();
                        this.render(true);
                    }
                }
            }
        } catch (error) {
            console.error("Error refreshing Square form:", error);
        }
    }
}

registry.category("views").add("square_provider_form", {
    ...formView,
    Controller: SquareFormController,
});
