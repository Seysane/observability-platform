resource "proxmox_download_file" "debian_cloud" {
  node_name    = var.node_name
  datastore_id = var.datastore_id
  content_type = "import"
  file_name    = "debian-12-genericcloud-amd64.qcow2"
  url          = "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
}