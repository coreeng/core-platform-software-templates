variable "infrastructure_project_id" {
  type = string
}

variable "platform_project_id" {
  type = string
}

variable "environment" {
  type = string
}

variable "region" {
  type = string
}

variable "cloudsql" {
  description = "Cloud SQL configuration"
  type = object({
    enabled           = bool
    allowed_ip_ranges = optional(list(map(string)), [])
    clusters = optional(object({
      postgresql = optional(list(object({
        name               = string
        tier               = string
        database_version   = string
        edition            = optional(string, "ENTERPRISE")
        activation_policy  = optional(string, "ALWAYS")
        data_cache_enabled = optional(bool, false)
        databases = list(object({
          name      = string
          charset   = optional(string, "")
          collation = optional(string, "")
        }))
        disk_size             = optional(number, 10)
        disk_type             = optional(string, "PD_SSD")
        disk_autoresize       = optional(bool, true)
        disk_autoresize_limit = optional(number, 0)
        availability_type     = optional(string, "ZONAL")
        backup_configuration = optional(object({
          enabled                        = optional(bool, true)
          start_time                     = optional(string, "23:00")
          location                       = optional(string, null)
          point_in_time_recovery_enabled = optional(bool, true)
          transaction_log_retention_days = optional(string, "7")
          retained_backups               = optional(number, 15)
          retention_unit                 = optional(string, "COUNT")
        }), {})
        database_flags = optional(list(object({
          name  = string
          value = string
        })), [])
        insights_config = optional(object({
          query_plans_per_minute  = optional(number, 5)
          query_string_length     = optional(number, 1024)
          record_application_tags = optional(bool, false)
          record_client_address   = optional(bool, false)
        }), {})
        maintenance_window_day          = optional(number, 1)
        maintenance_window_hour         = optional(number, 23)
        maintenance_window_update_track = optional(string, "stable")
        deletion_protection             = optional(bool, true)
        database_deletion_policy        = optional(string, "ABANDON")
        retain_backups_on_delete        = optional(bool, false)
        connector_enforcement           = optional(bool, false)
        iam_users = optional(list(object({
          id    = string
          email = string
          type  = optional(string)
        })), [])
      })))
    }))
  })
}
