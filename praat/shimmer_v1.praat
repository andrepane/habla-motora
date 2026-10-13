form Experimental shimmer v1
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
    positive Maximum_amplitude_factor
endform
Read from file: input_file$
sound_id = selected("Sound")
To Pitch (raw cross-correlation): time_step, pitch_floor, pitch_ceiling, max_candidates, very_accurate, silence_threshold, voicing_threshold, octave_cost, octave_jump_cost, voiced_unvoiced_cost
pitch_id = selected("Pitch")
selectObject: sound_id, pitch_id
To PointProcess (cc)
pulse_id = selected("PointProcess")
accepted = Get number of periods: interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
n = Get number of points
inside = 0
for i from 1 to n
    t = Get time from index: i
    if t >= interval_start and t <= interval_end
        inside += 1
    endif
endfor
selectObject: sound_id, pulse_id
shimmer = Get shimmer (local): interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor, maximum_amplitude_factor
shimmer$ = "null"
if shimmer <> undefined
    shimmer$ = fixed$(shimmer, 17)
endif
amplitude_count = 0
tier_shimmer$ = "null"
if inside >= 3
    To AmplitudeTier (period): interval_start, interval_end, period_floor, period_ceiling, maximum_period_factor
    tier_shimmer = Get shimmer (local): period_floor, period_ceiling, maximum_amplitude_factor
    if tier_shimmer <> undefined
        tier_shimmer$ = fixed$(tier_shimmer, 17)
    endif
    amplitude_count = Get number of points
    if amplitude_count > 0
        Down to TableOfReal
        amplitude_table = selected("TableOfReal")
    endif
endif
writeInfo: "{""shimmer_local_ratio"":", shimmer$, ",""tier_shimmer_ratio"":", tier_shimmer$, ",""accepted_periods_praat"":", accepted, ",""pulses_in_interval"":", inside, ",""pulses"": ["
selectObject: pulse_id
separator$ = ""
for i from 1 to n
    t = Get time from index: i
    appendInfo: separator$, "{""pulse_index"":", i, ",""time_s"":", fixed$(t, 17), "}"
    separator$ = ","
endfor
appendInfo: "],""amplitudes"": ["
separator$ = ""
if amplitude_count > 0
    selectObject: amplitude_table
    for i from 1 to amplitude_count
        t = Get value: i, 1
        a = Get value: i, 2
        appendInfo: separator$, "{""amplitude_index"":", i, ",""time_s"":", fixed$(t, 17), ",""amplitude_rms"":", fixed$(a, 17), "}"
        separator$ = ","
    endfor
endif
appendInfoLine: "]}"
