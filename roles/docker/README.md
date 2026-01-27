# Docker Role

Installs Docker and Docker Compose on Debian-based systems.

## Role Variables

### Required Variables

None - all variables have defaults.

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `install_docker` | `true` | Enable/disable Docker installation |

### Docker Packages

The role installs the following packages:
- `docker-ce` - Docker Engine
- `docker-ce-cli` - Docker CLI
- `containerd.io` - Container runtime
- `docker-buildx-plugin` - Buildx plugin for multi-platform builds
- `docker-compose-plugin` - Compose plugin v2

## Handlers

Available handlers:

| Handler | Description |
|---------|-------------|
| `restart docker` | Restart Docker service |
| `reload docker` | Reload Docker configuration |
| `start docker` | Start Docker service |
| `stop docker` | Stop Docker service |

## Tasks Structure

```
roles/docker/
├── tasks/
│   └── main.yaml      # Installation and configuration
├── handlers/
│   └── main.yaml      # Docker service handlers
└── defaults/
    └── main.yaml     # Default variables
```

## Usage

### Basic Usage

```yaml
- name: Install Docker
  hosts: docker_servers
  become: yes
  roles:
    - docker
```

### With Custom Variables

```yaml
- name: Install Docker with custom settings
  hosts: docker_servers
  become: yes
  vars:
    install_docker: true
  roles:
    - docker
```

## Installation Process

1. **Check for existing installation**
   - Runs `docker --version` to check if Docker is already installed

2. **Set up Docker repository**
   - Creates `/etc/apt/keyrings` directory
   - Downloads Docker GPG key
   - Adds Docker repository to apt sources

3. **Install Docker packages**
   - Updates apt package index
   - Installs Docker CE, CLI, containerd, and plugins

4. **Configure user permissions**
   - Adds current user to `docker` group

5. **Validate installation**
   - Verifies Docker is installed and accessible

## OS Compatibility

| OS Family | Status |
|-----------|--------|
| Debian/Ubuntu | ✅ Supported |
| Arch/Manjaro | ⚠️ Not supported (use pacman) |

## Requirements

- Debian or Ubuntu system
- Root/sudo access
- Internet access for downloading Docker packages

## Post-Installation

### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version

# Test Docker
docker run hello-world
```

### User Configuration

The role adds the current user to the `docker` group. You may need to log out and log back in for the group change to take effect.

```bash
# Check if user is in docker group
groups $USER

# If not, log out and log back in
# Or use newgrp for current session
newgrp docker
```

### Start Docker Service

```bash
# Start Docker
sudo systemctl start docker

# Enable Docker on boot
sudo systemctl enable docker

# Check Docker status
sudo systemctl status docker
```

## Advanced Configuration

### Docker Daemon Configuration

To customize Docker daemon settings, create `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
```

Then restart Docker:
```bash
sudo systemctl restart docker
```

### Docker Compose Usage

```bash
# Create a docker-compose.yml file
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
EOF

# Start services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

## Troubleshooting

### Permission Denied

If you get "permission denied" when running Docker commands:
```bash
# Add user to docker group (role does this automatically)
sudo usermod -aG docker $USER

# Log out and log back in, or use:
newgrp docker
```

### Docker Service Not Starting

```bash
# Check service status
sudo systemctl status docker

# View logs
sudo journalctl -u docker -n 50

# Check for conflicts
sudo docker info
```

### Network Issues

```bash
# Restart Docker network
sudo systemctl restart docker

# Clear Docker network cache
docker network prune

# Rebuild Docker network
sudo systemctl restart docker
```

## Validation

The role includes installation validation:
```yaml
- name: Verify Docker installation
  ansible.builtin.command: docker --version
  register: docker_version
  changed_when: false

- name: Assert Docker is installed
  ansible.builtin.assert:
    that:
      - docker_version.rc == 0
    success_msg: "Docker successfully installed: {{ docker_version.stdout }}"
    fail_msg: "Docker installation verification failed"
```

## Security Considerations

1. **Docker Group Access**: Adding users to the `docker` group gives them root-equivalent access to the system via Docker. Only add trusted users.

2. **Update Regularly**: Keep Docker and container images updated:
   ```bash
   sudo apt update && sudo apt upgrade docker-ce
   ```

3. **Use Non-Root Containers**: Consider running containers as non-root users:
   ```yaml
   version: '3.8'
   services:
     app:
       image: nginx:latest
       user: "1000:1000"
   ```

## Examples

### Deploy Simple Web Server

```yaml
- name: Deploy web server with Docker
  hosts: web_servers
  become: yes
  vars:
    install_docker: true
  roles:
    - docker

  tasks:
    - name: Create docker-compose.yml
      ansible.builtin.copy:
        dest: /opt/docker-compose.yml
        content: |
          version: '3.8'
          services:
            nginx:
              image: nginx:latest
              ports:
                - "80:80"
              volumes:
                - /opt/html:/usr/share/nginx/html

    - name: Start Docker Compose
      ansible.builtin.command:
        cmd: docker compose -f /opt/docker-compose.yml up -d
      become: yes
```