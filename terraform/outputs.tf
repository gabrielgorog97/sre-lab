output "app_url" {
  description = "URL of the running app"
  value       = "http://localhost:${var.host_port}"
}

output "image" {
  description = "Image the container runs"
  value       = docker_image.app.name
}
