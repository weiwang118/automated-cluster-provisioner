output "gdce_provisioner_sa_email" {
  description = "Email of the GDCE provisioning Service Account"
  value       = google_service_account.gdce-provisioning-agent.email
}

output "zone_watcher_sa_email" {
  description = "Email of the Zone Watcher Service Account"
  value       = google_service_account.zone-watcher-agent.email
}
