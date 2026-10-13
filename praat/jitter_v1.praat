form Experimental jitter v1
    sentence Input_file
    real Interval_start
    real Interval_end
    positive Time_step
    positive Pitch_floor
    positive Pitch_ceiling
    integer Max_candidates
    boolean Very_accurate 0
    real Silence_threshold
    real Voicing_threshold
    real Octave_cost
    real Octave_jump_cost
    real Voiced_unvoiced_cost
    positive Period_floor
    positive Period_ceiling
    positive Maximum_period_factor
endform
Read from file: input_file$
sound_id = selected("Sound")
To Pitch (raw cross-correlation): time_step, pitch_floor, pitch_ceiling, max_candidates, very_accurate, silence_threshold, voicing_threshold, octave_cost, octave_jump_cost, voiced_unvoiced_cost
pitch_id = selected("Pitch")
selectObject: sound_id, pitch_id
To PointProcess (cc)
jitter = Get jitter (local): interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
accepted = Get number of periods: interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
jitter$ = "null"
if jitter <> undefined
    jitter$ = fixed$(jitter, 17)
endif
n = Get number of points
inside = 0
for i from 1 to n
    t = Get time from index: i
    if t >= interval_start and t <= interval_end
        inside += 1
    endif
endfor
writeInfo: "{""jitter_local_ratio"":", jitter$, ",""accepted_periods_praat"":", accepted, ",""pulses_in_interval"":", inside, ",""pulses"": ["
separator$ = ""
for i from 1 to n
    t = Get time from index: i
    appendInfo: separator$, "{""pulse_index"":", i, ",""time_s"":", fixed$(t, 17), "}"
    separator$ = ","
endfor
appendInfoLine: "]}"
