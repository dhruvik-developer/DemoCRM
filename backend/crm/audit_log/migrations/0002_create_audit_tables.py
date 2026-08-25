# Creates the real database tables for the unmanaged models in this app.
#
# The models AuditLog and Activity are declared with managed = False, so
# Django never creates their tables (0001_initial was recorded as applied
# without executing any SQL). This migration creates them via raw DDL so
# every environment gets the tables through the normal `migrate` flow.
#
# The DDL mirrors exactly the current model definitions in audit_log/models.py.

from django.db import migrations


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS audit_log (
    "id" uuid NOT NULL,
    "user_id" uuid NOT NULL,
    "entity_type" varchar(100) NOT NULL,
    "entity_id" uuid NOT NULL,
    "action" varchar(100) NOT NULL,
    "old_value" jsonb NULL,
    "new_value" jsonb NULL,
    "metadata" jsonb NULL,
    "created_at" timestamp with time zone NOT NULL,
    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "audit_log_user_id_a5f7c2_fk" FOREIGN KEY ("user_id") REFERENCES "accounts_customuser" ("user_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS "audit_log_user_id_a5f7c2_idx" ON "audit_log" ("user_id");

CREATE TABLE IF NOT EXISTS activity (
    "id" uuid NOT NULL,
    "lead_id" uuid NULL,
    "customer_id" uuid NULL,
    "quotation_id" uuid NULL,
    "created_by_id" uuid NOT NULL,
    "activity_type" varchar(30) NOT NULL,
    "outcome" varchar(255) NOT NULL,
    "notes" text NULL,
    "follow_up_required" boolean NOT NULL,
    "follow_up_date" timestamp with time zone NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    CONSTRAINT "activity_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "activity_lead_id_8f2b41_fk" FOREIGN KEY ("lead_id") REFERENCES "lead" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "activity_customer_id_6d93a0_fk" FOREIGN KEY ("customer_id") REFERENCES "customer" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "activity_quotation_id_1c47e8_fk" FOREIGN KEY ("quotation_id") REFERENCES "quotation" ("id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "activity_created_by_id_9b21d5_fk" FOREIGN KEY ("created_by_id") REFERENCES "accounts_customuser" ("user_id") DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX IF NOT EXISTS "activity_lead_id_8f2b41_idx" ON "activity" ("lead_id");
CREATE INDEX IF NOT EXISTS "activity_customer_id_6d93a0_idx" ON "activity" ("customer_id");
CREATE INDEX IF NOT EXISTS "activity_quotation_id_1c47e8_idx" ON "activity" ("quotation_id");
CREATE INDEX IF NOT EXISTS "activity_created_by_id_9b21d5_idx" ON "activity" ("created_by_id");
"""

REVERSE_SQL = """
DROP TABLE IF EXISTS activity CASCADE;
DROP TABLE IF EXISTS audit_log CASCADE;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        # quotation table is created in customer_management.0003
        (
            "customer_management",
            "0003_pipelinestage_quotation_approval_required_and_more",
        ),
        ("audit_log", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_SQL, reverse_sql=REVERSE_SQL),
    ]
