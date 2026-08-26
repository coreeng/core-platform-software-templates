mock_provider "google" {}
mock_provider "google-beta" {}
mock_provider "null" {}
mock_provider "random" {}

run "bootstraps_cloud_resource_manager_before_project_services" {
  command = plan

  plan_options {
    target = [google_project_iam_member.cloudsql_viewer]
  }

  module {
    source = "./modules/cloudsql"
  }

  variables {
    infrastructure_project_id = "example-infra-test"
    platform_project_id       = "example-platform-test"
    environment               = "integration"
    region                    = "europe-west2"
    cloudsql = {
      enabled = true
      clusters = {
        postgresql = [{
          name             = "bootstrap"
          tier             = "db-g1-small"
          database_version = "POSTGRES_18"
          databases = [{
            name = "application"
            iam_users = [{
              id    = "application"
              email = "application@example.com"
              roles = ["pg_read_all_data"]
            }]
          }]
        }]
      }
    }
  }

  assert {
    condition     = google_project_service.cloud_resource_manager.service == "cloudresourcemanager.googleapis.com"
    error_message = "Cloud Resource Manager must be bootstrapped before project services and IAM resources are managed."
  }
}
