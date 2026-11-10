# AWS setup — owner steps

| Field | Value |
|---|---|
| Who | **Owner only** (Temitope Agbola). Agents must not create accounts, buckets or roles. |
| Region | **eu-west-2 (London)** for everything except AWS global services |
| Accounts | management, staging, production (spec 14; ADR-06) |
| Cost | Creating accounts, the organisation, Identity Center, budgets and a basic CloudTrail organisation trail has little or no direct cost; S3/DynamoDB/KMS for state cost pennies to a few pounds a month. Running the application stack is what costs money — **do not apply `infra/terraform/envs/*` until the monthly cap is approved** (`docs/commercial/pilot-plan.md`). |
| Unblocks | M02-T04 (environment baseline) |
| Time | About half a day |

Replace every `<…>` placeholder. Values you will collect as you go:

| Value | Where it comes from | Record here |
|---|---|---|
| `MGMT_ID` | Management account ID | [Owner to complete] |
| `ORG_ID` | `aws organizations describe-organization` | [Owner to complete] |
| `STAGING_ID` | Staging account ID | [Owner to complete] |
| `PROD_ID` | Production account ID | [Owner to complete] |
| Account emails | Use three distinct mailboxes/aliases you control, e.g. `aws-management@vitalos.co.uk`, `aws-staging@…`, `aws-production@…` | [Owner to complete] |
| Alert email | Budget and security alerts | [Owner to complete] |

## 0. Before you start

- [ ] A password manager.
- [ ] Two second-factor devices for the root user: a hardware security key/passkey (preferred) **and** an authenticator app as backup.
- [ ] AWS CLI v2 (`aws --version`) and Terraform 1.9.x (`terraform version`; CI uses 1.9.8).
- [ ] Three mailboxes/aliases for the accounts.

## 1. Management account and root MFA

1. Sign up at https://aws.amazon.com with the management email. Account name: `vitalos-management`. Use Vitalos Technologies company details.
2. Sign in as root → top-right account menu → **Security credentials** → **Multi-factor authentication** → **Assign MFA device**. Register the security key/passkey, then register the authenticator app as a second device.
3. **Do not create root access keys.** If any exist, delete them.
4. Account menu → **Account** → **Alternate contacts**: set Billing, Operations and Security contacts.
5. Account → **IAM user and role access to Billing information** → Activate (so Identity Center users can see billing).
6. Billing → **Billing preferences**: turn on alerts for free-tier usage and invoice by email.
7. Store the root email, password and recovery details in the password manager. From now on use root only for tasks that need it.

## 2. Create the organisation and member accounts

Open **CloudShell** (top bar, region London) while signed in to the management account, or use your CLI with temporary credentials.

```bash
aws organizations create-organization --feature-set ALL
ROOT_ID=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
ORG_ID=$(aws organizations describe-organization --query 'Organization.Id' --output text)
OU_ID=$(aws organizations create-organizational-unit --parent-id "$ROOT_ID" --name Workloads \
  --query 'OrganizationalUnit.Id' --output text)

aws organizations create-account --email <aws-staging@…> --account-name vitalos-verify-staging \
  --iam-user-access-to-billing ALLOW
aws organizations create-account --email <aws-production@…> --account-name vitalos-verify-production \
  --iam-user-access-to-billing ALLOW

# Wait until both show SUCCEEDED, then note the account IDs
aws organizations list-create-account-status --states SUCCEEDED \
  --query 'CreateAccountStatuses[].[AccountName,AccountId]' --output table
```

Move both into the Workloads OU:

```bash
aws organizations move-account --account-id <STAGING_ID> --source-parent-id "$ROOT_ID" --destination-parent-id "$OU_ID"
aws organizations move-account --account-id <PROD_ID>    --source-parent-id "$ROOT_ID" --destination-parent-id "$OU_ID"
```

### Remove root passwords from member accounts (centralised root access)

Member accounts don't need their own root logins:

