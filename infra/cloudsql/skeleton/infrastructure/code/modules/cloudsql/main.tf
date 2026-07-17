data "google_project" "platform_project" {
  project_id = var.platform_project_id
  depends_on = [module.project-services]
}

resource "random_password" "cloudsql_initial_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "google_compute_network" "psa" {
  count = local.any_psa_enabled && local.manage_psa_resources ? 1 : 0

  name                    = "cloudsql-${var.environment}-psa"
  project                 = var.infrastructure_project_id
  auto_create_subnetworks = false
  description             = "Cloud SQL PSA network"
  depends_on              = [module.project-services]
}

module "cloudsql-psa" {
  count = local.any_psa_enabled && local.manage_psa_resources ? 1 : 0

  source  = "terraform-google-modules/sql-db/google//modules/private_service_access"
  version = "26.2.2"

  depends_on  = [module.project-services, google_compute_network.psa]
  project_id  = var.infrastructure_project_id
  vpc_network = google_compute_network.psa[0].name
  address     = "10.220.0.0"
}

module "cloudsql-postgresql" {
  for_each   = local.postgresql_clusters_map
  source     = "terraform-google-modules/sql-db/google//modules/postgresql"
  version    = "26.2.2"
  depends_on = [module.project-services, module.cloudsql-psa]
  project_id = var.infrastructure_project_id
  region     = var.region
  name       = "${each.key}-${var.environment}-cluster"

  availability_type = each.value.availability_type

  database_version   = each.value.database_version
  edition            = each.value.edition
  activation_policy  = each.value.activation_policy
  data_cache_enabled = each.value.data_cache_enabled

  tier                  = each.value.tier
  disk_type             = each.value.disk_type
  disk_autoresize       = each.value.disk_autoresize
  disk_autoresize_limit = each.value.disk_autoresize_limit
  disk_size             = each.value.disk_size

  maintenance_window_day          = each.value.maintenance_window_day
  maintenance_window_hour         = each.value.maintenance_window_hour
  maintenance_window_update_track = each.value.maintenance_window_update_track

  deletion_protection         = each.value.deletion_protection
  deletion_protection_enabled = each.value.deletion_protection
  database_deletion_policy    = each.value.database_deletion_policy
  retain_backups_on_delete    = each.value.retain_backups_on_delete

  database_flags = each.value.database_flags
  iam_users      = each.value.iam_users

  insights_config = {
    query_plans_per_minute  = each.value.insights_config.query_plans_per_minute
    query_string_length     = each.value.insights_config.query_string_length
    record_application_tags = each.value.insights_config.record_application_tags
    record_client_address   = each.value.insights_config.record_client_address
  }

  ip_configuration = {
    ssl_mode                      = "ENCRYPTED_ONLY"
    authorized_networks           = var.cloudsql.allowed_ip_ranges
    ipv4_enabled                  = each.value.public_ip_enabled
    private_network               = local.cluster_psa_enabled[each.key] ? local.psa_network_id : null
    psc_enabled                   = local.cluster_psc_enabled[each.key]
    psc_allowed_consumer_projects = local.cluster_psc_enabled[each.key] ? [data.google_project.platform_project.number] : []
  }

  backup_configuration = {
    enabled                        = each.value.backup_configuration.enabled
    start_time                     = each.value.backup_configuration.start_time
    location                       = each.value.backup_configuration.location
    point_in_time_recovery_enabled = each.value.backup_configuration.point_in_time_recovery_enabled
    transaction_log_retention_days = each.value.backup_configuration.transaction_log_retention_days
    retained_backups               = each.value.backup_configuration.retained_backups
    retention_unit                 = each.value.backup_configuration.retention_unit
  }

  enable_default_db    = false
  additional_databases = each.value.databases

  # Default postgres user is required for the provisioner to grant privileges to IAM users
  # Do not disable unless switching to a different privilege grant mechanism
  user_name     = "postgres"
  user_password = random_password.cloudsql_initial_password.result

  # Connector enforcement requires all connections to use Cloud SQL Auth Proxy or connector library
  connector_enforcement = each.value.connector_enforcement

