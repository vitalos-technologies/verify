# Private, KMS-encrypted evidence bucket. No public access, TLS only, no cross-region replication.
variable "name" { type = string }
variable "noncurrent_days" {
  type        = number
  default     = 35
  description = "Matches backup retention; application deletes current objects per retention profile."
}

data "aws_caller_identity" "current" {}

resource "aws_kms_key" "evidence" {
  description             = "${var.name} evidence"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

resource "aws_s3_bucket" "evidence" {
  bucket        = "${var.name}-evidence-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
}

resource "aws_s3_bucket_ownership_controls" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_public_access_block" "evidence" {
  bucket                  = aws_s3_bucket.evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.evidence.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_lifecycle_configuration" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  rule {
    id     = "expire-noncurrent"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = var.noncurrent_days }
    abort_incomplete_multipart_upload { days_after_initiation = 1 }
  }
}

resource "aws_s3_bucket_policy" "evidence" {
  bucket = aws_s3_bucket.evidence.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.evidence.arn, "${aws_s3_bucket.evidence.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

output "bucket_arn" { value = aws_s3_bucket.evidence.arn }
output "bucket_name" { value = aws_s3_bucket.evidence.bucket }
output "kms_key_arn" { value = aws_kms_key.evidence.arn }

# Tombstone log (IMP-18): deletion records kept OUTSIDE database backups and replayed after any restore.
# Separate bucket with object lock so a deletion record cannot be removed early.
resource "aws_s3_bucket" "tombstones" {
  bucket              = "${var.name}-tombstones-${data.aws_caller_identity.current.account_id}"
  object_lock_enabled = true
  force_destroy       = false
}

resource "aws_s3_bucket_ownership_controls" "tombstones" {
  bucket = aws_s3_bucket.tombstones.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_public_access_block" "tombstones" {
  bucket                  = aws_s3_bucket.tombstones.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "tombstones" {
  bucket = aws_s3_bucket.tombstones.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tombstones" {
  bucket = aws_s3_bucket.tombstones.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.evidence.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_object_lock_configuration" "tombstones" {
  bucket = aws_s3_bucket.tombstones.id
  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = 400 # longer than backup retention plus audit window
    }
  }
}

resource "aws_s3_bucket_policy" "tombstones" {
  bucket = aws_s3_bucket.tombstones.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.tombstones.arn, "${aws_s3_bucket.tombstones.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
}

output "tombstone_bucket_arn" { value = aws_s3_bucket.tombstones.arn }
output "tombstone_bucket_name" { value = aws_s3_bucket.tombstones.bucket }
