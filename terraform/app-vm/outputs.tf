output "ip_address" {
  description = "IP address output"
  value       = split("/", var.ip_address)[0]
}