```bash
aws organizations enable-aws-service-access --service-principal iam.amazonaws.com
aws iam enable-organizations-root-credentials-management
aws iam enable-organizations-root-sessions
```

New member accounts created by Organizations have no root password. Keep it that way.

## 3. Guard rails: region lock, protect logging, AI opt-out

```bash
aws organizations enable-policy-type --root-id "$ROOT_ID" --policy-type SERVICE_CONTROL_POLICY
aws organizations enable-policy-type --root-id "$ROOT_ID" --policy-type AISERVICES_OPT_OUT_POLICY
```

Save as `scp-guardrails.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyOutsideLondon",
      "Effect": "Deny",
      "NotAction": [
        "acm:*", "budgets:*", "ce:*", "cloudfront:*", "cur:*", "globalaccelerator:*", "health:*",
        "iam:*", "kms:*", "organizations:*", "pricing:*", "route53:*", "route53domains:*",
        "s3:GetAccountPublic*", "s3:ListAllMyBuckets", "s3:PutAccountPublic*", "shield:*",
        "sts:*", "support:*", "trustedadvisor:*", "waf:*", "wafv2:*", "sso:*", "account:*",
        "billing:*", "payments:*", "tax:*", "freetier:*", "notifications:*"
      ],
      "Resource": "*",
      "Condition": { "StringNotEquals": { "aws:RequestedRegion": ["eu-west-2"] } }
    },
    {
      "Sid": "DenyLeavingOrg",
      "Effect": "Deny",
      "Action": ["organizations:LeaveOrganization"],
      "Resource": "*"
    },
    {
      "Sid": "ProtectCloudTrail",
      "Effect": "Deny",
      "Action": ["cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "cloudtrail:UpdateTrail"],
      "Resource": "*"
    },
    {
      "Sid": "NoLongLivedUserKeys",
      "Effect": "Deny",
      "Action": ["iam:CreateAccessKey", "iam:CreateUser"],
      "Resource": "*"
    }
  ]
}
```

Save as `ai-opt-out.json` (stops AWS AI services, including Rekognition, using content to improve AWS services — S09):

```json
{ "services": { "default": { "opt_out_policy": { "@@assign": "optOut" } } } }
```

Attach:

```bash
SCP_ID=$(aws organizations create-policy --type SERVICE_CONTROL_POLICY --name vv-guardrails \
  --description "London only, protect CloudTrail, no IAM users" --content file://scp-guardrails.json \
  --query 'Policy.PolicySummary.Id' --output text)
aws organizations attach-policy --policy-id "$SCP_ID" --target-id "$OU_ID"

AI_ID=$(aws organizations create-policy --type AISERVICES_OPT_OUT_POLICY --name vv-ai-opt-out \
  --description "Opt out of AI service data use" --content file://ai-opt-out.json \
  --query 'Policy.PolicySummary.Id' --output text)
aws organizations attach-policy --policy-id "$AI_ID" --target-id "$ROOT_ID"
```

Notes:
- SCPs don't restrict the management account; keep workloads out of it.
- The region lock **blocks AWS Face Liveness** (only offered in Ireland, not London). That's intentional: add `eu-west-1` only after a recorded decision and transfer assessment (`docs/compliance/DPIA.md` §A7).
- If a needed global service is denied, add it to `NotAction` rather than removing the region lock.

## 4. IAM Identity Center (day-to-day sign-in)

Console (management account, region **London**):

1. **IAM Identity Center** → **Enable** → organisation instance.
2. **Settings → Authentication → Multi-factor authentication**: *Every time they sign in*; allowed types: **Authenticator apps** and **Security keys/built-in authenticators**; *Require them to register an MFA device at sign in*.
3. **Settings → Authentication**: session duration 8 hours or less.
4. **Users → Add user**: yourself (work email). Accept the invite, set a password, register MFA.
5. **Permission sets → Create**:

   | Name | Policy | Session |
   |---|---|---|
   | `VVAdmin` | AWS managed `AdministratorAccess` | 1 hour |
   | `VVReadOnly` | AWS managed `ViewOnlyAccess` | 4 hours |
   | `VVBilling` | AWS managed job function `Billing` | 4 hours |

