output "gdce_provisioner_sa_email" {
  description = "IAM member string of the GDCE provisioning Service Account"
  value       = google_service_account.gdce-provisioning-agent.member
}

output "zone_watcher_sa_email" {
  description = "IAM member string of the Zone Watcher Service Account"
  value       = google_service_account.zone-watcher-agent.member
}
