/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import paymentForm from '@payment/js/payment_form';

paymentForm.include({
    _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'square') {
            return this._super(...arguments);
        }

        if (flow === 'token') {
            return;
        }

        this._setPaymentFlow('direct');
    },

    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'square') {
            return this._super(...arguments);
        }

        if (processingValues.error) {
            this._displayError(_t("Payment Processing Error"), processingValues.error);
            return;
        }

        if (!processingValues.square_payment_link) {
            this._displayError(
                _t("Payment Processing Error"), 
                _t("Could not redirect to Square. Please try again.")
            );
            return;
        }

        window.top.location.href = processingValues.square_payment_link;
    },
});