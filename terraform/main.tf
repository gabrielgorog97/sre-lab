provider "docker" {}

resource "docker_image" "app" {
  name         = "${var.image_repository}:${var.image_tag}"
  keep_locally = false
}

resource "docker_container" "app" {
  name    = var.container_name
  image   = docker_image.app.image_id
  restart = "unless-stopped"

  ports {
    internal = 8000
    external = var.host_port
  }
}
