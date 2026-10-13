form Known times reference, no acoustic detector
    sentence Times_file
    real Interval_start
    real Interval_end
    positive Period_floor
    positive Period_ceiling
    positive Maximum_period_factor
endform
Read from file: times_file$
jitter = Get jitter (local): interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
accepted = Get number of periods: interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
jitter$ = "null"
if jitter <> undefined
    jitter$ = fixed$(100*jitter, 17)
endif
writeInfoLine: "{""jitter_local_percent"":", jitter$, ",""accepted_periods"":", accepted, "}"