  # Password validation policy
  password_validation_policy_config = each.value.password_validation_policy_config
}

# Grant Cloud SQL Client role to all IAM users
# This allows them to call the Cloud SQL Admin API for connection info
resource "google_project_iam_member" "cloudsql_client" {
  for_each = local.iam_users

  project = var.infrastructure_project_id
  role    = "roles/cloudsql.client"
  member  = each.value
}

# Grant Cloud SQL Instance User role to all IAM users
# This allows them to authenticate to Cloud SQL instances using IAM
resource "google_project_iam_member" "cloudsql_instance_user" {
  for_each = local.iam_users

  project = var.infrastructure_project_id
  role    = "roles/cloudsql.instanceUser"
  member  = each.value
}

# Grant Service Usage Consumer role to IAM service accounts only
# This allows the service accounts from the platform project to access Cloud SQL in the infrastructure project
resource "google_project_iam_member" "service_usage_consumer" {
  for_each = local.service_account_iam_users

  project = var.infrastructure_project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = each.value
}

# Grant Cloud SQL Viewer role to all IAM users
# This allows them to list databases and users in Cloud SQL instances
resource "google_project_iam_member" "cloudsql_viewer" {
  for_each = local.iam_users

  project = var.infrastructure_project_id
  role    = "roles/cloudsql.viewer"
  member  = each.value
}

# Grant comprehensive privileges to IAM users specified for each database
resource "null_resource" "grant_iam_user_privileges" {
  for_each = {
    for combo in flatten([
      for cluster_name, cluster in local.postgresql_clusters_map : [
        for db in cluster.databases : [
          for iam_user in db.iam_users : {
            key          = "${cluster_name}/${db.name}/${iam_user.id}"
            cluster_name = "${cluster_name}-${var.environment}-cluster"
            database     = db.name
            # CloudSQL truncates IAM usernames to end at .iam (63 char PostgreSQL limit)
            iam_user = replace(iam_user.email, ".iam.gserviceaccount.com", ".iam")
            roles    = try(iam_user.roles, [])
          }
        ]
      ]
    ]) : combo.key => combo
  }

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = "/bin/bash \"${path.module}/scripts/grant-iam-user-privileges.sh\""

    environment = {
      CLUSTER_NAME   = each.value.cluster_name
      DATABASE_NAME  = each.value.database
      IAM_USER       = each.value.iam_user
      PGPASSWORD     = nonsensitive(random_password.cloudsql_initial_password.result)
      POSTGRES_ROLES = jsonencode(each.value.roles)
      PROJECT_ID     = var.infrastructure_project_id
    }
  }

  depends_on = [
    module.cloudsql-postgresql,
    google_project_iam_member.cloudsql_client
  ]

  triggers = {
    cluster  = each.value.cluster_name
    database = each.value.database
    iam_user = each.value.iam_user
    roles    = join(",", each.value.roles)
    # Increment this version to force re-run
    grant_version = "v1"
  }
}

# Apply password verification to the postgres user to satisfy Google Cloud security recommendations
resource "null_resource" "apply_user_password_policy" {
  for_each = local.postgresql_clusters_map

  provisioner "local-exec" {
    interpreter = ["/bin/bash", "-c"]
    command     = <<-EOT
      set -euo pipefail

      echo "Applying password policy to postgres user on instance '$CLUSTER_NAME'..."

      gcloud sql users set-password-policy postgres \
        --instance="$CLUSTER_NAME" \
        --project="$PROJECT_ID" \
        --host="%" \
        --password-policy-enable-password-verification

      echo "Password verification enabled for postgres user"
    EOT

    environment = {
      CLUSTER_NAME = "${each.key}-${var.environment}-cluster"
      PROJECT_ID   = var.infrastructure_project_id
    }
  }

  depends_on = [
    module.cloudsql-postgresql
  ]

  triggers = {
    cluster = "${each.key}-${var.environment}-cluster"
    # Increment this version to force re-run
    policy_version = "v1"
  }
}
