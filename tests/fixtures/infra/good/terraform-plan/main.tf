# A module the simulation can init, validate and plan without a cloud account, so step (1) of K11,
# the planned difference captured from the tool, is shown on a real terraform plan.
terraform {
  required_version = ">= 1.5"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "2.5.2"
    }
  }
}

resource "local_file" "release_notes" {
  filename = "${path.module}/out/release-notes.txt"
  content  = "release 1\n"
}
