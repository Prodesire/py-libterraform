variable "time1" {
  type = string
  default = "1s"
}

variable "time2" {
  type = string
  default = "1s"
}

resource "time_sleep" "wait1" {
  create_duration = var.time1
}

resource "time_sleep" "wait2" {
  create_duration = var.time2
}
