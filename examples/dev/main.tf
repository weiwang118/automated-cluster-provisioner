module "cluster_automation" {
  source                       = "../../module"
  project_id                   = "cloud-alchemists-sandbox"
  source_of_truth_repo         = "github.com/weiwang118/automated-cluster-provisioner"
  git_secret_id                = "wei-acp-test"
  project_id_secrets           = "cloud-alchemists-sandbox"
  source_of_truth_path         = "example-source-of-truth.csv"
  region                       = "us-central1"
  environment                  = "wei-dev"
  cluster_creation_timeout     = "86400"
  cluster_creation_max_retries = "0"
  notification_channel_email   = "weiww@google.com"
  opt_in_build_messages        = true
  default_config_sync_version  = "1.18.3"
}