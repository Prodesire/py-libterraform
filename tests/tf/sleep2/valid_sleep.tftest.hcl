variables {
  sleep2_time2 = "2s"
}

run "valid_sleep_duration" {

  assert {
    condition     = time_sleep.sleep2_wait1.create_duration == "1s"
    error_message = "libterraform test success!"
  }

  assert {
    condition     = time_sleep.sleep2_wait2.create_duration == "2s"
    error_message = "Duration did not match expected"
  }

}
