form Experimental pitch v1
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
endform
Read from file: input_file$
To Pitch (raw cross-correlation): time_step, pitch_floor, pitch_ceiling, max_candidates, very_accurate, silence_threshold, voicing_threshold, octave_cost, octave_jump_cost, voiced_unvoiced_cost
n = Get number of frames
included = 0
voiced = 0
for i from 1 to n
    t = Get time from frame number: i
    if t >= interval_start and t <= interval_end
        included += 1
        f = Get value in frame: i, "Hertz"
        if f <> undefined
            voiced += 1
        endif
    endif
endfor
mean$ = "null"
sd$ = "null"
if voiced > 0
    mean = Get mean: interval_start, interval_end, "Hertz"
    if mean <> undefined
        mean$ = fixed$(mean, 17)
    endif
endif
if voiced > 1
    sd = Get standard deviation: interval_start, interval_end, "Hertz"
    if sd <> undefined
        sd$ = fixed$(sd, 17)
    endif
endif
writeInfo: "{""f0_mean_hz"":", mean$, ",""f0_sd_hz"":", sd$, ",""total_frames"":", included, ",""voiced_frames"":", voiced, ",""frames"": ["
separator$ = ""
for i from 1 to n
    t = Get time from frame number: i
    if t >= interval_start and t <= interval_end
        f = Get value in frame: i, "Hertz"
        f$ = "null"
        if f <> undefined
            f$ = fixed$(f, 17)
        endif
        appendInfo: separator$, "{""frame_index"":", i, ",""time_s"":", fixed$(t, 17), ",""f0_hz"":", f$, "}"
        separator$ = ","
    endif
endfor
appendInfoLine: "]}"
