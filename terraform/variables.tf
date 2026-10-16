variable "image_repository" {
  description = "Container image repository"
  type        = string
  default     = "ghcr.io/gabrielgorog97/sre-lab"
}

variable "image_tag" {
  description = "Image tag to run, for example sha-f63dd8f"
  type        = string
}

variable "container_name" {
  description = "Name of the Docker container"
  type        = string
  default     = "sre-lab-tf"
}

variable "host_port" {
  description = "Port on the Mac that forwards to the app"
  type        = number
  default     = 8080

  validation {
    condition     = var.host_port >= 1024 && var.host_port <= 65535
    error_message = "host_port must be between 1024 and 65535."
  }
}
