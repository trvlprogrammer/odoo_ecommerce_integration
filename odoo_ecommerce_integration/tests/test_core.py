from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCore(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Integration Test WH", "code": "ITW", "company_id": cls.company.id}
        )
        cls.backend = cls.env["ecommerce.backend"].create(
            {
                "name": "Test Backend",
                "code": "test",
                "provider": "magento",
                "base_url": "https://magento.example.test",
                "access_token": "test-token",
                "job_user_id": cls.env.user.id,
            }
        )
        cls.store = cls.env["ecommerce.store"].create(
            {
                "name": "Test Store",
                "code": "test",
                "backend_id": cls.backend.id,
                "company_id": cls.company.id,
                "external_store_view_code": "default",
                "external_website_id": "1",
                "external_store_view_id": "1",
                "warehouse_id": cls.warehouse.id,
                "stock_location_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.template = cls.env["product.template"].create(
            {"name": "Mapped Product", "default_code": "IT-001", "type": "consu"}
        )

    def _mapping_values(self, external_id="100"):
        return {
            "backend_id": self.backend.id,
            "store_id": self.store.id,
            "external_id": external_id,
            "odoo_template_id": self.template.id,
            "external_product_type": "simple",
        }

    def test_backend_store_scope(self):
        self.assertEqual(self.store.company_id, self.company)
        self.assertEqual(self.backend.state, "draft")
        self.assertTrue(self.backend.access_token)

    def test_mapping_company_is_derived(self):
        mapping = self.env["ecommerce.product.mapping"].create(self._mapping_values())
        self.assertEqual(mapping.company_id, self.company)

    def test_external_mapping_is_unique_per_store(self):
        self.env["ecommerce.product.mapping"].create(self._mapping_values())
        other_template = self.env["product.template"].create(
            {"name": "Other Mapped Product", "type": "consu"}
        )
        with self.assertRaises(IntegrityError):
            self.env["ecommerce.product.mapping"].create(
                dict(self._mapping_values(), odoo_template_id=other_template.id)
            )


    def test_backend_company_mismatch_is_rejected(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})
        with self.assertRaises(ValidationError):
            self.store.company_id = other_company

    def test_company_record_rule(self):
        other_company = self.env["res.company"].create({"name": "Other Company"})
        other_backend = self.env["ecommerce.backend"].create(
            {
                "name": "Other Backend",
                "code": "other",
                "provider": "magento",
                "base_url": "https://other.example.test",
                "company_id": other_company.id,
                "job_user_id": self.env.user.id,
            }
        )
        user = self.env["res.users"].create(
            {
                "name": "Company A User",
                "login": "company-a-user",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [
                    (6, 0, [self.env.ref("base.group_user").id, self.env.ref("odoo_ecommerce_integration.group_ecommerce_user").id])
                ],
            }
        )
        visible = self.env["ecommerce.backend"].with_user(user).search([])
        self.assertIn(self.backend, visible)
        self.assertNotIn(other_backend, visible)

    def test_event_and_issue_are_separate(self):
        event = self.env["ecommerce.sync.event"].create(
            {
                "backend_id": self.backend.id,
                "store_id": self.store.id,
                "event_type": "test_event",
                "title": "Test event",
            }
        )
        issue = self.env["ecommerce.sync.issue"]._record(
            store=self.store,
            issue_type="test_issue",
            reason_code="test_reason",
            title="Test issue",
            summary="Test summary",
            fingerprint="store:test|issue:test",
        )
        self.assertNotEqual(event._name, issue._name)
        self.assertEqual(issue.status, "open")

    def test_issue_deduplicates(self):
        issue_model = self.env["ecommerce.sync.issue"]
        first = issue_model._record(
            store=self.store,
            issue_type="test_issue",
            reason_code="test_reason",
            title="Test issue",
            summary="Test summary",
            fingerprint="store:test|issue:dedupe",
        )
        second = issue_model._record(
            store=self.store,
            issue_type="test_issue",
            reason_code="test_reason",
            title="Test issue",
            summary="Test summary",
            fingerprint="store:test|issue:dedupe",
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(second.occurrence_count, 2)

class FakeProviderAdapter:
    """Test-only provider adapter; never installed in production."""

    code = "fake"
    label = "Fake Provider"
    capabilities = (
        "product.import",
        "product.export",
        "product.update",
        "order.import",
    )

    @classmethod
    def definition(cls):
        return {
            "code": cls.code,
            "label": cls.label,
            "capabilities": list(cls.capabilities),
        }


class TestGenericProviderContract(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Fake Provider WH", "code": "FPW", "company_id": cls.company.id}
        )
        cls.backend = cls.env["ecommerce.backend"].create(
            {
                "name": "Fake Backend",
                "code": "fake",
                "provider": FakeProviderAdapter.code,
                "base_url": "https://fake.example.test",
                "job_user_id": cls.env.user.id,
            }
        )
        cls.store = cls.env["ecommerce.store"].create(
            {
                "name": "Fake Store",
                "code": "fake",
                "backend_id": cls.backend.id,
                "company_id": cls.company.id,
                "external_store_view_code": "default",
                "warehouse_id": cls.warehouse.id,
                "stock_location_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.template = cls.env["product.template"].create(
            {"name": "Fake Mapped Product", "default_code": "FAKE-1", "type": "consu"}
        )

    def _patch_provider(self, calls=None):
        from unittest.mock import patch

        from odoo.addons.odoo_ecommerce_integration.models.ecommerce_backend import (
            EcommerceBackend,
        )
        from odoo.addons.odoo_ecommerce_integration.models.ecommerce_mapping import (
            EcommerceStore,
        )

        original_registry = EcommerceBackend._ecommerce_provider_registry

        def registry(model):
            return original_registry(model) + [FakeProviderAdapter.definition()]

        def enqueue(store, resource, operation):
            if calls is not None:
                calls.append((store.id, resource, operation))
            return 1

        return (
            patch.object(EcommerceBackend, "_ecommerce_provider_registry", registry),
            patch.object(EcommerceStore, "_ecommerce_enqueue_sync", enqueue),
        )

    def test_fake_provider_is_discoverable_and_capability_filtered(self):
        patches = self._patch_provider()
        with patches[0], patches[1]:
            selection = self.env["ecommerce.backend"]._ecommerce_provider_selection()
            self.assertIn((FakeProviderAdapter.code, FakeProviderAdapter.label), selection)
            self.assertTrue(self.store.can_product_sync)
            self.assertTrue(self.store._ecommerce_supports("products", "update"))
            self.assertTrue(self.store._ecommerce_supports("orders", "import"))
            self.assertFalse(self.store._ecommerce_supports("inventory", "export"))
            self.assertFalse(self.store.can_preflight)

    def test_fake_provider_runs_generic_store_wizard(self):
        calls = []
        patches = self._patch_provider(calls)
        with patches[0], patches[1]:
            wizard = self.env["ecommerce.store.sync.wizard"].create(
                {
                    "operation": "import",
                    "data_type": "orders",
                    "provider": FakeProviderAdapter.code,
                    "backend_id": self.backend.id,
                    "store_ids": [(6, 0, self.store.ids)],
                }
            )
            result = wizard.action_sync()
            self.assertEqual(result["tag"], "display_notification")
            self.assertEqual(calls, [(self.store.id, "orders", "import")])

    def test_fake_provider_rejects_unsupported_store_wizard_operation(self):
        from odoo.exceptions import UserError

        patches = self._patch_provider()
        with patches[0], patches[1]:
            wizard = self.env["ecommerce.store.sync.wizard"].create(
                {
                    "operation": "export",
                    "data_type": "inventory",
                    "provider": FakeProviderAdapter.code,
                    "backend_id": self.backend.id,
                    "store_ids": [(6, 0, self.store.ids)],
                }
            )
            with self.assertRaises(UserError):
                wizard.action_sync()

    def test_fake_provider_mapping_is_resolved_by_product_wizard(self):
        mapping = self.env["ecommerce.product.mapping"].create(
            {
                "backend_id": self.backend.id,
                "store_id": self.store.id,
                "external_id": "9001",
                "odoo_template_id": self.template.id,
                "external_product_type": "simple",
            }
        )
        self.assertTrue(mapping)
        patches = self._patch_provider()
        with patches[0], patches[1]:
            wizard = self.env["ecommerce.product.sync.wizard"].create(
                {
                    "operation": "update",
                    "provider": FakeProviderAdapter.code,
                    "backend_id": self.backend.id,
                    "store_ids": [(6, 0, self.store.ids)],
                    "product_ids": [(6, 0, self.template.product_variant_id.ids)],
                }
            )
            wizard._compute_existing_status()
            self.assertIn("Mapped (external ID 9001)", wizard.existing_status)


class TestGenericNavigation(TransactionCase):
    def test_generic_mapping_menus_exist(self):
        for xmlid in (
            "menu_ecommerce_product_mappings",
            "menu_ecommerce_variant_mappings",
            "menu_ecommerce_customer_mappings",
            "menu_ecommerce_order_mappings",
            "menu_ecommerce_category_mappings",
            "menu_ecommerce_invoice_mappings",
            "menu_ecommerce_payment_mappings",
            "menu_ecommerce_refund_mappings",
            "menu_ecommerce_shipment_mappings",
            "menu_ecommerce_issues",
            "menu_ecommerce_sync_states",
        ):
            self.assertTrue(
                self.env.ref("odoo_ecommerce_integration.%s" % xmlid),
                xmlid,
            )

    def test_view_jobs_action_is_scoped_to_ecommerce(self):
        company = self.env.company
        backend = self.env["ecommerce.backend"].create(
            {
                "name": "Jobs Backend",
                "code": "jobs",
                "provider": "magento",
                "base_url": "https://jobs.example.test",
                "job_user_id": self.env.user.id,
            }
        )
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Jobs WH", "code": "JWH", "company_id": company.id}
        )
        store = self.env["ecommerce.store"].create(
            {
                "name": "Jobs Store",
                "code": "jobs",
                "backend_id": backend.id,
                "company_id": company.id,
                "external_store_view_code": "default",
                "warehouse_id": warehouse.id,
                "stock_location_id": warehouse.lot_stock_id.id,
            }
        )
        action = store.action_view_jobs()
        self.assertEqual(action["res_model"], "queue.job")
        self.assertIn(("channel", "=like", "ecommerce%"), action["domain"])


class TestHardening(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Hardening WH", "code": "HDW", "company_id": cls.company.id}
        )
        cls.backend = cls.env["ecommerce.backend"].create(
            {
                "name": "Hardening Backend",
                "code": "hardening",
                "provider": "magento",
                "base_url": "https://hardening.example.test",
                "job_user_id": cls.env.user.id,
            }
        )
        cls.store = cls.env["ecommerce.store"].create(
            {
                "name": "Hardening Store",
                "code": "hardening",
                "backend_id": cls.backend.id,
                "company_id": cls.company.id,
                "external_store_view_code": "default",
                "warehouse_id": cls.warehouse.id,
                "stock_location_id": cls.warehouse.lot_stock_id.id,
            }
        )
        cls.template = cls.env["product.template"].create(
            {
                "name": "Hardening Product",
                "default_code": "HARD-1",
                "sale_ok": True,
                "type": "consu",
            }
        )

    def _mapping(self, template=None):
        return self.env["ecommerce.product.mapping"].create(
            {
                "backend_id": self.backend.id,
                "store_id": self.store.id,
                "external_id": "HARD-EXT-1",
                "odoo_template_id": (template or self.template).id,
                "external_product_type": "simple",
            }
        )

    def test_readonly_user_cannot_open_sync_wizard(self):
        from odoo.exceptions import AccessError

        user = self.env["res.users"].create(
            {
                "name": "Readonly eCommerce",
                "login": "readonly-ecommerce-hardening",
                "company_id": self.company.id,
                "company_ids": [(6, 0, [self.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "odoo_ecommerce_integration.group_ecommerce_user"
                            ).id,
                        ],
                    )
                ],
            }
        )
        with self.assertRaises(AccessError):
            self.store.with_user(user).action_open_ecommerce_sync_wizard()

    def test_queue_job_uses_store_company(self):
        self.store._ecommerce_enqueue_job(
            "action_view_jobs",
            channel="ecommerce.catalog",
            identity_key="test:queue-company",
        )
        job = self.env["queue.job"].search(
            [("identity_key", "=", "test:queue-company")], limit=1
        )
        self.assertTrue(job)
        self.assertEqual(job.company_id, self.store.company_id)

    def test_store_backend_change_blocked_with_mapping(self):
        from odoo.exceptions import UserError

        self._mapping()
        other_backend = self.backend.copy({"code": "hardening-other"})
        with self.assertRaises(UserError):
            self.store.backend_id = other_backend

    def test_mapping_rejects_cross_company_template(self):
        from odoo.exceptions import ValidationError

        other_company = self.env["res.company"].create({"name": "Hardening Other Co"})
        other_template = self.env["product.template"].create(
            {
                "name": "Other Company Product",
                "default_code": "HARD-OTHER",
                "company_id": other_company.id,
            }
        )
        with self.assertRaises(ValidationError):
            self._mapping(other_template)

    def test_dashboard_filters_and_drilldown(self):
        self._mapping()
        data = self.env["ecommerce.dashboard"].get_dashboard_data(
            {
                "company_ids": [self.company.id],
                "provider": "magento",
                "backend_id": self.backend.id,
                "store_id": self.store.id,
            }
        )
        self.assertTrue(data["has_stores"])
        self.assertEqual(data["coverage"]["products"]["mapped"], 1)
        self.assertGreaterEqual(data["coverage"]["products"]["total"], 1)
        action = self.env["ecommerce.dashboard"].get_drilldown(
            "mapped_products",
            {
                "company_ids": [self.company.id],
                "store_id": self.store.id,
            },
        )
        self.assertEqual(action["res_model"], "ecommerce.product.mapping")
        self.assertIn(("store_id", "in", [self.store.id]), action["domain"])


class TestSyncRunProgress(TransactionCase):
    def test_batch_progress_is_idempotent_and_completes(self):
        company = self.env.company
        warehouse = self.env["stock.warehouse"].create(
            {"name": "Run WH", "code": "RUNW", "company_id": company.id}
        )
        backend = self.env["ecommerce.backend"].create(
            {
                "name": "Run Backend",
                "code": "run",
                "provider": "magento",
                "base_url": "https://run.example.test",
                "job_user_id": self.env.user.id,
            }
        )
        store = self.env["ecommerce.store"].create(
            {
                "name": "Run Store",
                "code": "run",
                "backend_id": backend.id,
                "company_id": company.id,
                "external_store_view_code": "default",
                "warehouse_id": warehouse.id,
                "stock_location_id": warehouse.lot_stock_id.id,
            }
        )
        run = store._ecommerce_start_run("product", "import", total=2)
        run._record_batch("one", succeeded=1)
        run._record_batch("one", succeeded=1)
        self.assertEqual(run.processed, 1)
        run._record_batch("two", succeeded=1)
        self.assertEqual(run.state, "done")
        self.assertEqual(run.processed, 2)
