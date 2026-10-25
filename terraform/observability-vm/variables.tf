variable "node_name" {
  type        = string
  description = "Proxmox node the VM runs on"
  default     = "pve2"
}

variable "datastore_id" {
  type        = string
  description = "Proxmox storage for the VM disk and cloud image"
  default     = "pve-storage"
}

variable "bridge" {
  type        = string
  description = "Proxmox network bridge"
  default     = "vmbr0"
}

variable "vm_id" {
  type        = number
  description = "Unique Proxmox VM ID"
  default     = 170
}

variable "vm_name" {
  type        = string
  description = "Name of the observability VM"
  default     = "observability"
}

variable "ip_address" {
  type        = string
  description = "Static IPv4 address with CIDR prefix"
  default     = "192.168.1.70/24"
}

variable "gateway" {
  type        = string
  description = "IPv4 default gateway"
  default     = "192.168.1.1"
}

variable "cpu_cores" {
  type        = number
  description = "Number of vCPU cores"
  default     = 2
}

variable "memory_mb" {
  type        = number
  description = "Memory in MB"
  default     = 4096
}

variable "disk_size_gb" {
  type        = number
  description = "System disk size in GB"
  default     = 32
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to the SSH public key used for the Debian account"
  default     = "~/.ssh/id_ed25519.pub"
}

variable "debian_image_url" {
  type        = string
  description = "Pinned Debian 12 generic cloud image URL"
  default     = "https://cloud.debian.org/images/cloud/bookworm/20261018-2635/debian-12-generic-amd64-20261018-2635.qcow2"
}

# Separate name because app-vm uses its own Terraform state.
variable "debian_file_name" {
  type        = string
  description = "Unique filename for the observability VM cloud image"
  default     = "debian-12-observability-20261018-2635.qcow2"
}

variable "image_node_name" {
  type        = string
  description = "Proxmox node that downloads the cloud image"
  default     = "pve"
}
