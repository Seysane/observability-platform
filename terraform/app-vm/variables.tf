variable "node_name" {
  type        = string
  description = "Proxmox node the VM runs on"
  default     = "pve"
}

variable "datastore_id" {
  type        = string
  description = "Proxmox Storage"
  default     = "pve-storage"
}

variable "bridge" {
  type        = string
  description = "Proxmox Bridge"
  default     = "vmbr0"
}

variable "vm_id" {
  type        = number
  description = "Proxmox VM ID"
  default     = 160
}

variable "vm_name" {
  type        = string
  description = "Proxmox client app"
  default     = "client-app"
}

variable "ip_address" {
  type        = string
  description = "IP address"
  default     = "192.168.1.60/24"
}

variable "gateway" {
  type        = string
  description = "Proxmox Gate"
  default     = "192.168.1.1"
}

variable "cpu_cores" {
  type        = number
  description = "CPUs"
  default     = 2
}

variable "memory_mb" {
  type        = number
  description = "RAM in MB"
  default     = 4096
}

variable "disk_size_gb" {
  type        = number
  description = "Disk size in GB"
  default     = 20
}

variable "ssh_public_key_path" {
  type        = string
  description = "SSH public key file path"
  default     = "~/.ssh/id_ed25519.pub"
}

variable "debian_image_url" {
  type        = string
  description = "Pinned Debian 12 generic image URL"
  default     = "https://cloud.debian.org/images/cloud/bookworm/20261018-2635/debian-12-generic-amd64-20261018-2635.qcow2"
}

variable "debian_file_name" {
  type        = string
  description = "Debian file name"
  default     = "debian-12-generic-amd64-20261018-2635.qcow2"
}