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
