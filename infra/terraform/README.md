# Infrastructure (Terraform) — not applied

Design from `docs/spec/14_infrastructure_and_delivery.md`: AWS eu-west-2, separate accounts per environment, private RDS PostgreSQL, KMS-encrypted private evidence bucket, SQS with DLQs, ECS Fargate API/worker, CloudWatch, budget alarms at 50/80/100%.

**Status:** code only. Nothing has been planned or applied; no AWS account is bound and no spend is approved (M02-T04 blocked on owner). CI runs `terraform fmt -check` and `terraform validate` with no credentials.

To use later (owner action): create the AWS accounts, a state bucket + lock table, then
`terraform -chdir=envs/staging init -backend-config=backend.hcl` and review `plan` before any `apply`.

Guard rails encoded here: public access blocked on evidence, deny non-TLS, no public DB, encrypted storage/queues/logs, deletion protection on, 35-day backups, no cross-region evidence replication, region pinned to eu-west-2.
