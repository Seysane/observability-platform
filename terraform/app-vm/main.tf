resource "proxmox_download_file" "debian_cloud" {
  node_name    = var.node_name
  datastore_id = var.datastore_id
  content_type = "import"
  file_name    = var.debian_file_name
  url          = var.debian_image_url
}