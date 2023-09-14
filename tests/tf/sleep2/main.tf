variable "sleep2_time1" {
  type    = string
  default = "1s"
}

variable "sleep2_time2" {
  type    = string
  default = "1s"
}

resource "time_sleep" "sleep2_wait1" {
  create_duration = var.time1
}

resource "time_sleep" "sleep2_wait2" {
  create_duration = var.time2
}

output "sleep2_wait1_id" {
  value = time_sleep.wait1.id
}

output "sleep2_wait2_id" {
  value = time_sleep.wait2.id
}
