variable "name" { type = string }
variable "queues" {
  type    = list(string)
  default = ["provider-events", "webhook-deliveries", "deletions"]
}

resource "aws_sqs_queue" "dlq" {
  for_each                  = toset(var.queues)
  name                      = "${var.name}-${each.key}-dlq"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "this" {
  for_each                   = toset(var.queues)
  name                       = "${var.name}-${each.key}"
  visibility_timeout_seconds = 300
  sqs_managed_sse_enabled    = true
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = 8
  })
}

output "queue_arns" { value = { for k, q in aws_sqs_queue.this : k => q.arn } }
output "dlq_names" { value = { for k, q in aws_sqs_queue.dlq : k => q.name } }