6. **AWS accounts → assign**:

   | Account | Assign |
   |---|---|
   | management | `VVBilling`, `VVAdmin` |
   | staging | `VVAdmin`, `VVReadOnly` |
   | production | `VVReadOnly` (day to day), `VVAdmin` (use only for planned changes) |

7. On your laptop:

```bash
aws configure sso   # SSO start URL from Identity Center dashboard; region eu-west-2
# create profiles: vv-mgmt (management/VVAdmin), vv-staging (staging/VVAdmin), vv-prod (production/VVAdmin)
aws sso login --profile vv-staging
aws sts get-caller-identity --profile vv-staging
```

From here, stop using root.

## 5. Budgets and CloudTrail

### Budgets (management account, covers all accounts)

The monthly cap is **not approved yet** (`docs/commercial/pilot-plan.md` proposes £750 non-labour). AWS Budgets use USD: [Owner to complete: approved GBP cap and USD figure used].

`budget.json`:

```json
{ "BudgetName": "vv-org-monthly", "BudgetType": "COST", "TimeUnit": "MONTHLY",
  "BudgetLimit": { "Amount": "<USD amount>", "Unit": "USD" } }
```

`notifications.json`:

```json
[
  { "Notification": { "NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 50, "ThresholdType": "PERCENTAGE" },
    "Subscribers": [ { "SubscriptionType": "EMAIL", "Address": "<alert email>" } ] },
  { "Notification": { "NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 80, "ThresholdType": "PERCENTAGE" },
    "Subscribers": [ { "SubscriptionType": "EMAIL", "Address": "<alert email>" } ] },
  { "Notification": { "NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 100, "ThresholdType": "PERCENTAGE" },
    "Subscribers": [ { "SubscriptionType": "EMAIL", "Address": "<alert email>" } ] },
  { "Notification": { "NotificationType": "FORECASTED", "ComparisonOperator": "GREATER_THAN", "Threshold": 100, "ThresholdType": "PERCENTAGE" },
    "Subscribers": [ { "SubscriptionType": "EMAIL", "Address": "<alert email>" } ] }
]
```

```bash
aws budgets create-budget --account-id <MGMT_ID> --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json --profile vv-mgmt
```

Also: Billing → **Cost Anomaly Detection** → create a monitor for all accounts with email alerts. The staging Terraform adds a per-account budget (`infra/terraform/modules/budget`) when applied. Budgets alert; they do not stop spending.

### CloudTrail organisation trail (management account)

```bash
export AWS_PROFILE=vv-mgmt
TRAIL_BUCKET=vv-org-cloudtrail-<MGMT_ID>
aws organizations enable-aws-service-access --service-principal cloudtrail.amazonaws.com
aws s3api create-bucket --bucket "$TRAIL_BUCKET" --region eu-west-2 \
  --create-bucket-configuration LocationConstraint=eu-west-2
aws s3api put-public-access-block --bucket "$TRAIL_BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$TRAIL_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$TRAIL_BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

`trail-bucket-policy.json` (replace `<BUCKET>`, `<MGMT_ID>`, `<ORG_ID>`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "AclCheck", "Effect": "Allow", "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:GetBucketAcl", "Resource": "arn:aws:s3:::<BUCKET>",
      "Condition": { "StringEquals": { "aws:SourceArn": "arn:aws:cloudtrail:eu-west-2:<MGMT_ID>:trail/vv-org-trail" } } },
    { "Sid": "WriteMgmt", "Effect": "Allow", "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:PutObject", "Resource": "arn:aws:s3:::<BUCKET>/AWSLogs/<MGMT_ID>/*",
      "Condition": { "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control",
        "aws:SourceArn": "arn:aws:cloudtrail:eu-west-2:<MGMT_ID>:trail/vv-org-trail" } } },
    { "Sid": "WriteOrg", "Effect": "Allow", "Principal": { "Service": "cloudtrail.amazonaws.com" },
      "Action": "s3:PutObject", "Resource": "arn:aws:s3:::<BUCKET>/AWSLogs/<ORG_ID>/*",
      "Condition": { "StringEquals": { "s3:x-amz-acl": "bucket-owner-full-control",
        "aws:SourceArn": "arn:aws:cloudtrail:eu-west-2:<MGMT_ID>:trail/vv-org-trail" } } },
    { "Sid": "DenyInsecureTransport", "Effect": "Deny", "Principal": "*", "Action": "s3:*",
      "Resource": ["arn:aws:s3:::<BUCKET>", "arn:aws:s3:::<BUCKET>/*"],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } } }
  ]
}
```

