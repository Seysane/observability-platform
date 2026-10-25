output "ip_address" {
  description = "Observability VM IPv4 address"
  value       = split("/", var.ip_address)[0]
}

output "vm_id" {
  description = "Proxmox VM ID"
  value       = proxmox_virtual_environment_vm.observability.vm_id
}

output "vm_name" {
  description = "Proxmox VM name"
  value       = proxmox_virtual_environment_vm.observability.name
}
