form Known amplitudes
    sentence Tier_file
    positive Period_floor
    positive Period_ceiling
    positive Maximum_amplitude_factor
endform
Read from file: tier_file$
s = Get shimmer (local): period_floor, period_ceiling, maximum_amplitude_factor
s$ = "null"
if s <> undefined
    s$ = fixed$(100*s, 17)
endif
writeInfoLine: "{""shimmer_local_percent"":", s$, "}"