```bash
aws s3api put-bucket-policy --bucket "$TRAIL_BUCKET" --policy file://trail-bucket-policy.json
aws cloudtrail create-trail --name vv-org-trail --s3-bucket-name "$TRAIL_BUCKET" \
  --is-organization-trail --is-multi-region-trail --enable-log-file-validation --region eu-west-2
aws cloudtrail start-logging --name vv-org-trail --region eu-west-2
```

Log retention: [Owner to complete: e.g. 1 year] — add an S3 lifecycle rule once decided. These are Vitalos security logs (DPIA Part C).

## 6. Terraform state bucket, lock table and GitHub OIDC role (per workload account)

Use the bootstrap config `infra/terraform/bootstrap/main.tf`. It creates, in **one** account:
- S3 state bucket: versioned, KMS-encrypted, public access blocked, TLS only, prevent-destroy;
- DynamoDB lock table `vv-terraform-locks` (encrypted, point-in-time recovery, deletion protection);
- GitHub Actions OIDC provider;
- role `vv-<env>-github-plan`: assumable only from `vitalos-technologies/verify` pull requests and `main`; **plan only** — read-only access, state read, lock use; explicit denies on reading S3 objects (except state), secrets, parameters, queues, logs and on writes.

Run once for staging, then once for production:

```bash
aws sso login --profile vv-staging
export AWS_PROFILE=vv-staging
cd infra/terraform/bootstrap
terraform init
terraform plan -out bootstrap.plan \
  -var account_id=<STAGING_ID> \
  -var environment=staging \
  -var state_bucket_name=vv-staging-tfstate-<STAGING_ID>
terraform apply bootstrap.plan
terraform output -raw backend_hcl > ../envs/staging/backend.hcl
terraform output plan_role_arn
```

