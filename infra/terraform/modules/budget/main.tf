# Owner-approved monthly cap is UNRESOLVED (02_decisions). The amount is a required input with no default.
variable "name" { type = string }
variable "monthly_limit_usd" {
  type        = number
  description = "AWS budgets are in USD: convert the owner-approved GBP cap when binding."
}
variable "alert_emails" { type = list(string) }

resource "aws_budgets_budget" "monthly" {
  name         = "${var.name}-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_limit_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = notification.value == 100 ? "FORECASTED" : "ACTUAL"
      subscriber_email_addresses = var.alert_emails
    }
  }
}
