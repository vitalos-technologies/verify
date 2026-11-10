# Staging: mirrors production isolation and IAM, synthetic data only, no live biometric data (14_infrastructure).
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
  backend "s3" {} # bucket/key/region/dynamodb_table via -backend-config=backend.hcl (owner provides)
}

provider "aws" {
  region              = "eu-west-2"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = { Product = "vitalos-verify", Environment = "staging", ManagedBy = "terraform" }
  }
}

variable "account_id" { type = string }
variable "certificate_arn" { type = string }
variable "api_image" {
  type        = string
  description = "Immutable image reference with digest (…@sha256:…)."
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.api_image))
    error_message = "Deploy images by digest."
  }
}
variable "web_image" {
  type = string
  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.web_image))
    error_message = "Deploy images by digest."
  }
}
variable "monthly_limit_usd" { type = number }
variable "alert_emails" { type = list(string) }
variable "alarm_topic_arn" { type = string }

locals { name = "vv-staging" }

module "network" {
  source = "../../modules/network"
  name   = local.name
  azs    = ["eu-west-2a", "eu-west-2b"]
}

module "evidence" {
  source = "../../modules/evidence_storage"
  name   = local.name
}

module "queues" {
  source = "../../modules/queues"
  name   = local.name
}

module "observability" {
  source          = "../../modules/observability"
  name            = local.name
  alarm_topic_arn = var.alarm_topic_arn
  dlq_names       = module.queues.dlq_names
}

module "compute" {
  source                = "../../modules/compute"
  name                  = local.name
  vpc_id                = module.network.vpc_id
  private_subnet_ids    = module.network.private_subnet_ids
  public_subnet_ids     = module.network.public_subnet_ids
  certificate_arn       = var.certificate_arn
  api_image             = var.api_image
  web_image             = var.web_image
  evidence_bucket_arn   = module.evidence.bucket_arn
  evidence_kms_key_arn  = module.evidence.kms_key_arn
  evidence_bucket_name  = module.evidence.bucket_name
  tombstone_bucket_arn  = module.evidence.tombstone_bucket_arn
  tombstone_bucket_name = module.evidence.tombstone_bucket_name
  queue_arns            = values(module.queues.queue_arns)
  secret_arns           = [module.database.master_secret_arn]
  log_group_names       = module.observability.log_group_names
}

module "database" {
  source                 = "../../modules/database"
  name                   = local.name
  vpc_id                 = module.network.vpc_id
  subnet_ids             = module.network.private_subnet_ids
  app_security_group_ids = [module.compute.app_security_group_id]
}

module "budget" {
  source            = "../../modules/budget"
  name              = local.name
  monthly_limit_usd = var.monthly_limit_usd
  alert_emails      = var.alert_emails
}

output "alb_dns_name" { value = module.compute.alb_dns_name }
