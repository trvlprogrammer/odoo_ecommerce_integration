/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class EcommerceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            filters: {
                company_ids: [],
                provider: "",
                backend_id: false,
                store_id: false,
                date_from: "",
                date_to: "",
                granularity: "day",
            },
            meta: { companies: [], providers: [], backends: [], stores: [] },
            data: null,
        });
        onWillStart(async () => {
            const meta = await this.orm.call("ecommerce.dashboard", "get_filters", []);
            this.state.meta = meta;
            this.state.filters.company_ids = meta.default_company_ids || [];
            this.state.filters.date_from = meta.default_date_from;
            this.state.filters.date_to = meta.default_date_to;
            await this.load();
        });
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "ecommerce.dashboard",
                "get_dashboard_data",
                [this.state.filters]
            );
        } finally {
            this.state.loading = false;
        }
    }

    filteredBackends() {
        const provider = this.state.filters.provider;
        return this.state.meta.backends.filter(
            (item) =>
                this.state.filters.company_ids.includes(item.company_id) &&
                (!provider || item.provider === provider)
        );
    }

    filteredStores() {
        const backendId = Number(this.state.filters.backend_id || 0);
        return this.state.meta.stores.filter(
            (item) =>
                this.state.filters.company_ids.includes(item.company_id) &&
                (!this.state.filters.provider || item.provider === this.state.filters.provider) &&
                (!backendId || item.backend_id === backendId)
        );
    }

    onCompaniesChange(ev) {
        this.state.filters.company_ids = Array.from(ev.target.selectedOptions).map(
            (option) => Number(option.value)
        );
        this.state.filters.backend_id = false;
        this.state.filters.store_id = false;
        this.load();
    }

    onProviderChange(ev) {
        this.state.filters.provider = ev.target.value;
        this.state.filters.backend_id = false;
        this.state.filters.store_id = false;
        this.load();
    }

    onBackendChange(ev) {
        this.state.filters.backend_id = ev.target.value ? Number(ev.target.value) : false;
        this.state.filters.store_id = false;
        this.load();
    }

    onStoreChange(ev) {
        this.state.filters.store_id = ev.target.value ? Number(ev.target.value) : false;
        this.load();
    }

    onDateChange() {
        this.load();
    }

    onKpiClick(ev) {
        const key = ev.currentTarget.dataset.key;
        if (key) {
            this.openDrill(key);
        }
    }

    async openDrill(key) {
        const action = await this.orm.call("ecommerce.dashboard", "get_drilldown", [
            key,
            this.state.filters,
        ]);
        if (action) {
            this.action.doAction(action);
        }
    }

    donutStyle(item) {
        const percent = Math.max(0, Math.min(100, item.percent || 0));
        return `background: conic-gradient(#1f6f50 0 ${percent}%, #e4ebe7 ${percent}% 100%);`;
    }

    barWidth(value, values) {
        const max = Math.max(1, ...values.map((item) => item.count || 0));
        return `${Math.round(((value || 0) * 100) / max)}%`;
    }

    format(value) {
        if (value === undefined || value === null) {
            return "0";
        }
        if (typeof value === "number") {
            return new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value);
        }
        return value;
    }
}

EcommerceDashboard.template = "ecommerce_dashboard.Dashboard";
registry.category("actions").add("ecommerce_dashboard", EcommerceDashboard);
