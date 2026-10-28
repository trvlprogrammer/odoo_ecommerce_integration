/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STORE_COLORS = [
    "#2f6f8f",
    "#c47f2c",
    "#6b5ca5",
    "#3d8b6d",
    "#b05a5a",
    "#5b6b83",
    "#8a6d3b",
];

export class EcommerceDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            error: false,
            filters: {
                provider: "",
                backend_id: false,
                store_id: false,
                date_from: "",
                date_to: "",
                granularity: "day",
            },
            meta: { active_companies: [], providers: [], backends: [], stores: [] },
            data: null,
        });
        onWillStart(async () => {
            try {
                const meta = await this.orm.call("ecommerce.dashboard", "get_filters", []);
                this.state.meta = meta;
                this.state.filters.date_from = meta.default_date_from;
                this.state.filters.date_to = meta.default_date_to;
                await this.load();
            } catch (error) {
                this.state.loading = false;
                this.state.error = this.errorMessage(error);
            }
        });
    }

    errorMessage(error) {
        return error?.message || error?.data?.message || String(error);
    }

    async load() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call(
                "ecommerce.dashboard",
                "get_dashboard_data",
                [this.state.filters]
            );
        } catch (error) {
            this.state.error = this.errorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    filteredBackends() {
        const provider = this.state.filters.provider;
        return this.state.meta.backends.filter(
            (item) => !provider || item.provider === provider
        );
    }

    filteredStores() {
        const backendId = Number(this.state.filters.backend_id || 0);
        return this.state.meta.stores.filter(
            (item) =>
                (!this.state.filters.provider || item.provider === this.state.filters.provider) &&
                (!backendId || item.backend_id === backendId)
        );
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

    resetFilters() {
        this.state.filters = {
            provider: "",
            backend_id: false,
            store_id: false,
            date_from: this.state.meta.default_date_from,
            date_to: this.state.meta.default_date_to,
            granularity: "day",
        };
        this.load();
    }

    async onBarClick(ev) {
        const dataset = ev.currentTarget.dataset;
        const action = await this.orm.call("ecommerce.dashboard", "get_metric_drilldown", [
            dataset.metric,
            dataset.scope,
            dataset.storeId ? Number(dataset.storeId) : false,
            this.state.filters,
        ]);
        if (action) {
            this.action.doAction(action);
        }
    }

    periodLabel(group) {
        return group.date_filtered ? "Selected period" : "Current snapshot";
    }

    format(value, group) {
        const number = Number(value || 0);
        const decimals =
            group.value_type === "currency" ? 2 : group.value_type === "quantity" ? 2 : 0;
        const formatted = new Intl.NumberFormat(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        }).format(number);
        if (group.value_type === "currency") {
            return `${this.state.data?.currency_symbol || ""}${formatted}`;
        }
        return formatted;
    }

    barWidth(value, group) {
        const max = Math.max(Number(group.max_value || 0), 0);
        return max ? `${Math.round((Number(value || 0) * 100) / max)}%` : "0%";
    }

    barStyle(bar, barIndex, group) {
        const color =
            bar.scope === "odoo"
                ? "#123f38"
                : STORE_COLORS[Math.max(barIndex - 1, 0) % STORE_COLORS.length];
        return `width: ${this.barWidth(bar.value, group)}; background: ${color};`;
    }

    barTitle(bar, group) {
        return `${group.metric_label} — ${bar.label}: ${this.format(
            bar.value,
            group
        )} (${this.periodLabel(group)})`;
    }
}

EcommerceDashboard.template = "ecommerce_dashboard.Dashboard";
registry.category("actions").add("ecommerce_dashboard", EcommerceDashboard);
