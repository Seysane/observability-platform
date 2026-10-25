# Observability VM (Proxmox)

Creates a separate Debian 12 cloud VM for the observability stack.

Defaults:
- Proxmox node: `pve2`
- VM ID: `170`
- VM name: `observability`
- IPv4: `192.168.1.70/24`
- CPU: 2 cores
- RAM: 4096 MB
- Disk: 32 GB
- SSH user: `debian`

Before applying, verify that VM ID `170` and IP `192.168.1.70` are unused.
Also verify `pve-storage`, `vmbr0`, `pve2`, and image-download node `pve`
match your Proxmox configuration. The provider credentials should be supplied
through the environment as in the existing `app-vm` setup.

From this directory:

```bash
terraform init
terraform fmt -check
terraform validate
terraform plan
```

Review the plan before running `terraform apply`.

The cloud image has a distinct filename because this module has a separate
Terraform state from `terraform/app-vm`.