For production use `--profile vv-prod`, `environment=production`, `state_bucket_name=vv-production-tfstate-<PROD_ID>` and a separate working copy (or delete `terraform.tfstate` only **after** backing it up — each account's bootstrap has its own local state).

The bootstrap keeps its own state **locally** (`terraform.tfstate`, ignored by git via `infra/terraform/bootstrap/.gitignore`). It holds no secrets but keep a copy in your password manager or encrypted storage.

Then check the backend works (no resources are created by `init`):

```bash
cd ../envs/staging
terraform init -backend-config=backend.hcl
```

**Do not run `plan`/`apply` for `envs/staging` until the cap is approved and the certificate/images exist.**

<details><summary>Equivalent plain CLI for the state bucket and lock table (reference only — use either this or the bootstrap, not both)</summary>

```bash
B=vv-staging-tfstate-<STAGING_ID>
KEY_ID=$(aws kms create-key --description "vv-staging terraform state" --query KeyMetadata.KeyId --output text)
aws kms enable-key-rotation --key-id "$KEY_ID"
aws s3api create-bucket --bucket "$B" --region eu-west-2 --create-bucket-configuration LocationConstraint=eu-west-2
aws s3api put-public-access-block --bucket "$B" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$B" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$B" --server-side-encryption-configuration \
  "{\"Rules\":[{\"ApplyServerSideEncryptionByDefault\":{\"SSEAlgorithm\":\"aws:kms\",\"KMSMasterKeyID\":\"$KEY_ID\"},\"BucketKeyEnabled\":true}]}"
aws dynamodb create-table --table-name vv-terraform-locks --region eu-west-2 \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
```
</details>

### GitHub settings (owner)

GitHub → `vitalos-technologies/verify` → **Settings → Secrets and variables → Actions → Variables** (variables, not secrets — role ARNs are not secret):

| Variable | Value |
|---|---|
| `AWS_PLAN_ROLE_ARN_STAGING` | output `plan_role_arn` from staging bootstrap |
| `AWS_PLAN_ROLE_ARN_PRODUCTION` | output from production bootstrap |

A CI `terraform plan` job using these is **not yet in** `.github/workflows/ci.yml`; engineering adds it after this step. There is deliberately **no apply/deploy role** yet: production deployment needs a separate identity with its own review (spec 11 §Software supply chain).

## 7. Certificates and email sending

### TLS certificate (staging)
`envs/staging` needs `certificate_arn`. [Owner to complete: staging hostnames, e.g. `staging.verify.vitalos.co.uk`, and where DNS for vitalos.co.uk is managed.]

```bash
aws acm request-certificate --domain-name <staging host> --validation-method DNS --region eu-west-2 --profile vv-staging
aws acm describe-certificate --certificate-arn <arn> --region eu-west-2 --profile vv-staging \
  --query 'Certificate.DomainValidationOptions[].ResourceRecord'
```

Add the CNAME shown at your DNS provider; wait for `ISSUED`.

### Amazon SES (magic links and applicant email codes)

Per environment account:

```bash
aws sesv2 create-email-identity --email-identity <sending domain, e.g. verify.vitalos.co.uk> --region eu-west-2 --profile vv-staging
aws sesv2 get-email-identity --email-identity <sending domain> --region eu-west-2 --profile vv-staging \
  --query 'DkimAttributes.Tokens'
```

- Add the three DKIM CNAMEs (`<token>._domainkey.<domain>` → `<token>.dkim.amazonses.com`), an SPF record and a DMARC record at your DNS provider.
- New SES accounts are in the **sandbox** (send only to verified addresses). For production, request production access in the SES console (no charge for the request). Staging can stay in the sandbox.
- Sender address: [Owner to complete: e.g. `no-reply@verify.vitalos.co.uk`].

## 8. Secrets Manager — what to create

Create in **each** environment account separately (`--profile vv-staging`, then `vv-prod`). **Never reuse a staging value in production.** Generating values inside `$(…)` keeps them out of shell history; don't paste them into chat, tickets or docs.

Key generator (32 random bytes, URL-safe base64 — matches `services/api/src/vv/config.py`):

```bash
gen_key() { python3 -c "import secrets,base64;print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"; }
gen_pw()  { python3 -c "import secrets;print(secrets.token_urlsafe(32))"; }
ENV=staging   # then production
```

| Secret name | What | How to create | Notes |
|---|---|---|---|
| `vv/$ENV/VV_DATA_KEY` | AES-256 key sealing evidence, webhook secrets, callback bodies | `aws secretsmanager create-secret --name vv/$ENV/VV_DATA_KEY --secret-string "$(gen_key)" --region eu-west-2` | **Losing it makes sealed evidence unreadable.** Rotation needs a re-seal job that is not built yet — don't rotate until it exists. |
| `vv/$ENV/VV_HMAC_PEPPER` | Pepper for API-key, email and code hashes | same, with `gen_key` | Changing it invalidates all API keys and contact hashes |
| RDS master password | Database admin | **Created automatically** by RDS (`manage_master_user_password = true` in `modules/database`) | Used only for migrations/owner role |
| `vv/$ENV/VV_APP_PASSWORD` | Runtime DB role `vv_app` password | `gen_pw` | App connects as `VV_APP_DSN=postgresql://vv_app:<pw>@<rds endpoint>:5432/<db name>`. The roles are created by the migration step; locally `vv-admin dev-roles` sets their passwords — [Engineering to confirm the production procedure] |
| `vv/$ENV/VV_WORKER_PASSWORD` | Runtime DB role `vv_worker` password | `gen_pw` | `VV_WORKER_DSN` likewise |
| `vv/$ENV/VV_APP_DSN`, `vv/$ENV/VV_WORKER_DSN` | Full connection strings | Build from the above + RDS endpoint (Terraform output) | Add `?sslmode=require` |
| `vv/$ENV/VV_OWNER_DSN` | Migration/owner connection | From the RDS master secret | **Give only to the migration task, never to the API/worker** (IMP-08) |
| `vv/$ENV/VV_OIDC_CLIENT_ID` and `vv/$ENV/VV_OIDC_CLIENT_SECRET` | Google sign-in for the console | Google Cloud console → APIs & Services → **OAuth consent screen** (internal/external, app name "Vitalos Verify") → **Credentials → Create OAuth client ID → Web application**. Authorised redirect URI: `<VV_CONSOLE_BASE_URL>/console/oidc/callback`. Copy ID and secret into the two secrets. | Issuer `VV_OIDC_ISSUER=https://accounts.google.com` (config, not secret). One client per environment. |
| Supplier API key and webhook signing secret | Identity supplier | From the supplier dashboard after contracting | Names to be fixed when the real adapter is built [Engineering to confirm] |

Plain configuration (ECS task environment, not secrets):

| Variable | Value |
|---|---|
| `VV_ENV` | `staging` or `production` (refuses mocks and dev routes) |
| `VV_EVIDENCE_BUCKET` | Terraform output `bucket_name` from `modules/evidence_storage` |
| `VV_EVIDENCE_KMS_KEY_ID` | Terraform output `kms_key_arn` from `modules/evidence_storage` |
| `VV_TOMBSTONE_BUCKET` | **Gap:** no Terraform module creates the tombstone bucket yet. It must be a separate private, versioned, encrypted bucket **outside** database backups (IMP-18). Engineering to add before staging apply. |
| `VV_OIDC_ISSUER` | `https://accounts.google.com` |
| `VV_CONSOLE_BASE_URL` | e.g. `https://<console host>` |
| `VV_HOSTED_BASE_URL` | e.g. `https://<applicant host>` |
| Email sender (SES identity and from-address) | [Engineering to confirm variable name when the SES mailer is built; owner supplies the verified sender from §7] |

**Do not set** `VV_DUMMY_PROVIDER_SECRET` or `VV_DEV_EXPOSE_CODES` in staging/production — they are development-only.

Wiring gap: `modules/compute` currently passes only the RDS master secret and `VV_ENV` to the task. Engineering must add the secrets and config above to the task definition before the first staging apply.

## 9. Done checklist

- [ ] Root MFA on management account (two devices); no root keys
- [ ] Organisation with staging and production in `Workloads` OU; member root credentials centrally managed
- [ ] SCP guard rails and AI opt-out policy attached
- [ ] Identity Center with MFA; profiles `vv-mgmt`, `vv-staging`, `vv-prod` work
- [ ] Org budget with 50/80/100% alerts (amount = approved cap); anomaly detection on
- [ ] Organisation CloudTrail logging to a private bucket
- [ ] Bootstrap applied in staging and production; `backend.hcl` generated; `terraform init` works for `envs/staging`
- [ ] GitHub variables `AWS_PLAN_ROLE_ARN_*` set
- [ ] ACM certificate issued; SES domain verified
- [ ] Secrets created in each environment
- [ ] Account IDs recorded (§ table at top) and shared with engineering — **not** committed to a public repo
- [ ] Tell engineering: M02-T04 unblocked for `plan` (apply still needs the approved cap)
