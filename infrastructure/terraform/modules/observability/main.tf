# One log group (docker awslogs driver: streams api/web/caddy), one SNS topic, two alarms:
# month-to-date EstimatedCharges (billing metrics live in us-east-1 and need "Receive
# Billing Alerts" enabled once in the console) and instance status.

resource "aws_cloudwatch_log_group" "app" {
  name              = "/${var.name}/app"
  retention_in_days = var.log_retention_days
}

resource "aws_sns_topic" "alarms" {
  name = "${var.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "estimated_charges" {
  alarm_name          = "${var.name}-estimated-charges"
  alarm_description   = "Month-to-date AWS charges exceeded the demo threshold"
  namespace           = "AWS/Billing"
  metric_name         = "EstimatedCharges"
  statistic           = "Maximum"
  period              = 21600
  evaluation_periods  = 1
  threshold           = var.daily_cost_alarm_usd
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { Currency = "USD" }
  alarm_actions       = [aws_sns_topic.alarms.arn]
  treat_missing_data  = "notBreaching"
}
