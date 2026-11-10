# Bootstrap, run once per AWS account (staging, then production) by the owner with local state.
# Creates: Terraform state bucket (versioned, KMS-encrypted, public access blocked, TLS only),
# DynamoDB lock table, GitHub Actions OIDC provider and a PLAN-ONLY role for CI.
# It does not create application resources and grants no apply/deploy rights.
# Steps: docs/infrastructure/aws-setup.md section 6. Not applied by any agent.
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
  }
}

provider "aws" {
  region              = "eu-west-2"
  allowed_account_ids = [var.account_id]
  default_tags {
    tags = { Product = "vitalos-verify", Environment = var.environment, ManagedBy = "terraform-bootstrap" }
  }
}

variable "account_id" {
  type        = string
  description = "12-digit AWS account ID this bootstrap is allowed to touch (guards against the wrong profile)."
  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be 12 digits."
  }
}

variable "environment" {
  type        = string
  description = "staging or production."
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique S3 bucket name for Terraform state, e.g. vv-staging-tfstate-<account id>."
}

variable "lock_table_name" {
  type    = string
  default = "vv-terraform-locks"
}

variable "github_org" {
  type    = string
  default = "vitalos-technologies"
}

variable "github_repo" {
  type    = string
  default = "verify"
}

variable "create_github_oidc_provider" {
  type        = bool
  default     = true
  description = "Set false if this account already has the token.actions.githubusercontent.com provider."
}

variable "existing_github_oidc_provider_arn" {
  type        = string
  default     = ""
  description = "ARN of the existing provider when create_github_oidc_provider = false."
}

locals {
  name         = "vv-${var.environment}"
  state_prefix = "verify/"
  oidc_arn     = var.create_github_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : var.existing_github_oidc_provider_arn
  # Plan runs on pull requests and on main. No other branch, tag or environment can assume the role.
  github_subjects = [
    "repo:${var.github_org}/${var.github_repo}:pull_request",
    "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main",
  ]
}

# ---------------------------------------------------------------- state bucket

resource "aws_kms_key" "state" {
  description             = "${local.name} terraform state"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_kms_alias" "state" {
  name          = "alias/${local.name}-tfstate"
  target_key_id = aws_kms_key.state.key_id
}

resource "aws_s3_bucket" "state" {
  bucket        = var.state_bucket_name
  force_destroy = false
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.state.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    id     = "keep-90-days-of-old-state"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 90 }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.state]
}

# ------------------------------------------------------------------ lock table

resource "aws_dynamodb_table" "lock" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption { enabled = true }
  point_in_time_recovery { enabled = true }
  deletion_protection_enabled = true
}

# ------------------------------------------------------- GitHub Actions OIDC

resource "aws_iam_openid_connect_provider" "github" {
  count           = var.create_github_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

data "aws_iam_policy_document" "github_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = local.github_subjects
    }
  }
}

resource "aws_iam_role" "plan" {
  name                 = "${local.name}-github-plan"
  description          = "GitHub Actions terraform plan only. No apply, no data-plane reads."
  assume_role_policy   = data.aws_iam_policy_document.github_assume.json
  max_session_duration = 3600
}

# Read configuration of resources so `terraform plan` can refresh state.
resource "aws_iam_role_policy_attachment" "plan_read_only" {
  role       = aws_iam_role.plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

data "aws_iam_policy_document" "plan" {
  statement {
    sid       = "ReadState"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/${local.state_prefix}*"]
  }
  statement {
    sid       = "DecryptState"
    actions   = ["kms:Decrypt", "kms:DescribeKey"]
    resources = [aws_kms_key.state.arn]
  }
  statement {
    sid       = "UseLock"
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:DescribeTable"]
    resources = [aws_dynamodb_table.lock.arn]
  }
  # ReadOnlyAccess includes some data-plane reads. Evidence, secrets, queues and logs stay off-limits.
  statement {
    sid    = "DenyDataPlaneReads"
    effect = "Deny"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:GetObjectAttributes",
    ]
    not_resources = ["${aws_s3_bucket.state.arn}/*"]
  }
  statement {
    sid    = "DenySecretsAndMessages"
    effect = "Deny"
    actions = [
      "secretsmanager:GetSecretValue",
      "ssm:GetParameter",
      "ssm:GetParameters",
      "ssm:GetParametersByPath",
      "sqs:ReceiveMessage",
      "logs:GetLogEvents",
      "logs:FilterLogEvents",
      "logs:StartQuery",
      "rds-data:ExecuteStatement",
      "dynamodb:Scan",
      "dynamodb:Query",
    ]
    resources = ["*"]
  }
  statement {
    sid           = "DenyOtherDecrypt"
    effect        = "Deny"
    actions       = ["kms:Decrypt"]
    not_resources = [aws_kms_key.state.arn]
  }
  statement {
    sid    = "DenyWrites"
    effect = "Deny"
    actions = [
      "s3:PutObject",
      "s3:DeleteObject",
      "iam:PassRole",
      "sts:AssumeRole",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "plan" {
  name   = "${local.name}-github-plan"
  role   = aws_iam_role.plan.id
  policy = data.aws_iam_policy_document.plan.json
}

# --------------------------------------------------------------------- outputs

output "backend_hcl" {
  description = "Paste into infra/terraform/envs/<env>/backend.hcl (not committed if it reveals account details you want private)."
  value       = <<-EOT
    bucket         = "${aws_s3_bucket.state.id}"
    key            = "${local.state_prefix}${var.environment}/terraform.tfstate"
    region         = "eu-west-2"
    dynamodb_table = "${aws_dynamodb_table.lock.name}"
    encrypt        = true
    kms_key_id     = "${aws_kms_key.state.arn}"
  EOT
}

output "plan_role_arn" {
  description = "Set as the GitHub Actions variable AWS_PLAN_ROLE_ARN_<ENV> (not a secret)."
  value       = aws_iam_role.plan.arn
}
