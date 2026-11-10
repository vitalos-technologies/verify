# Infrastructure, environments and deployment design

Version 1.0 | 10 November 2026 | Planning baseline

## Proposed AWS topology
Core region eu-west-2 London. Separate cloud accounts or equivalently strong boundaries for development, staging and production. Route 53/approved DNS and ACM certificates; CloudFront for static assets only; load balancer to ECS Fargate API/web and worker services; RDS PostgreSQL; S3 evidence buckets; SQS and dead-letter queues; KMS; Secrets Manager; CloudWatch and CloudTrail. WAF/rate limiting as justified. Private database, encrypted storage and restricted egress. Evaluate networking/NAT and database baseline costs before approving the topology; a pilot cost cap may require a simpler managed deployment with equivalent security.

## Residency
Explicit region matrix per service, logs, backups and supplier. No automatic cross-region evidence replication. A separately approved EU supplier region can coexist with UK core only under disclosed, reviewed processing terms. Region capability must be checked in account before provisioning; AWS liveness is not assumed available in London (S09).

## Infrastructure as code specification
Terraform modules: account_baseline, network, compute, database, evidence_storage, queues, identity, observability and DNS. Inputs include region, allowed environments, deletion protection, retention, tenant limits and budget alerts. Store remote state encrypted with locking and restricted access. Policy checks deny public evidence buckets, public database ingress, unrestricted runtime IAM and unencrypted persistence. This pack contains a design, not executable production Terraform or cloud changes.

## Deployment flow
PR -> lint/types/unit/contract/security checks -> review -> immutable build -> staging deployment -> migration test -> smoke and acceptance tests -> release record -> controlled production rollout -> monitor -> promote or rollback. Source SHA, image digest, migration version, configuration digest and policy versions recorded. Canary uses permitted synthetic transactions; do not upload real IDs into staging. Health checks avoid sensitive data.

## Rollback
Keep previous application image deployable; expand/contract schemas tolerate mixed versions. For a bad adapter/model change, disable new sessions for affected capability, preserve evidence and route existing work for reconciliation. Do not mass-reclassify old decisions automatically. Data rollback is a separate recovery procedure, not routine app rollback. Replaying queues after rollback requires deduplication and correct schema versions.

## Recovery
Automated backups, point-in-time recovery where supported and protected backup access. Proposed GA RPO 15 minutes/RTO four hours; prove with a timed isolated restore, application reconciliation, deletion tombstone replay and evidence access verification. A database snapshot alone does not restore provider sessions, object evidence or external webhooks. Maintain recovery manifest across these systems.

## Environment gates
Development uses dummy/sandbox suppliers and synthetic data. Staging mimics isolation and IAM but excludes live biometric data. Pilot production has tenant allowlist, capped volume and staffed incident contact. General production requires M07 gates and approved actual cost cap. No deployment credentials in prompts, docs or screenshots.
