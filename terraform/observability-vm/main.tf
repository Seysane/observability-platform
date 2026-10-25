resource "proxmox_download_file" "debian_cloud" {
  node_name    = var.image_node_name
  datastore_id = var.datastore_id
  content_type = "import"
  file_name    = var.debian_file_name
  url          = var.debian_image_url
}

resource "proxmox_virtual_environment_vm" "observability" {
  name      = var.vm_name
  node_name = var.node_name
  vm_id     = var.vm_id

  cpu {
    cores = var.cpu_cores
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = var.memory_mb
  }

  disk {
    datastore_id = var.datastore_id
    import_from  = proxmox_download_file.debian_cloud.id
    interface    = "scsi0"
    size         = var.disk_size_gb
  }

  network_device {
    bridge = var.bridge
  }

  initialization {
    datastore_id = var.datastore_id

    ip_config {
      ipv4 {
        address = var.ip_address
        gateway = var.gateway
      }
    }

    user_account {
      username = "debian"
      keys     = [trimspace(file(pathexpand(var.ssh_public_key_path)))]
    }
  }

  operating_system {
    type = "l26"
  }

  serial_device {}
}
