# ECS Fargate API, worker and web. Images by immutable digest. Runtime roles are least-privilege and
# separate from the migration role (run as a one-off task by the release pipeline, not defined here).
variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "public_subnet_ids" { type = list(string) }
variable "certificate_arn" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "evidence_bucket_arn" { type = string }
variable "evidence_kms_key_arn" { type = string }
variable "evidence_bucket_name" { type = string }
variable "tombstone_bucket_arn" { type = string }
variable "tombstone_bucket_name" { type = string }
variable "queue_arns" { type = list(string) }
variable "secret_arns" { type = list(string) }
variable "log_group_names" { type = map(string) }

resource "aws_ecs_cluster" "this" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_security_group" "alb" {
  name   = "${var.name}-alb"
  vpc_id = var.vpc_id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name   = "${var.name}-app"
  vpc_id = var.vpc_id
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb" "this" {
  name                       = var.name
  load_balancer_type         = "application"
  subnets                    = var.public_subnet_ids
  security_groups            = [aws_security_group.alb.id]
  drop_invalid_header_fields = true
  enable_deletion_protection = true
}

resource "aws_lb_target_group" "api" {
  name        = "${var.name}-api"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check { path = "/healthz" }
}

resource "aws_lb_target_group" "web" {
  name        = "${var.name}-web"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id
  health_check { path = "/" }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.certificate_arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern { values = ["/v1/*", "/callbacks/*", "/healthz"] }
  }
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = var.secret_arns }]
  })
}

resource "aws_iam_role" "runtime" {
  name               = "${var.name}-runtime"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "runtime" {
  role = aws_iam_role.runtime.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], Resource = "${var.evidence_bucket_arn}/*" },
      { Effect = "Allow", Action = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey"], Resource = var.evidence_kms_key_arn },
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject"], Resource = "${var.tombstone_bucket_arn}/tombstones/*" },
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = var.tombstone_bucket_arn },
      { Effect = "Allow", Action = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:ChangeMessageVisibility", "sqs:GetQueueAttributes"], Resource = var.queue_arns },
    ]
  })
}

locals {
  services = {
    api    = { image = var.api_image, command = ["vv-api"], port = 8000, tg = aws_lb_target_group.api.arn }
    worker = { image = var.api_image, command = ["vv-worker"], port = null, tg = null }
    web    = { image = var.web_image, command = null, port = 3000, tg = aws_lb_target_group.web.arn }
  }
}

resource "aws_ecs_task_definition" "this" {
  for_each                 = local.services
  family                   = "${var.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.runtime.arn
  container_definitions = jsonencode([merge(each.value.command == null ? {} : { command = each.value.command }, {
    name                   = each.key
    image                  = each.value.image
    essential              = true
    readonlyRootFilesystem = true
    portMappings           = each.value.port == null ? [] : [{ containerPort = each.value.port }]
    environment = [
      { name = "VV_ENV", value = "staging" },
      { name = "VV_EVIDENCE_BUCKET", value = var.evidence_bucket_name },
      { name = "VV_EVIDENCE_KMS_KEY_ID", value = var.evidence_kms_key_arn },
      { name = "VV_TOMBSTONE_BUCKET", value = var.tombstone_bucket_name },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = var.log_group_names[each.key]
        awslogs-region        = "eu-west-2"
        awslogs-stream-prefix = each.key
      }
    }
  })])
}

resource "aws_ecs_service" "this" {
  for_each        = local.services
  name            = each.key
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this[each.key].arn
  desired_count   = 1
  launch_type     = "FARGATE"
  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }
  dynamic "load_balancer" {
    for_each = each.value.tg == null ? [] : [1]
    content {
      target_group_arn = each.value.tg
      container_name   = each.key
      container_port   = each.value.port
    }
  }
}

output "app_security_group_id" { value = aws_security_group.app.id }
output "alb_dns_name" { value = aws_lb.this.dns_name }
