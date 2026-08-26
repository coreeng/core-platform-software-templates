resource "google_project_service" "cloud_resource_manager" {
  project                    = var.infrastructure_project_id
  service                    = "cloudresourcemanager.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

module "project-services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "18.1.0"

  project_id = var.infrastructure_project_id

  depends_on = [google_project_service.cloud_resource_manager]

  disable_dependent_services  = false
  disable_services_on_destroy = false

  activate_apis = [
    "compute.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com",
  ]
}
