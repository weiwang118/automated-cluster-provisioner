terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.42.0, < 7.0.0"
    }
  }
  backend "gcs" {
    bucket = "wei-acp-test-bucket" ## Change the bucket name before using
    prefix = "sandbox" ## Change the prefix name before using
  }
} 